---
name: material-intake-markdown
description: 将诉讼、仲裁或争议解决材料转换成适合 AI 阅读、定位、引用和复核的 Markdown 材料文件夹。用户需要整理 PDF、扫描件、Word、图片、聊天记录、邮件、法院文件、当事人材料、律师文书或 AI 过程文件时使用；优先确认 MinerU API 配置，再生成材料清单、阅读顺序、分类目录和待复核标记。
---

# Material Intake Markdown

## 核心目标

把原始案件材料整理成一个可交给下游 AI 分析的 Markdown 材料体系。

这里的“材料原生化”包含三件事：

1. **可读取**：把 PDF、扫描件、Word、图片、聊天记录等材料转换成 AI 可以处理的 Markdown 文本或图片证据索引。
2. **可定位**：每份材料都保留原文件、材料时间、材料名称、来源分类、规范文件名和输出路径，便于回到原件。
3. **可复核**：把 OCR 质量、引用建议、待人工复核事项写进材料清单和单份材料头部，避免下游分析混用未复核内容。

最终输出至少包含：

- `00_材料清单.md`
- `01_阅读顺序.md`
- `materials/` 分类目录

默认目录：

```text
[案件名]/
├── 00_材料清单.md
├── 01_阅读顺序.md
└── materials/
    ├── A_法院及仲裁机构文件/
    ├── B_当事人主张材料/
    ├── C_当事人提交的证据材料/
    ├── D_第三方客观材料/
    ├── E_律师制作文书/
    ├── F_AI过程文件/
    └── Z_待人工复核/
```

## 启动步骤

收到材料整理请求后，先确认 MinerU API 配置。

优先检查：

1. 环境变量 `MINERU_API_TOKEN`
2. 当前工作目录下的 `.env` 或 `mineru.env`
3. 本 Skill 目录下的 `.env` 或 `mineru.env`

如果没有检测到 `MINERU_API_TOKEN`，先引导用户完成配置，再继续材料转换。引导步骤保持简单：

1. 打开 MinerU API 页面：`https://mineru.net/apiManage/docs?openApplyModal=true`
2. 登录或注册 MinerU / OpenDataLab 账号
3. 在 API 管理页面申请或复制 API Token
4. 在当前项目目录或 Skill 目录新建 `mineru.env`
5. 写入 `MINERU_API_TOKEN=你的Token`
6. 重新运行 `python scripts/intake_case.py "D:/path/to/案件材料目录"`

配置文件格式：

```env
MINERU_API_TOKEN=your_token_here
MINERU_API_BASE=https://mineru.net/api/v4
MINERU_MODEL_VERSION=pipeline
MINERU_LANGUAGE_CODE=ch
MINERU_ENABLE_OCR=true
MINERU_ENABLE_TABLE=true
MINERU_ENABLE_FORMULA=false
```

Token 不要写入仓库、聊天记录、材料输出或公开文档。公开发布前确认 `.env`、`mineru.env` 和 `_mineru_cache/` 已被排除。

## 正常执行

主入口只有一个：

```bash
python scripts/intake_case.py "D:/path/to/案件材料目录"
```

指定输出目录：

```bash
python scripts/intake_case.py "D:/path/to/案件材料目录" --output-dir "D:/path/to/输出目录"
```

这个脚本负责：

1. 盘点原始文件
2. 提交 MinerU 精准解析 API
3. 下载 Markdown 结果
4. 按来源和诉讼用途分类放入 `materials/`
5. 规范命名
6. 生成材料清单和阅读顺序
7. 标记待人工复核事项

## 分类规则

分类时同时考虑材料来源和材料在案件中的作用。即使文件都由当事人提交，也要继续区分当事人的主张和支持主张的证据材料。

### A_法院及仲裁机构文件

法院、仲裁机构、行政机关形成或送达的文件。

常见材料：传票、裁定、判决、决定书、通知书、受理通知、举证通知、开庭通知、庭审笔录、调解书、仲裁文书。

### B_当事人主张材料

当事人提出的事实陈述、诉讼请求、抗辩理由和程序申请。这类材料反映当事人的主张，后续分析时需要继续核对证据支持情况。

常见材料：起诉状、答辩状、反诉状、上诉状、申请书、情况说明、事实陈述、陈述书。

### C_当事人提交的证据材料

当事人提交的交易、履行和沟通材料。后续分析时，应结合具体证明对象判断其证明作用。

常见材料：合同、协议、订单、确认单、付款凭证、发票、收据、微信聊天记录、邮件、短信、通知函、照片、录音整理。

### D_第三方客观材料

银行、公证、鉴定、审计、评估、登记、检测等第三方或机构形成的客观材料。

常见材料：银行流水、公证书、鉴定意见、评估报告、审计报告、登记信息、检测报告、专家意见。

### E_律师制作文书

律师或法律团队制作的工作成果和对外文书。

常见材料：代理词、代理意见、质证意见、证据目录、法律意见书、律师函、庭审提纲、工作备忘录。

### F_AI过程文件

AI 或自动化流程生成的中间文件。

常见材料：OCR 结果、MinerU 结果、材料清单、阅读顺序、事实时间线草稿、证据核查表、检索记录、AI 分析草稿。

### Z_待人工复核

来源、时间、版本、OCR 质量或材料性质暂时无法判断的文件。

## 单份材料 Markdown

每份可读材料优先输出为一个 Markdown 文件。头部建议包含：

```markdown
# [材料标题]

- 原文件：...
- 材料产生时间：...
- 材料名称：...
- 分类：...
- 规范文件名：...
- 类型：PDF / Office / 内容图片 / 图片证据 / 文本
- 来源：MinerU 精准解析 API / 手工整理 / 图片证据索引
- 是否 OCR：是 / 否 / 待处理
- 处理说明：...
- 引用建议：可直接引用 / 需人工复核

## 正文
```

## 材料清单

`00_材料清单.md` 是下游 AI 分析的入口。每一行至少记录：

- 原文件名
- 材料产生时间
- 材料名称
- 分类目录
- 规范文件名
- 输出 Markdown 路径
- 类型
- 是否 OCR
- 引用建议
- 备注

材料清单要保留原文件路径，便于后续复核和回看原件。

## 命名规则

处理后的 Markdown 文件名使用：

```text
YYYY-MM-DD-分类-材料名称.md
```

无法判断日期时使用：

```text
未明日期-分类-材料名称.md
```

材料产生时间优先取正文中的落款、签署、发送、出具、形成或拍摄时间；其次取原文件名、元数据或用户说明。出生日期、身份证日期、护照日期等个人信息日期不作为材料产生时间。

## 交接给下游分析

交给下游法律分析或检索 Skill 前，确认：

- `00_材料清单.md` 已生成
- `01_阅读顺序.md` 已生成
- `materials/` 下存在可读 Markdown
- 待复核材料已标入 `Z_待人工复核` 或在清单备注中标明
- 每份材料都能从清单回到原文件和对应 Markdown

下游通常接入 `legal-research-analysis`。

## 参考文件

- MinerU API 细节：`references/mineru-api.md`
- 输出格式：`references/output-format.md`
- 工作流说明：`references/workflow.md`
