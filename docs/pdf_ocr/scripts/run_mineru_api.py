#!/usr/bin/env python3
"""Submit local PDF parts to the MinerU Precision API, poll and download ZIPs."""

from __future__ import annotations

import argparse
import os
import shutil
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from common import (
    RAW_DIR,
    ROOT,
    WORK_DIR,
    ensure_dirs,
    fail,
    load_environment,
    read_json,
    sha256_file,
    source_pdf_path,
    write_json,
)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST", "PUT"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class MinerUClient:
    def __init__(self, api_base: str, token: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.session = make_session()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _json(self, response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"non-JSON response: HTTP {response.status_code}") from exc
        if response.status_code >= 400:
            raise RuntimeError(
                f"HTTP {response.status_code}: {data.get('msg') or data.get('message') or data}"
            )
        if data.get("code") not in (0, None):
            raise RuntimeError(f"API code {data.get('code')}: {data.get('msg')}")
        return data

    def request_upload_urls(self, files: list[dict[str, Any]], model: str) -> dict[str, Any]:
        payload = {
            "files": files,
            "model_version": model,
            "language": os.environ.get("MINERU_LANGUAGE", "ch"),
            "enable_table": env_bool("MINERU_ENABLE_TABLE", True),
            "enable_formula": env_bool("MINERU_ENABLE_FORMULA", True),
        }
        response = self.session.post(
            f"{self.api_base}/file-urls/batch",
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        return self._json(response)

    def upload(self, url: str, path: Path) -> None:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                with path.open("rb") as handle:
                    response = self.session.put(url, data=handle, timeout=600)
                if response.status_code in (200, 201):
                    return
                last_error = RuntimeError(
                    f"upload HTTP {response.status_code}: {response.text[:200]}"
                )
            except requests.RequestException as exc:
                last_error = exc
            print(f"  upload attempt {attempt} failed: {last_error}")
            time.sleep(2**attempt)
        raise RuntimeError(f"upload failed after retries: {last_error}")

    def poll_batch(
        self,
        batch_id: str,
        parts_by_data_id: dict[str, dict[str, Any]],
        timeout_seconds: int,
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout_seconds
        interval = 5.0
        last_state: dict[str, str] = {}
        while time.monotonic() < deadline:
            response = self.session.get(
                f"{self.api_base}/extract-results/batch/{batch_id}",
                headers=self.headers,
                timeout=60,
            )
            data = self._json(response)
            results = data.get("data", {}).get("extract_result", [])
            if not isinstance(results, list):
                results = []
            done: list[dict[str, Any]] = []
            all_terminal = True
            for result in results:
                data_id = result.get("data_id")
                file_name = result.get("file_name")
                part = parts_by_data_id.get(str(data_id)) if data_id else None
                if part is None and file_name:
                    part = next(
                        (row for row in parts_by_data_id.values() if row["name"] == file_name),
                        None,
                    )
                state = str(result.get("state", "unknown"))
                label = part["part_id"] if part else (file_name or data_id or "?")
                if last_state.get(label) != state:
                    print(f"  {label}: {state}")
                    last_state[label] = state
                if state == "done":
                    if not result.get("full_zip_url"):
                        raise RuntimeError(f"{label}: done but full_zip_url is empty")
                    done.append({**result, "part": part})
                elif state == "failed":
                    raise RuntimeError(
                        f"{label}: failed: {result.get('err_msg') or 'unknown error'}"
                    )
                elif state in {"waiting-file", "pending", "running", "converting"}:
                    all_terminal = False
                else:
                    all_terminal = False
            if done and all_terminal and len(results) >= len(parts_by_data_id):
                return done
            if all_terminal and len(results) >= len(parts_by_data_id):
                return done
            time.sleep(interval)
            interval = min(interval * 1.4, 30.0)
        raise RuntimeError(f"polling timed out after {timeout_seconds}s for batch {batch_id}")

    def download(self, url: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(url, stream=True, timeout=600) as response:
            if response.status_code != 200:
                raise RuntimeError(f"download HTTP {response.status_code}")
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        if target.stat().st_size == 0:
            raise RuntimeError("downloaded ZIP is empty")


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def find_one(root: Path, names: tuple[str, ...]) -> Path | None:
    for pattern in names:
        matches = sorted(root.rglob(pattern))
        if matches:
            return matches[0]
    return None


def materialize_zip(zip_path: Path, part_dir: Path) -> None:
    part_dir.mkdir(parents=True, exist_ok=True)
    staging = part_dir / "_unzip"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"unsafe ZIP member: {member.filename}")
        archive.extractall(staging)

    full_md = find_one(staging, ("full.md",))
    content_list = find_one(staging, ("*content_list.json", "content_list.json"))
    layout = find_one(staging, ("*layout.json", "layout.json", "*middle.json", "middle.json"))
    images = find_one(staging, ("images",))
    if not full_md:
        raise RuntimeError("result ZIP has no full.md")
    if not content_list:
        raise RuntimeError("result ZIP has no content_list.json")
    if not layout:
        raise RuntimeError("result ZIP has no layout.json/middle.json")

    for source, target_name in (
        (full_md, "full.md"),
        (content_list, "content_list.json"),
        (layout, "layout.json"),
    ):
        shutil.copy2(source, part_dir / target_name)

    if images and images.is_dir():
        target_images = part_dir / "images"
        if target_images.exists():
            shutil.rmtree(target_images)
        shutil.copytree(images, target_images)

    shutil.rmtree(staging)


def load_parts(part_ids: list[str] | None) -> list[dict[str, Any]]:
    parts = read_json(WORK_DIR / "parts.json", [])
    if not parts:
        fail("work/parts.json missing; run split_pdf.py first")
    if part_ids:
        wanted = set(part_ids)
        parts = [part for part in parts if part["part_id"] in wanted]
        if not parts:
            fail(f"no parts matched: {', '.join(sorted(wanted))}")
    return parts


def result_complete(part_dir: Path) -> bool:
    return (
        (part_dir / "full.md").is_file()
        and (part_dir / "content_list.json").is_file()
        and ((part_dir / "layout.json").is_file() or (part_dir / "part.json").is_file())
    )


def existing_result_dir(part_id: str) -> Path | None:
    candidates = []
    for batch_dir in RAW_DIR.glob("mineru/batch-*"):
        candidate = batch_dir / part_id
        if result_complete(candidate):
            candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", action="append", help="part_id; repeat to submit a subset")
    parser.add_argument("--model", default=os.environ.get("MINERU_MODEL_VERSION", "vlm"))
    parser.add_argument("--timeout", type=int, default=3600, help="poll timeout in seconds")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="re-submit parts with local results")
    args = parser.parse_args()

    ensure_dirs()
    env_file = load_environment()
    token = os.environ.get("MINERU_API_KEY", "").strip()
    if not token:
        fail("MINERU_API_KEY is empty; set it in docs/pdf_ocr/.env")
    api_base = os.environ.get("MINERU_API_BASE", "https://mineru.net/api/v4")
    parts = load_parts(args.part)
    missing: list[dict[str, Any]] = []
    for part in parts:
        existing = existing_result_dir(part["part_id"])
        if existing and not args.force:
            print(f"{part['part_id']}: already downloaded ({existing})")
            continue
        missing.append(part)

    print(f"env file: {env_file or 'process environment'}")
    print(f"model: {args.model}; parts to submit: {len(missing)}")
    if not missing:
        print("nothing to do")
        return
    if args.dry_run:
        for part in missing:
            print(f"would upload {part['part_id']} ({part['page_count']} pages)")
        return

    payload_files = [
        {
            "name": Path(part["file"]).name,
            "data_id": f"cn8-{part['part_id']}",
            "is_ocr": env_bool("MINERU_IS_OCR", True),
        }
        for part in missing
    ]
    client = MinerUClient(api_base, token)
    print(f"requesting upload URLs for {len(payload_files)} file(s) ...")
    response = client.request_upload_urls(payload_files, args.model)
    batch_id = response.get("data", {}).get("batch_id")
    upload_urls = response.get("data", {}).get("file_urls") or []
    if not batch_id or len(upload_urls) != len(missing):
        fail(f"unexpected upload response: {response}")

    batch_dir = RAW_DIR / "mineru" / f"batch-{batch_id}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    parts_by_data_id = {
        f"cn8-{part['part_id']}": {**part, "name": Path(part["file"]).name} for part in missing
    }
    batch_record = {
        "batch_id": batch_id,
        "created_at": now_iso(),
        "model_version": args.model,
        "parts": [
            {
                "part_id": part["part_id"],
                "data_id": f"cn8-{part['part_id']}",
                "name": Path(part["file"]).name,
                "start_pdf_page": part["start_pdf_page"],
                "end_pdf_page": part["end_pdf_page"],
                "sha256": part.get("sha256") or sha256_file(Path(part["file"])),
            }
            for part in missing
        ],
    }
    write_json(batch_dir / "batch.json", batch_record)
    print(f"batch_id: {batch_id}")

    for index, part in enumerate(missing):
        print(f"uploading {part['part_id']} ...")
        client.upload(upload_urls[index], Path(part["file"]))

    print("waiting for MinerU results ...")
    results = client.poll_batch(batch_id, parts_by_data_id, args.timeout)
    for result in results:
        part = result.get("part")
        if not part:
            fail(f"cannot match result to a part: {result}")
        part_dir = batch_dir / part["part_id"]
        zip_path = part_dir / "result.zip"
        print(f"downloading {part['part_id']} ...")
        client.download(result["full_zip_url"], zip_path)
        materialize_zip(zip_path, part_dir)
        write_json(
            part_dir / "part.json",
            {
                "part_id": part["part_id"],
                "start_pdf_page": part["start_pdf_page"],
                "end_pdf_page": part["end_pdf_page"],
                "page_count": part["page_count"],
                "batch_id": batch_id,
                "data_id": f"cn8-{part['part_id']}",
                "model_version": args.model,
                "source_pdf": part.get("source_pdf"),
                "sha256": part.get("sha256"),
                "full_zip_url": result["full_zip_url"],
                "downloaded_at": now_iso(),
                "zip_sha256": sha256_file(zip_path),
            },
        )
        print(f"  saved: {part_dir}")

    batch_record["completed_at"] = now_iso()
    batch_record["status"] = "complete"
    write_json(batch_dir / "batch.json", batch_record)

    source = source_pdf_path()
    source_pdf = (
        str(source.relative_to(ROOT))
        if source.is_file() and ROOT in source.parents
        else str(source)
    )
    source_sha = sha256_file(source) if source.is_file() else parts[0].get("source_sha256")
    source_manifest = read_json(RAW_DIR / "mineru" / "source.json", {}) or {}
    source_manifest.update(
        {
            "source_pdf": source_pdf,
            "source_sha256": source_sha,
            "page_count": 485,
            "book_page_offset": 11,
            "updated_at": now_iso(),
        }
    )
    mineru = source_manifest.setdefault("mineru", {})
    mineru.setdefault("api_base", api_base)
    mineru["model_version"] = args.model
    batch_ids = set(mineru.get("batch_ids", []))
    batch_ids.add(batch_id)
    mineru["batch_ids"] = sorted(batch_ids)
    mineru["parts"] = [
        {
            "part_id": part["part_id"],
            "start_pdf_page": part["start_pdf_page"],
            "end_pdf_page": part["end_pdf_page"],
            "local_page_count": part["page_count"],
            "batch_id": batch_id,
        }
        for part in parts
    ]
    source_manifest["generated_at"] = now_iso()
    write_json(RAW_DIR / "mineru" / "source.json", source_manifest)


if __name__ == "__main__":
    main()
