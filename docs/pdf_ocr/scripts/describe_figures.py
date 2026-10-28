#!/usr/bin/env python3
"""Generate sidecar descriptions for textbook figures via OpenCode vision model."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from common import (
    GENERATED_DIR,
    ROOT,
    WORK_DIR,
    ensure_dirs,
    fail,
    load_environment,
    read_json,
    sha256_file,
    write_json,
)

DEFAULT_API_MODEL = "gemini-4-argon"
DEFAULT_API_BASE = "https://opencode.ai/inference/go/openai/v1"
DEFAULT_MODEL = "opencode/nemotron-3.5-super-vl-free"
# Deliberately empty: the default run must never silently use a paid model.
DEFAULT_FALLBACK_MODEL = ""


class QuotaExceeded(RuntimeError):
    """Raised when the free model quota is exhausted."""


PROMPT = """你是计算机网络教材的图片描述助手。
只根据图片本身可见内容生成辅助说明，不要补充图外知识，不要复述教材正文，不要猜测看不清的文字。
请只输出以下 JSON，不要输出解释或 Markdown 代码围栏：
{
  "summary": "1-2 句中文概述，说明图片是什么、主要画了什么",
  "visible_text": ["图中清晰可见的标题、字段、标签、坐标轴或图例"],
  "structure": "用中文描述布局、节点、箭头方向、分层、流程或模块关系",
  "relations": ["图中最重要的 2-5 条关系或流程"],
  "uncertainties": ["无法辨认、被裁剪或可能识别错误的内容"],
  "confidence": 0.0
}
若图中有表格或公式，在 structure 中说明其行列/公式含义；看不清就写入 uncertainties。"""


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def quote_yaml(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {
        "summary": text,
        "visible_text": [],
        "structure": "",
        "relations": [],
        "uncertainties": ["模型未返回可解析的 JSON，已保留原始输出"],
        "confidence": 0.0,
    }


def image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def call_api(
    image_path: Path,
    base: str,
    key: str,
    model: str,
    prompt: str,
    timeout: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你只输出严格 JSON，不要输出解释或代码围栏。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_uri(image_path)}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-opencode-session": f"ses_ocr_{uuid.uuid4().hex}",
    }
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                f"{base.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            if response.status_code in (200, 201):
                content = response.json()["choices"][0]["message"].get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        part.get("text", "") for part in content if isinstance(part, dict)
                    )
                return extract_json(str(content))
            last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
            if response.status_code not in (408, 409, 429, 500, 502, 503, 504):
                break
        except (requests.RequestException, KeyError, ValueError) as exc:
            last_error = exc
        if attempt < 3:
            import time

            time.sleep(2**attempt)
    raise RuntimeError(f"vision API failed: {last_error}")


def call_opencode(image_path: Path, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    cmd = [
        "opencode",
        "run",
        "--model",
        model,
        "--file",
        str(image_path),
        "--format",
        "json",
        prompt,
    ]
    env = os.environ.copy()
    env.setdefault("OPENCODE_SESSION_ID", f"ocr-figures-{uuid.uuid4().hex}")
    try:
        process = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"opencode timed out after {timeout}s") from exc
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "").strip()[-800:]
        if (
            "FreeUsageLimitError" in detail
            or "provider.quota" in detail
            or "Free usage limit" in detail
        ):
            raise QuotaExceeded(detail)
        raise RuntimeError(f"opencode exited {process.returncode}: {detail}")
    texts: list[str] = []
    for line in process.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            part = event.get("part") or {}
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    content = "\n".join(texts).strip()
    if not content:
        content = process.stdout.strip()
    return extract_json(content)


def sidecar_text(
    row: dict[str, Any],
    result: dict[str, Any],
    model: str,
    source_sha: str,
) -> str:
    label = str(row.get("label") or "教材图片")
    caption = str(row.get("caption") or "")
    visible = result.get("visible_text") or []
    relations = result.get("relations") or []
    uncertainties = result.get("uncertainties") or []
    confidence = result.get("confidence")
    lines = [
        "---",
        f'figure: "{quote_yaml(label)}"',
        f'file: "{quote_yaml(str(row.get("file") or ""))}"',
        f"book_page: {row.get('book_page') or 'null'}",
        f'caption: "{quote_yaml(caption)}"',
        f'model: "{quote_yaml(model)}"',
        f'source_sha256: "{source_sha}"',
        f'generated_at: "{now_iso()}"',
        "reviewed: false",
        "---",
        "",
        f"# {label}",
        "",
        "## 概述",
        "",
        str(result.get("summary") or "模型未返回概述。"),
        "",
        "## 图中可见文字",
        "",
    ]
    if visible:
        lines.extend(f"- {item}" for item in visible)
    else:
        lines.append("- 未识别到清晰可读的文字。")
    lines.extend(["", "## 结构关系", "", str(result.get("structure") or "未返回结构描述。"), ""])
    if relations:
        lines.append("## 关系/流程")
        lines.append("")
        lines.extend(f"- {item}" for item in relations)
        lines.append("")
    lines.append("## 不确定项")
    lines.append("")
    if uncertainties:
        lines.extend(f"- {item}" for item in uncertainties)
    else:
        lines.append("- 无。")
    lines.extend(
        [
            "",
            f"> 本说明由视觉模型 `{model}` 生成，仅作辅助；以教材原图和图注为准。",
        ]
    )
    if confidence is not None:
        lines.append(f"> 模型置信度：{confidence}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ensure_dirs()
    env_file = load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("api", "cli"), default="cli")
    parser.add_argument("--base", default=os.environ.get("OPENCODE_GO_BASE", DEFAULT_API_BASE))
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENCODE_VL_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument(
        "--fallback-model",
        default=os.environ.get("OPENCODE_VL_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
    )
    parser.add_argument("--limit", type=int, default=0, help="only process N rows, for testing")
    parser.add_argument("--only", default="", help="process rows whose file/caption contains this")
    parser.add_argument("--force", action="store_true", help="overwrite existing sidecars")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    key = os.environ.get("OPENCODE_GO_API_KEY", "").strip()
    if args.backend == "api" and not key:
        fail("OPENCODE_GO_API_KEY is empty; set it in docs/pdf_ocr/.env")
    if args.backend == "cli" and "/" not in args.model:
        args.model = f"opencode/{args.model}"
    payload = read_json(WORK_DIR / "figures.json", {"figures": []})
    all_rows = payload.get("figures", [])
    if not all_rows:
        fail("work/figures.json missing; run build_figures.py first")
    rows = list(all_rows)
    if args.only:
        rows = [
            row
            for row in rows
            if args.only in str(row.get("file") or "") or args.only in str(row.get("caption") or "")
        ]
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        fail("no matching figures")

    root = GENERATED_DIR / "computer-networks"
    descriptions_root = root / "figures" / "descriptions"
    descriptions_root.mkdir(parents=True, exist_ok=True)
    print(f"env file: {env_file or 'process environment'}")
    print(
        f"backend: {args.backend}; base: {args.base}; model: {args.model}; "
        f"fallback: {args.fallback_model or 'disabled'}; "
        f"figures: {len(rows)}; workers: {args.workers}"
    )

    quota_state = {"exhausted": False}

    def work(row: dict[str, Any]) -> dict[str, Any]:
        image_path = Path(str(row.get("source_path") or ""))
        if not image_path.is_file():
            raise RuntimeError(f"image missing: {image_path}")
        relative = Path(str(row.get("file") or ""))
        sidecar = descriptions_root / relative.with_suffix(".md")
        source_sha = sha256_file(image_path)
        if sidecar.is_file() and not args.force:
            text = sidecar.read_text(encoding="utf-8")
            # Only reuse a sidecar produced by the currently requested model.
            # This prevents a free-only run from silently keeping paid-model output.
            if source_sha in text and f'model: "{args.model}"' in text:
                return {
                    **row,
                    "description_path": str(Path("descriptions") / relative.with_suffix(".md")),
                }
        used_model = (
            args.fallback_model if quota_state["exhausted"] and args.fallback_model else args.model
        )
        if args.backend == "api":
            result = call_api(image_path, args.base, key, used_model, PROMPT, args.timeout)
        else:
            try:
                result = call_opencode(image_path, used_model, PROMPT, args.timeout)
            except QuotaExceeded:
                if not args.fallback_model:
                    raise
                quota_state["exhausted"] = True
                used_model = args.fallback_model
                print(f"  quota hit; falling back to {used_model} for {row.get('file')}")
                result = call_opencode(image_path, used_model, PROMPT, args.timeout)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(sidecar_text(row, result, used_model, source_sha), encoding="utf-8")
        return {
            **row,
            "description_path": str(Path("descriptions") / relative.with_suffix(".md")),
            "description_model": used_model,
            "description_generated_at": now_iso(),
        }

    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(work, row): row for row in rows}
        for index, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                updated = future.result()
                results[str(updated.get("source_path"))] = updated
                print(f"[{index}/{len(rows)}] {updated.get('file')}")
            except Exception as exc:
                print(f"[{index}/{len(rows)}] FAILED {row.get('file')}: {exc}")

    payload["figures"] = [results.get(str(row.get("source_path")), row) for row in all_rows]
    write_json(WORK_DIR / "figures.json", payload)

    index_lines = [
        "# 图示说明索引",
        "",
        "> 由视觉模型生成，仅作辅助；以教材原图和图注为准。",
        "",
        "| 图号 | 教材页 | 说明 | 图片 |",
        "|---|---|---|---|",
    ]
    for row in payload["figures"]:
        if not row.get("description_path"):
            continue
        label = str(row.get("label") or "教材图片").replace("|", "\\|")
        description = str(row["description_path"]).replace("|", "\\|")
        image = str(row.get("file") or "").replace("|", "\\|")
        index_lines.append(
            f"| {label} | {row.get('book_page') or '—'} | `{description}` | `{image}` |"
        )
    (descriptions_root / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"descriptions written: {len(results)}")
    print(f"wrote {descriptions_root}")


if __name__ == "__main__":
    main()
