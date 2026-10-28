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

# 6. 生成小节 Markdown（正文嵌入图片链接）
uv run python scripts/build_sections.py

# 7. 生成目录、索引和页码 JSON
uv run python scripts/build_index.py

# 8. 生成 SKILL.md
uv run python scripts/build_skill.py

# 9. 校验
uv run python scripts/validate_pages.py

# 10. 同步到 agent skill
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

## 关键约定

- `book_page = pdf_page - 11`，PDF 第 12 页是教材第 1 页。
- skill 小节 frontmatter 只有 `section`、`title`、`book_pages`。
- PDF 页码只保存在 `work/pages/pages.jsonl` 和 `raw/mineru/source.json`。
- 教材图片全量收录到 `figures/`，正文使用相对链接引用；原图仍保留在 `raw/`。
- `.env`、`input/`、`raw/`、`work/` 不提交。
