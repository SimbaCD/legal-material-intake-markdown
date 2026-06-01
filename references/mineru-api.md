# MinerU API

## Auto 模式

正常执行时不要搜索网页或打开 MinerU 在线文档；本文件就是 API 调用依据。只有 API 返回参数错误、认证错误，或用户明确要求核对官方文档时，才查官方文档。

优先级：

1. 如果 `MINERU_API_TOKEN` 已配置，使用精准解析 API。
2. 如果没有 Token，先引导用户完成 MinerU API Token 配置。
3. 如果材料不能上传云端、API 不可用或超出限制，回退本地工具。

配置读取顺序：

1. 环境变量
2. 当前工作目录下的 `.env` 或 `mineru.env`
3. 当前 skill 目录下的 `.env` 或 `mineru.env`

不要把 Token 写入 Git 仓库、`SKILL.md`、输出 Markdown 或材料清单。

## 无 Token 时的用户引导

检测不到 `MINERU_API_TOKEN` 时，先暂停材料转换，向用户显示最短配置步骤：

1. 打开 MinerU API 页面：`https://mineru.net/apiManage/docs?openApplyModal=true`
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

6. 保存后重新运行：

```bash
python scripts/intake_case.py "D:/path/to/案件材料目录"
```

提醒用户：Token 只放在本机环境变量或本地 `mineru.env`，不要发送到聊天窗口，不要提交到 GitHub。

## 精准解析 API

适用：

- 长 PDF
- 扫描型 PDF
- 表格密集材料
- 复杂版式
- 需要 Markdown + JSON + Zip 结果包

默认配置：

```text
MINERU_API_BASE=https://mineru.net/api/v4
MINERU_MODEL_VERSION=pipeline
MINERU_LANGUAGE_CODE=ch
MINERU_ENABLE_OCR=true
MINERU_ENABLE_TABLE=true
MINERU_ENABLE_FORMULA=false
```

法律材料默认使用 `pipeline`，优先稳定和低幻觉；只有扫描质量差、版式复杂或图表很多时，再考虑 `vlm`。

本地文件按官方“文件批量上传解析”流程：

1. `POST {MINERU_API_BASE}/file-urls/batch`，请求体包含 `files`、`model_version`、`language`、`enable_table`、`enable_formula`。
2. 使用返回的 `file_urls` 对每个文件执行 `PUT` 上传。
3. 无须额外提交任务，上传完成后服务端会自动解析。
4. 用 `GET {MINERU_API_BASE}/extract-results/batch/{batch_id}` 轮询状态。
5. 完成后下载 `full_zip_url`，其中 `full.md` 是 Markdown 解析结果。

请求体中的每个文件项应包含：

```json
{"name": "demo.pdf", "data_id": "material_0001", "is_ocr": true}
```

正常执行不要手写 API 代码，使用 `scripts/intake_case.py`。只有维护脚本或修复接口时才需要查看本参考。

远程 URL 按官方“单个文件解析”流程：

1. `POST {MINERU_API_BASE}/extract/task`，请求体包含 `url` 和 `model_version`。
2. 用 `GET {MINERU_API_BASE}/extract/task/{task_id}` 轮询状态。
3. 完成后下载 `full_zip_url`，其中 `full.md` 是 Markdown 解析结果。

## Agent 轻量解析 API

适用：

- 快速试跑
- 小文件
- 少页数材料
- 用户明确要求免 Token 试跑时的临时方案

默认配置：

```text
MINERU_AGENT_API_BASE=https://mineru.net/api/v1/agent
```

轻量接口受 IP 限频、文件大小和页数限制影响；失败时不要反复重试，应提示配置 Token 或回退本地工具。

轻量接口按官方签名上传流程：

1. `POST {MINERU_AGENT_API_BASE}/parse/file` 获取 `task_id` 和 `file_url`。
2. `PUT file_url` 上传本地文件。
3. `GET {MINERU_AGENT_API_BASE}/parse/{task_id}` 轮询结果。
4. 完成后下载 `markdown_url`。

## 保密边界

真实案件材料上传云端前应确认授权和脱敏要求。若材料不适合上传，使用本地 MarkItDown / PyMuPDF / Umi-OCR，并在材料清单中标注识别质量和人工复核需求。
