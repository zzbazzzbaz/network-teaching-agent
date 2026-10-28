# 计算机网络教材 OCR

将扫描版《计算机网络（第 8 版）》经 MinerU 云 API 转成按小节拆分的 Markdown，并生成 `teach_agent` 的 `computer-networks` skill 资源。

## 目录

```text
docs/pdf_ocr/
├── .env                  # MINERU_API_KEY，禁止提交
├── input/                # 源 PDF，禁止提交
├── raw/                  # 上传分片、MinerU ZIP、图片，禁止提交
├── work/                 # outline、pages.jsonl、units.json，禁止提交
├── generated/            # 生成的 skill 资源，验收后同步
└── scripts/              # 生产脚本
```

## 首次配置

```bash
cd docs/pdf_ocr
cp .env.example .env
# 编辑 .env，填入 MINERU_API_KEY
uv sync
```

源 PDF 放到：

```text
docs/pdf_ocr/input/计算机网络（第8版）(谢希仁).pdf
```

## 全量流程

```bash
cd docs/pdf_ocr

# 1. 书签与章节结构
uv run python scripts/extract_outline.py

# 2. 拆 PDF（每片 ≤ 200 页，按章节边界）
uv run python scripts/split_pdf.py

# 3. 上传、轮询、下载（支持跳过已有结果）
uv run python scripts/run_mineru_api.py --model vlm --timeout 3600

# 4. 归一化为页级块
uv run python scripts/normalize_api_output.py

# 5. 复制全部教材图片（含子图/无图注大图）并生成索引
uv run python scripts/build_figures.py

# 6. 用视觉模型生成 figures/descriptions/*.md（可中断续跑）
uv run python scripts/describe_figures.py --workers 1 --timeout 180

# 7. 生成小节 Markdown（正文会嵌入图片链接和图示说明链接）
uv run python scripts/build_sections.py

# 8. 生成目录、索引和页码 JSON
uv run python scripts/build_index.py

# 9. 生成 SKILL.md
uv run python scripts/build_skill.py

# 10. 校验
uv run python scripts/validate_pages.py

# 11. 同步到 agent skill
uv run python scripts/promote_to_skill.py --clean
```

## 样张

样张只用于确认 API/模型质量，不用于最终 skill：

```bash
uv run python scripts/split_pdf.py --range 12-20 --part-id sample-vlm
uv run python scripts/run_mineru_api.py --part sample-vlm-012-020 --model vlm
uv run python scripts/normalize_api_output.py --part sample-vlm-012-020
```

跑完样张后重新执行全量 `split_pdf.py`，否则 `work/parts.json` 仍只包含样张。

## 图示说明

图片说明通过本机已登录的 `opencode` CLI 调用视觉模型生成：

```bash
uv run python scripts/describe_figures.py --workers 1 --timeout 180
```

默认模型：

```text
opencode/nemotron-3.5-super-vl-free
```

可通过 `OPENCODE_VL_MODEL` 覆盖。默认只使用免费模型，不自动切换付费模型；
免费额度耗尽时脚本停止。说明写入：

```text
figures/descriptions/<章节目录>/<图片名>.md
```

说明是 AI 辅助内容，`reviewed: false`；教材原图、图注和页码优先。重复运行会跳过已有 SHA 匹配的说明，`--force` 可强制重生成。

## 本次全量结果（2026-10-27）

- 源 PDF：485 页，SHA-256 `ff70e7208d5d6c610441d7496408dfa68c5ed243503486330e38d8b8216ad19b`
- MinerU：`vlm`，4 个 part，batch `c3e116eb-4551-4b38-9171-b151ef4daa65`
- 归一化：485 页（第 485 页为空白页）
- 教材资源：179 个小节文件（每章“本章的重要概念”保留在对应章节目录中）
- 图表：333 张教材图片（含子图和无图注大图，排除二维码/视频入口）全部收录，并嵌入对应小节
- 校验：`validate_pages.py` 通过
- 已同步：`apps/agent/agent/resources/skills/teaching/computer-networks/`

## 关键约定

- `book_page = pdf_page - 11`，PDF 第 12 页是教材第 1 页。
- skill 小节 frontmatter 只有 `section`、`title`、`book_pages`。
- PDF 页码只保存在 `work/pages/pages.jsonl` 和 `raw/mineru/source.json`。
- 教材图片全量收录到 `figures/`，正文使用相对链接引用；原图仍保留在 `raw/`。
- `.env`、`input/`、`raw/`、`work/` 不提交。
