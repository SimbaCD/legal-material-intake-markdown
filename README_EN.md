# Litigation Material Intake Markdown Skill

[中文说明](README.md)

Convert PDFs, scanned documents, Word files, images, and chat records into a Markdown case-material directory that AI agents can read, locate, cite, and review.

This Skill prepares litigation materials before legal analysis begins. It uses the MinerU API to convert text-readable files into Markdown, classifies files by source and litigation purpose, and generates a material manifest and reading order. Downstream agents can continue with fact review, evidence checks, legal research, and drafting from the same directory.

## Features

- Check for a MinerU API Token and guide users through setup
- Convert PDFs, scanned files, Word documents, PPT files, images, TXT, and Markdown
- Create evidence indexes for scene or physical-object images that should not be forced through OCR
- Preserve source paths, material dates, categories, OCR status, citation guidance, and review notes
- Generate `00_材料清单.md` and `01_阅读顺序.md`
- Route files with unclear source, version, or document type to a manual-review directory

## Classification

| Directory | Contents |
|---|---|
| `A_法院及仲裁机构文件` | Court and arbitration documents |
| `B_当事人主张材料` | Pleadings, responses, applications, and party statements |
| `C_当事人提交的证据材料` | Contracts, payment records, chats, emails, and photos |
| `D_第三方客观材料` | Bank records, notarizations, appraisal opinions, and assessment reports |
| `E_律师制作文书` | Lawyer work product, evidence lists, and review notes |
| `F_AI过程文件` | OCR results, draft timelines, and research notes |
| `Z_待人工复核` | Files that require manual review |

## Installation

Python 3.10 or later is required.

```bash
git clone https://github.com/SimbaCD/legal-material-intake-markdown.git
cd legal-material-intake-markdown
pip install -r requirements.txt
```

Place the repository directory in your agent's Skills directory, or call the scripts directly when needed.

## Configure the MinerU API

1. Open the [MinerU API page](https://mineru.net/apiManage/docs?openApplyModal=true)
2. Sign in or create a MinerU / OpenDataLab account
3. Apply for or copy an API Token
4. Create `mineru.env` in the current project directory or the Skill directory
5. Add:

```env
MINERU_API_TOKEN=your_token_here
MINERU_API_BASE=https://mineru.net/api/v4
MINERU_MODEL_VERSION=pipeline
MINERU_LANGUAGE_CODE=ch
MINERU_ENABLE_OCR=true
MINERU_ENABLE_TABLE=true
MINERU_ENABLE_FORMULA=false
```

`mineru.env` is ignored by Git. Do not commit Tokens or include them in chat messages or public documents.

## Usage

```bash
python scripts/intake_case.py "D:/path/to/case-materials"
```

Specify an output directory:

```bash
python scripts/intake_case.py "D:/path/to/case-materials" --output-dir "D:/path/to/output"
```

The script generates:

```text
md诉讼材料/
├── 00_材料清单.md
├── 01_阅读顺序.md
└── materials/
```

## Confidentiality

Before uploading real case materials to a cloud service, confirm client authorization, confidentiality obligations, and redaction requirements. Lawyers should review OCR results, automated classifications, and downstream legal conclusions.

## License

This project uses the [Source-Available Personal Use License](LICENSE). You may download, learn from, use personally, and evaluate internally. Redistribution, commercial hosting, or use as part of a commercial product requires separate written permission.

## Star History

<a href="https://www.star-history.com/?legend=top-left&repos=SimbaCD%2Flegal-material-intake-markdown&type=date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=SimbaCD/legal-material-intake-markdown&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=SimbaCD/legal-material-intake-markdown&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=SimbaCD/legal-material-intake-markdown&type=date&legend=top-left" />
  </picture>
</a>
