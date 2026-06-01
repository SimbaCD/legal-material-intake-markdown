#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def guess_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "PDF"
    if ext in {".doc", ".docx"}:
        return "DOCX"
    if ext in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}:
        return "图片"
    if ext in {".txt", ".md"}:
        return "文本"
    if ext in {".xls", ".xlsx", ".csv"}:
        return "表格"
    return ext.lstrip(".").upper() or "未知"


def guess_ocr(type_name: str) -> str:
    if type_name in {"图片"}:
        return "建议 OCR"
    if type_name == "PDF":
        return "视是否扫描件而定"
    if type_name == "DOCX":
        return "通常不需 OCR"
    return "按需处理"


def guess_category(name: str) -> str:
    lowered = name.lower()
    if any(k in lowered for k in ["判决", "裁定", "传票", "庭审", "受理", "举证通知", "开庭", "调解书", "仲裁"]):
        return "A_法院及仲裁机构文件"
    if any(k in lowered for k in ["ocr", "mineru", "ai分析", "材料清单", "阅读顺序", "事实时间线", "证据核查", "检索记录", "草稿", "draft"]):
        return "F_AI过程文件"
    if any(k in lowered for k in ["起诉状", "答辩状", "反诉状", "上诉状", "再审申请", "申请书", "情况说明", "事实陈述", "陈述书", "申诉书", "保全申请", "调查取证申请", "调查令申请", "执行申请"]):
        return "B_当事人主张材料"
    if any(k in lowered for k in ["代理词", "代理意见", "质证意见", "证据目录", "法律意见", "律师函", "庭审提纲", "工作备忘录"]):
        return "E_律师制作文书"
    if any(k in lowered for k in ["鉴定", "评估", "审计", "专家意见", "公证", "银行流水", "工商", "征信", "检测"]):
        return "D_第三方客观材料"
    if any(k in lowered for k in ["合同", "协议", "订单", "确认单", "付款", "发票", "收据", "微信", "wechat", "聊天记录", "聊天截图", "邮件", "函", "沟通", "通知", "短信", "照片", "录音", "凭证"]):
        return "C_当事人提交的证据材料"
    return "Z_待人工复核"


def category_label(category: str) -> str:
    if "_" in category:
        return category.split("_", 1)[1]
    return category


def guess_material_date(path: Path) -> str:
    name = path.stem
    patterns = [
        r"(?P<y>20\d{2}|19\d{2})[.\-_年](?P<m>1[0-2]|0?[1-9])[.\-_月](?P<d>3[01]|[12]\d|0?[1-9])日?",
        r"(?P<y>20\d{2}|19\d{2})(?P<m>0[1-9]|1[0-2])(?P<d>0[1-9]|[12]\d|3[01])",
        r"(?P<y>20\d{2}|19\d{2})[.\-_年](?P<m>1[0-2]|0?[1-9])月?",
        r"(?P<y>20\d{2}|19\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if not match:
            continue
        year = match.group("y")
        month = match.groupdict().get("m")
        day = match.groupdict().get("d")
        if month and day:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        if month:
            return f"{year}-{int(month):02d}"
        return year
    return "未明日期"


def clean_material_name(path: Path) -> str:
    name = path.stem.strip()
    date_patterns = [
        r"^(20\d{2}|19\d{2})[.\-_年]?(1[0-2]|0?[1-9])?[.\-_月]?(3[01]|[12]\d|0?[1-9])?日?[\s.\-_]*",
        r"[\s.\-_]*(20\d{2}|19\d{2})[.\-_年](1[0-2]|0?[1-9])([.\-_月](3[01]|[12]\d|0?[1-9])日?)?[\s.\-_]*$",
    ]
    for pattern in date_patterns:
        name = re.sub(pattern, "", name).strip()
    name = re.sub(r"[<>:\"/\\|?*\r\n\t]+", "-", name)
    name = re.sub(r"\s+", "", name)
    name = re.sub(r"-{2,}", "-", name).strip(" .-_")
    if not name:
        return "未命名材料"
    return name[:80]


def canonical_filename(date_text: str, category: str, material_name: str, seen: dict[str, int]) -> str:
    base = f"{date_text}-{category_label(category)}-{material_name}"
    base = re.sub(r"[<>:\"/\\|?*\r\n\t]+", "-", base)
    base = re.sub(r"-{2,}", "-", base).strip(" .-_")
    count = seen.get(base, 0) + 1
    seen[base] = count
    if count > 1:
        base = f"{base}-{count:02d}"
    return f"{base}.md"


def quote_hint(type_name: str) -> str:
    if type_name in {"文本", "DOCX"}:
        return "通常可直接引用"
    if type_name in {"图片"}:
        return "需人工复核"
    if type_name == "PDF":
        return "视抽取质量而定"
    return "按需判断"


def collect_files(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in source_dir.rglob("*"):
        if path.is_file():
            files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a markdown material manifest from a source directory.")
    parser.add_argument("--source-dir", required=True, help="Directory containing original materials.")
    parser.add_argument("--output", required=True, help="Target markdown file path.")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    files = collect_files(source_dir)

    lines = [
        f"# {source_dir.name} 材料清单",
        "",
        "| 序号 | 原文件 | 材料产生时间 | 材料名称 | 分类目录 | 规范文件名 | 输出 Markdown | 类型 | 是否 OCR | 引用建议 | 备注 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    seen_names: dict[str, int] = {}

    for idx, path in enumerate(files, start=1):
        rel = path.relative_to(source_dir).as_posix()
        type_name = guess_type(path)
        ocr = guess_ocr(type_name)
        category = guess_category(path.name)
        quote = quote_hint(type_name)
        material_date = guess_material_date(path)
        material_name = clean_material_name(path)
        md_name = canonical_filename(material_date, category, material_name, seen_names)
        md_path = f"materials/{category}/{md_name}"
        lines.append(
            f"| {idx} | `{rel}` | {material_date} | {material_name} | {category} | `{md_name}` | `{md_path}` | {type_name} | {ocr} | {quote} | |"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
