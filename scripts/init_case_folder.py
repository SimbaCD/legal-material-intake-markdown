#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


DIRS = [
    "materials/A_法院及仲裁机构文件",
    "materials/B_当事人主张材料",
    "materials/C_当事人提交的证据材料",
    "materials/D_第三方客观材料",
    "materials/E_律师制作文书",
    "materials/F_AI过程文件",
    "materials/Z_待人工复核",
]


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a Markdown case folder for litigation materials."
    )
    parser.add_argument("--case-name", required=True, help="Case name shown in the markdown files.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the case folder will be created.",
    )
    args = parser.parse_args()

    root = Path(args.output_dir).expanduser().resolve() / args.case_name
    root.mkdir(parents=True, exist_ok=True)

    for rel in DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)

    write_if_missing(
        root / "00_材料清单.md",
        f"# {args.case_name} 材料清单\n\n"
        "| 序号 | 原文件 | 材料产生时间 | 材料名称 | 分类目录 | 规范文件名 | 输出 Markdown | 类型 | 是否 OCR | 引用建议 | 备注 |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n",
    )
    write_if_missing(
        root / "01_阅读顺序.md",
        f"# {args.case_name} 阅读顺序\n\n"
        "## 优先阅读\n- \n\n"
        "## 第二轮阅读\n- \n\n"
        "## 待人工复核\n- \n",
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
