#!/usr/bin/env python3
"""Fixed entrypoint for converting litigation materials into Markdown folders.

The script handles deterministic work only: inventory, MinerU submission,
result download, folder layout, normalized filenames, manifests, and review
markers for downstream legal analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - shown to the operator at runtime
    requests = None  # type: ignore[assignment]


CASE_DIRS = [
    "materials/A_法院及仲裁机构文件",
    "materials/B_当事人主张材料",
    "materials/C_当事人提交的证据材料",
    "materials/D_第三方客观材料",
    "materials/E_律师制作文书",
    "materials/F_AI过程文件",
    "materials/Z_待人工复核",
]

PROCESSABLE_EXTS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEXT_EXTS = {".txt", ".md"}
OFFICE_EXTS = {".doc", ".docx", ".ppt", ".pptx"}
SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "md诉讼材料",
    "materials",
    "_mineru_cache",
}


MINERU_SETUP_GUIDE = """未检测到 MINERU_API_TOKEN，先完成 MinerU API 配置后再继续。

最短配置流程：
1. 打开 MinerU API 页面：
   https://mineru.net/apiManage/docs?openApplyModal=true
2. 登录或注册 MinerU / OpenDataLab 账号。
3. 在 API 管理页面申请或复制 API Token。
4. 在当前项目目录或本 Skill 目录中新建 mineru.env。
5. 写入以下内容：

   MINERU_API_TOKEN=你的Token
   MINERU_API_BASE=https://mineru.net/api/v4
   MINERU_MODEL_VERSION=pipeline
   MINERU_LANGUAGE_CODE=ch
   MINERU_ENABLE_OCR=true
   MINERU_ENABLE_TABLE=true
   MINERU_ENABLE_FORMULA=false

6. 保存后重新运行：
   python scripts/intake_case.py "D:/path/to/案件材料目录"

注意：Token 只放在本机环境变量或本地 mineru.env，不要发到聊天窗口，也不要提交到 GitHub。
"""


@dataclass
class SourceFile:
    path: Path
    data_id: str
    submit_to_mineru: bool
    evidence_only: bool


@dataclass
class ParsedRecord:
    file_name: str
    data_id: str
    state: str
    err_msg: str
    source_path: Path
    full_md_path: Path | None
    zip_path: Path | None


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config() -> dict[str, str]:
    config = dict(os.environ)
    skill_root = Path(__file__).resolve().parents[1]
    candidate_env_files = [
        Path.cwd() / ".env",
        Path.cwd() / "mineru.env",
        skill_root / ".env",
        skill_root / "mineru.env",
    ]
    for env_file in candidate_env_files:
        for key, value in read_env_file(env_file).items():
            config.setdefault(key, value)
    config.setdefault("MINERU_API_BASE", "https://mineru.net/api/v4")
    config.setdefault("MINERU_MODEL_VERSION", "pipeline")
    config.setdefault("MINERU_LANGUAGE_CODE", "ch")
    config.setdefault("MINERU_ENABLE_OCR", "true")
    config.setdefault("MINERU_ENABLE_TABLE", "true")
    config.setdefault("MINERU_ENABLE_FORMULA", "false")
    return config


def bool_config(config: dict[str, str], key: str) -> bool:
    return config.get(key, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def sanitize_filename(text: str, fallback: str = "未命名材料") -> str:
    text = re.sub(r"[<>:\"/\\|?*\r\n\t]+", "-", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"-{2,}", "-", text).strip(" .-_")
    return (text or fallback)[:100]


def guess_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "PDF"
    if ext in OFFICE_EXTS:
        return "Office"
    if ext in IMAGE_EXTS:
        return "内容图片"
    if ext in TEXT_EXTS:
        return "文本"
    return ext.lstrip(".").upper() or "未知"


def guess_category(name: str, text: str = "") -> str:
    lowered = f"{name}\n{text[:5000]}".lower()
    if any(k in lowered for k in ["传票", "裁定", "判决", "决定书", "通知书", "受理", "举证通知", "开庭", "庭审笔录", "调解书", "仲裁"]):
        return "A_法院及仲裁机构文件"
    if any(k in lowered for k in ["ocr", "mineru", "ai过程", "ai分析", "材料清单", "阅读顺序", "事实时间线", "证据核查", "检索记录", "草稿", "draft"]):
        return "F_AI过程文件"
    if any(k in lowered for k in ["起诉状", "答辩状", "反诉状", "上诉状", "再审申请", "申请书", "情况说明", "事实陈述", "陈述书", "申诉书", "保全申请", "调查取证申请", "调查令申请", "执行申请"]):
        return "B_当事人主张材料"
    if any(k in lowered for k in ["代理词", "代理意见", "质证意见", "证据目录", "法律意见", "律师函", "庭审提纲", "工作备忘录"]):
        return "E_律师制作文书"
    if any(k in lowered for k in ["鉴定", "评估", "审计", "公证", "银行流水", "工商", "征信", "检测", "专家意见"]):
        return "D_第三方客观材料"
    if any(k in lowered for k in ["合同", "协议", "订单", "确认单", "付款", "发票", "收据", "微信", "wechat", "聊天记录", "聊天截图", "邮件", "函", "沟通", "通知", "短信", "照片", "录音", "凭证"]):
        return "C_当事人提交的证据材料"
    return "Z_待人工复核"


def category_label(category: str) -> str:
    return category.split("_", 1)[1] if "_" in category else category


DATE_PATTERNS = [
    re.compile(r"(?P<y>20\d{2}|19\d{2})[.\-/年](?P<m>1[0-2]|0?[1-9])[.\-/月](?P<d>3[01]|[12]\d|0?[1-9])日?"),
    re.compile(r"(?P<y>20\d{2}|19\d{2})(?P<m>0[1-9]|1[0-2])(?P<d>0[1-9]|[12]\d|3[01])"),
    re.compile(r"(?P<y>20\d{2}|19\d{2})[.\-/年](?P<m>1[0-2]|0?[1-9])月?"),
    re.compile(r"(?P<y>20\d{2}|19\d{2})"),
]


DATE_SKIP_MARKERS = [
    "出生",
    "出生日期",
    "护照",
    "护照号",
]


DATE_FORMATION_MARKERS = [
    "日期",
    "签署",
    "签订",
    "出具",
    "开具",
    "落款",
]


def format_date_match(match: re.Match[str]) -> str:
    year = match.group("y")
    month = match.groupdict().get("m")
    day = match.groupdict().get("d")
    month_num = int(month) if month else None
    if month_num and day:
        return f"{year}-{month_num:02d}-{int(day):02d}"
    if month_num:
        return f"{year}-{month_num:02d}"
    return year


def extract_first_date(line: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(line)
        if match:
            return format_date_match(match)
    return None


def is_birth_or_identity_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in DATE_SKIP_MARKERS)


def is_formation_date_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in DATE_FORMATION_MARKERS)


def guess_material_date(path: Path, text: str = "") -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # First priority: explicit document formation dates, excluding identity/birth lines.
    for line in lines[:120]:
        if is_birth_or_identity_line(line):
            continue
        if is_formation_date_line(line):
            found = extract_first_date(line)
            if found:
                return found

    # Second priority: file name dates, useful for generated screenshots and exports.
    found = extract_first_date(path.stem)
    if found:
        return found

    # Last resort: any non-birth date in the first part of the text.
    for line in lines[:160]:
        if is_birth_or_identity_line(line):
            continue
        found = extract_first_date(line)
        if found:
            return found
    return "未明日期"


def clean_material_name(path: Path) -> str:
    name = path.stem.strip()
    name = re.sub(r"^(20\d{2}|19\d{2})[.\-_年]?(1[0-2]|0?[1-9])?[.\-_月]?(3[01]|[12]\d|0?[1-9])?日?[\s.\-_]*", "", name)
    name = re.sub(r"ChatGPTImage|ChatGPT Image", "", name, flags=re.IGNORECASE).strip()
    return sanitize_filename(name, "未命名材料")


def infer_material_name(path: Path, text: str) -> str:
    return clean_material_name(path)


def ensure_case_dirs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for rel in CASE_DIRS:
        (output_dir / rel).mkdir(parents=True, exist_ok=True)


def should_skip_dir(path: Path, output_dir: Path) -> bool:
    if path == output_dir or output_dir in path.parents:
        return True
    if path.name in SKIP_DIR_NAMES:
        return True
    if path.name.startswith("_tmp"):
        return True
    return False


def is_evidence_image(path: Path, input_dir: Path) -> bool:
    rel_parts = {part.lower() for part in path.relative_to(input_dir).parts[:-1]}
    return path.suffix.lower() in IMAGE_EXTS and "图片" in rel_parts


def collect_sources(input_dir: Path, output_dir: Path) -> list[SourceFile]:
    files: list[Path] = []
    for path in input_dir.rglob("*"):
        if path.is_dir():
            continue
        if any(should_skip_dir(parent, output_dir) for parent in [path.parent, *path.parents]):
            continue
        if path.suffix.lower() not in PROCESSABLE_EXTS | TEXT_EXTS:
            continue
        files.append(path)

    sources: list[SourceFile] = []
    for idx, path in enumerate(sorted(files), start=1):
        evidence_only = is_evidence_image(path, input_dir)
        submit = path.suffix.lower() in PROCESSABLE_EXTS and not evidence_only
        sources.append(
            SourceFile(
                path=path,
                data_id=f"material_{idx:04d}",
                submit_to_mineru=submit,
                evidence_only=evidence_only,
            )
        )
    return sources


def require_requests() -> Any:
    if requests is None:
        raise RuntimeError("requests is not installed; install requests or run with --no-api.")
    return requests


def post_json(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = require_requests()
    response = req.post(
        url,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"MinerU API failed: {data.get('msg') or data}")
    return data


def get_json(url: str, token: str) -> dict[str, Any]:
    req = require_requests()
    response = req.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"MinerU API failed: {data.get('msg') or data}")
    return data


def submit_mineru_batch(
    files: list[SourceFile],
    config: dict[str, str],
    poll_interval: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    token = config.get("MINERU_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError(MINERU_SETUP_GUIDE)

    base = config["MINERU_API_BASE"].rstrip("/")
    payload = {
        "files": [
            {"name": source.path.name, "data_id": source.data_id, "is_ocr": True}
            for source in files
        ],
        "model_version": config["MINERU_MODEL_VERSION"],
        "language": config["MINERU_LANGUAGE_CODE"],
        "enable_table": bool_config(config, "MINERU_ENABLE_TABLE"),
        "enable_formula": bool_config(config, "MINERU_ENABLE_FORMULA"),
    }

    result = post_json(f"{base}/file-urls/batch", token, payload)
    batch_id = result["data"]["batch_id"]
    upload_urls = result["data"]["file_urls"]
    if len(upload_urls) != len(files):
        raise RuntimeError("MinerU returned a different number of upload URLs than requested files.")

    req = require_requests()
    for source, upload_url in zip(files, upload_urls):
        with source.path.open("rb") as handle:
            upload = req.put(upload_url, data=handle, timeout=300)
        upload.raise_for_status()

    deadline = time.time() + timeout_seconds
    last_result: dict[str, Any] | None = None
    while time.time() < deadline:
        last_result = get_json(f"{base}/extract-results/batch/{batch_id}", token)
        items = last_result.get("data", {}).get("extract_result", [])
        states = {str(item.get("state", "")).lower() for item in items}
        if len(items) >= len(files) and states <= {"done", "failed"}:
            return last_result
        done_count = sum(1 for item in items if str(item.get("state", "")).lower() == "done")
        print(f"MinerU batch {batch_id}: {done_count}/{len(files)} done", flush=True)
        time.sleep(poll_interval)

    raise TimeoutError(f"MinerU batch polling timed out. Last result: {last_result}")


def download_and_extract_results(
    result: dict[str, Any],
    sources: list[SourceFile],
    cache_dir: Path,
) -> list[ParsedRecord]:
    req = require_requests()
    cache_dir.mkdir(parents=True, exist_ok=True)
    by_id = {source.data_id: source for source in sources}
    records: list[ParsedRecord] = []
    for item in result.get("data", {}).get("extract_result", []):
        data_id = item.get("data_id", "")
        source = by_id.get(data_id)
        if source is None:
            continue
        state = str(item.get("state", ""))
        err_msg = str(item.get("err_msg", ""))
        zip_path: Path | None = None
        full_md_path: Path | None = None
        full_zip_url = item.get("full_zip_url")
        if state.lower() == "done" and full_zip_url:
            zip_path = cache_dir / f"{data_id}.zip"
            response = req.get(full_zip_url, timeout=300)
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            extract_dir = cache_dir / data_id
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)
            candidates = list(extract_dir.rglob("full.md"))
            full_md_path = candidates[0] if candidates else None
        records.append(
            ParsedRecord(
                file_name=source.path.name,
                data_id=data_id,
                state=state,
                err_msg=err_msg,
                source_path=source.path,
                full_md_path=full_md_path,
                zip_path=zip_path,
            )
        )
    return records


def load_records(path: Path) -> list[ParsedRecord]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    records: list[ParsedRecord] = []
    for item in raw:
        records.append(
            ParsedRecord(
                file_name=item["file_name"],
                data_id=item["data_id"],
                state=item.get("state", ""),
                err_msg=item.get("err_msg", ""),
                source_path=Path(item["source_path"]),
                full_md_path=Path(item["full_md_path"]) if item.get("full_md_path") else None,
                zip_path=Path(item["zip_path"]) if item.get("zip_path") else None,
            )
        )
    return records


def write_records(path: Path, records: list[ParsedRecord]) -> None:
    serializable = [
        {
            "file_name": record.file_name,
            "data_id": record.data_id,
            "state": record.state,
            "err_msg": record.err_msg,
            "source_path": str(record.source_path),
            "full_md_path": str(record.full_md_path) if record.full_md_path else "",
            "zip_path": str(record.zip_path) if record.zip_path else "",
        }
        for record in records
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def unique_md_name(base_name: str, seen: dict[str, int]) -> str:
    base = sanitize_filename(base_name)
    count = seen.get(base, 0) + 1
    seen[base] = count
    if count > 1:
        base = f"{base}-{count:02d}"
    return f"{base}.md"


def relative_link(path: Path, output_dir: Path) -> str:
    return path.relative_to(output_dir).as_posix()


def wrap_markdown(
    record: ParsedRecord,
    output_dir: Path,
    seen: dict[str, int],
) -> dict[str, str]:
    raw_text = ""
    if record.full_md_path and record.full_md_path.exists():
        raw_text = record.full_md_path.read_text(encoding="utf-8-sig", errors="replace").strip()
    else:
        raw_text = f"> MinerU 未返回可用 Markdown。错误信息：{record.err_msg or record.state}"

    category = guess_category(record.source_path.name, raw_text)
    material_date = guess_material_date(record.source_path, raw_text)
    material_name = infer_material_name(record.source_path, raw_text)
    md_name = unique_md_name(f"{material_date}-{category_label(category)}-{material_name}", seen)
    out_path = output_dir / "materials" / category / md_name

    lines = [
        f"# {material_name}",
        "",
        f"- 原文件：{record.source_path}",
        f"- 材料产生时间：{material_date}",
        f"- 材料名称：{material_name}",
        f"- 分类：{category_label(category)}",
        f"- 规范文件名：{md_name}",
        f"- 类型：{guess_type(record.source_path)}",
        "- 来源：MinerU 精准解析 API",
        "- 是否 OCR：是",
        "- 处理说明：MinerU 解析结果已整理为 Markdown",
        "- 引用建议：需人工复核",
        "",
    ]
    lines.extend(["## 正文", "", raw_text, ""])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "source": str(record.source_path),
        "material_date": material_date,
        "material_name": material_name,
        "category": category,
        "md_name": md_name,
        "md_path": relative_link(out_path, output_dir),
        "type": guess_type(record.source_path),
        "ocr": "是",
        "quote": "需人工复核",
    }


def write_evidence_image(source: SourceFile, output_dir: Path, seen: dict[str, int]) -> dict[str, str]:
    category = "C_当事人提交的证据材料"
    material_date = guess_material_date(source.path)
    material_name = clean_material_name(source.path)
    md_name = unique_md_name(f"{material_date}-{category_label(category)}-{material_name}-图片证据索引", seen)
    out_path = output_dir / "materials" / category / md_name
    content = "\n".join(
        [
            f"# {material_name}",
            "",
            f"- 原文件：{source.path}",
            f"- 材料产生时间：{material_date}",
            f"- 材料名称：{material_name}",
            f"- 分类：{category_label(category)}",
            f"- 规范文件名：{md_name}",
        "- 类型：图片证据",
        "- 来源：原始图片目录",
        "- 是否 OCR：否",
        "- 处理说明：现场/实物/伤情类图片按图片证据索引处理，未强行 OCR 为正文",
        "- 引用建议：需结合原图人工复核",
        "",
        "## 图片证据索引",
            "",
            f"- 原图路径：{source.path}",
            "- 复核事项：确认图片内容、拍摄时间、与案件事实的关联性。",
            "",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return {
        "source": str(source.path),
        "material_date": material_date,
        "material_name": material_name,
        "category": category,
        "md_name": md_name,
        "md_path": relative_link(out_path, output_dir),
        "type": "图片证据",
        "ocr": "否",
        "quote": "需人工复核",
    }


def write_text_material(source: SourceFile, output_dir: Path, seen: dict[str, int]) -> dict[str, str]:
    raw_text = source.path.read_text(encoding="utf-8-sig", errors="replace").strip()
    category = guess_category(source.path.name, raw_text)
    material_date = guess_material_date(source.path, raw_text)
    material_name = infer_material_name(source.path, raw_text)
    md_name = unique_md_name(f"{material_date}-{category_label(category)}-{material_name}", seen)
    out_path = output_dir / "materials" / category / md_name
    lines = [
        f"# {material_name}",
        "",
        f"- 原文件：{source.path}",
        f"- 材料产生时间：{material_date}",
        f"- 材料名称：{material_name}",
        f"- 分类：{category_label(category)}",
        f"- 规范文件名：{md_name}",
        f"- 类型：{guess_type(source.path)}",
        "- 来源：原始文本文件",
        "- 是否 OCR：否",
        "- 处理说明：原始文本已整理为 Markdown",
        "- 引用建议：需人工复核",
        "",
        "## 正文",
        "",
        raw_text,
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "source": str(source.path),
        "material_date": material_date,
        "material_name": material_name,
        "category": category,
        "md_name": md_name,
        "md_path": relative_link(out_path, output_dir),
        "type": guess_type(source.path),
        "ocr": "否",
        "quote": "需人工复核",
    }


def write_manifest(output_dir: Path, rows: list[dict[str, str]], case_name: str) -> None:
    lines = [
        f"# {case_name} 材料清单",
        "",
        "| 序号 | 原文件 | 材料产生时间 | 材料名称 | 分类目录 | 规范文件名 | 输出 Markdown | 类型 | 是否 OCR | 引用建议 | 备注 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"| {idx} | `{row['source']}` | {row['material_date']} | {row['material_name']} | {row['category']} | `{row['md_name']}` | `{row['md_path']}` | {row['type']} | {row['ocr']} | {row['quote']} | |"
        )
    (output_dir / "00_材料清单.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reading_order(output_dir: Path, rows: list[dict[str, str]], case_name: str) -> None:
    ordered = sorted(rows, key=lambda row: (row["material_date"], row["category"], row["material_name"]))
    lines = [f"# {case_name} 阅读顺序", "", "## 优先阅读"]
    for row in ordered:
        if row["category"] in {"A_法院及仲裁机构文件", "B_当事人主张材料", "C_当事人提交的证据材料", "D_第三方客观材料"}:
            lines.append(f"- [{row['material_name']}]({row['md_path']})")
    lines.extend(["", "## 第二轮阅读"])
    for row in ordered:
        if row["category"] not in {"A_法院及仲裁机构文件", "B_当事人主张材料", "C_当事人提交的证据材料", "D_第三方客观材料"}:
            lines.append(f"- [{row['material_name']}]({row['md_path']})")
    lines.extend(["", "## 待人工复核"])
    for row in ordered:
        if row["quote"] == "需人工复核":
            lines.append(f"- [{row['material_name']}]({row['md_path']})")
    (output_dir / "01_阅读顺序.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_case_output(
    output_dir: Path,
    case_name: str,
    records: list[ParsedRecord],
    evidence_sources: list[SourceFile],
    text_sources: list[SourceFile],
) -> list[dict[str, str]]:
    ensure_case_dirs(output_dir)
    seen: dict[str, int] = {}
    rows: list[dict[str, str]] = []
    for record in records:
        rows.append(wrap_markdown(record, output_dir, seen))
    for source in evidence_sources:
        rows.append(write_evidence_image(source, output_dir, seen))
    for source in text_sources:
        rows.append(write_text_material(source, output_dir, seen))
    write_manifest(output_dir, rows, case_name)
    write_reading_order(output_dir, rows, case_name)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a litigation material folder into Markdown case materials.")
    parser.add_argument("input_dir", help="Folder containing raw litigation materials.")
    parser.add_argument("--output-dir", help="Output folder. Default: input_dir/md诉讼材料")
    parser.add_argument("--case-name", help="Case name. Default: input folder name")
    parser.add_argument("--cache-dir", help="MinerU cache folder. Default: output_dir/_mineru_cache")
    parser.add_argument("--from-records", help="Use an existing records.json instead of calling MinerU.")
    parser.add_argument("--no-api", action="store_true", help="Only create skeleton/manifests; do not call MinerU.")
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=1800, help="MinerU polling timeout in seconds.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.exists():
        print(f"ERROR: input folder not found: {input_dir}", file=sys.stderr)
        return 2
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else input_dir / "md诉讼材料"
    cache_dir = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else output_dir / "_mineru_cache"
    case_name = args.case_name or input_dir.name

    ensure_case_dirs(output_dir)
    sources = collect_sources(input_dir, output_dir)
    mineru_sources = [source for source in sources if source.submit_to_mineru]
    evidence_sources = [source for source in sources if source.evidence_only]
    text_sources = [
        source for source in sources if not source.submit_to_mineru and not source.evidence_only
    ]

    if args.from_records:
        records = load_records(Path(args.from_records).expanduser().resolve())
    elif args.no_api:
        records = [
            ParsedRecord(
                file_name=source.path.name,
                data_id=source.data_id,
                state="skipped",
                err_msg="--no-api",
                source_path=source.path,
                full_md_path=None,
                zip_path=None,
            )
            for source in mineru_sources
        ]
    else:
        if not mineru_sources:
            records = []
        else:
            config = load_config()
            if not config.get("MINERU_API_TOKEN", "").strip():
                print(MINERU_SETUP_GUIDE, file=sys.stderr)
                return 2
            print(f"Submitting {len(mineru_sources)} file(s) to MinerU Precision API", flush=True)
            try:
                result = submit_mineru_batch(mineru_sources, config, args.poll_interval, args.timeout)
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            records = download_and_extract_results(result, mineru_sources, cache_dir)
            write_records(cache_dir / "records.json", records)

    rows = build_case_output(output_dir, case_name, records, evidence_sources, text_sources)
    print(f"Output folder: {output_dir}")
    print(f"Materials: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
