# 诉讼材料 Markdown 整理 Skill

[English](README_EN.md)

将 PDF、扫描件、Word、图片、聊天记录等诉讼材料整理成适合 AI 阅读、定位、引用和复核的 Markdown 案件材料目录。

这个 Skill 用于法律分析之前的材料入口治理。它先调用 MinerU API 将可文本化材料转成 Markdown，再按照材料来源和诉讼用途归档，生成材料清单和阅读顺序。后续 Agent 可以从同一套目录继续完成事实梳理、证据核查、法律检索和文书起草。

## 主要功能

- 检查并引导配置 MinerU API Token
- 转换 PDF、扫描件、Word、PPT、图片、TXT 和 Markdown
- 为不适合 OCR 的现场或实物图片建立证据索引
- 记录原文件路径、材料时间、分类、OCR 状态、引用建议和复核提示
- 生成 `00_材料清单.md` 和 `01_阅读顺序.md`
- 将无法确定来源、版本或材料性质的文件送入待人工复核目录

## 分类体系

| 目录 | 内容 |
|---|---|
| `A_法院及仲裁机构文件` | 传票、裁定、判决、通知书、庭审笔录等 |
| `B_当事人主张材料` | 起诉状、答辩状、申请书、情况说明等 |
| `C_当事人提交的证据材料` | 合同、付款凭证、聊天记录、邮件、照片等 |
| `D_第三方客观材料` | 银行流水、公证书、鉴定意见、评估报告等 |
| `E_律师制作文书` | 代理意见、质证意见、证据目录、工作备忘录等 |
| `F_AI过程文件` | OCR 结果、事实时间线草稿、检索记录等 |
| `Z_待人工复核` | 来源、时间、版本、OCR 质量或材料性质暂时无法判断的文件 |

## 安装

需要 Python 3.10 或更高版本。

```bash
git clone https://github.com/SimbaCD/legal-material-intake-markdown.git
cd legal-material-intake-markdown
pip install -r requirements.txt
```

将仓库目录放入 Agent 的 Skills 目录，或在需要时直接调用脚本。

## 配置 MinerU API

1. 打开 [MinerU API 页面](https://mineru.net/apiManage/docs?openApplyModal=true)
2. 登录或注册 MinerU / OpenDataLab 账号
3. 在 API 管理页面申请或复制 API Token
4. 在当前项目目录或 Skill 目录新建 `mineru.env`
5. 写入：

```env
MINERU_API_TOKEN=你的Token
MINERU_API_BASE=https://mineru.net/api/v4
MINERU_MODEL_VERSION=pipeline
MINERU_LANGUAGE_CODE=ch
MINERU_ENABLE_OCR=true
MINERU_ENABLE_TABLE=true
MINERU_ENABLE_FORMULA=false
```

`mineru.env` 已加入 `.gitignore`。请勿将 Token 写入仓库、聊天记录或公开文档。

## 使用

```bash
python scripts/intake_case.py "D:/path/to/案件材料目录"
```

指定输出目录：

```bash
python scripts/intake_case.py "D:/path/to/案件材料目录" --output-dir "D:/path/to/输出目录"
```

运行后会生成：

```text
md诉讼材料/
├── 00_材料清单.md
├── 01_阅读顺序.md
└── materials/
```

## 保密提示

真实案件材料上传云端前，应确认客户授权、保密义务和脱敏要求。OCR 结果、自动分类和后续法律结论都需要律师复核。

## 授权

本项目采用 [Source-Available Personal Use License](LICENSE)。可以下载、学习、个人使用和内部试用；再分发、商业托管或作为商业产品的一部分使用，需要另行取得书面授权。

## Star History

<a href="https://www.star-history.com/?legend=top-left&repos=SimbaCD%2Flegal-material-intake-markdown&type=date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=SimbaCD/legal-material-intake-markdown&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=SimbaCD/legal-material-intake-markdown&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=SimbaCD/legal-material-intake-markdown&type=date&legend=top-left" />
  </picture>
</a>
