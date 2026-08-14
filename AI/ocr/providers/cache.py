"""The extraction cache, which is the reproducibility record.

NOT a performance optimisation. A hosted model is not reproducible from a
version string -- the weights behind `gemini-2.5-flash` can change without the
identifier changing, and a replay that re-calls the API may legitimately get a
different transcription. So the stored response IS the evidence of what the
model said on the day, and replay resolves from here rather than from the
network.

Master spec Phase 2.6 requires a stored result to be reproducible from its
recorded versions. For a local model that means pinned weights plus a hash.
For a hosted one it means this.

Key:   (page_sha256, model_id, prompt_version)
Value: the validated Page, the raw API response, and when it was requested.

`replay_evaluation` must never call the API. A replay that hits the network is
not a replay -- it is a second experiment.

STORAGE
-------
The interface is a small ABC so the durable backend (object storage, or a DB
table) can land without touching callers. `FilesystemExtractionCache` is the
reference implementation and writes to a configured directory -- durable in the
sense that matters here (survives the process), though object storage is the
production target. It is deliberately NOT a temp dir and NOT in-process: an
audit record that disappears with the worker is not an audit record.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from AI.ocr.providers.base import Line, Page

logger = logging.getLogger("GradeMIND.ExtractionCache")


class CacheMiss(KeyError):
    """No stored extraction for this key.

    Raised by `require()` rather than returning None, so a replay path cannot
    silently continue with nothing and produce an empty answer.
    """


def cache_key(page_sha256: str, model_id: str, prompt_version: str) -> str:
    return f"{page_sha256}__{model_id.replace('/', '_')}__{prompt_version.replace('/', '_')}"


class ExtractionCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def put(self, key: str, record: Dict[str, Any]) -> None: ...

    def require(self, key: str) -> Dict[str, Any]:
        record = self.get(key)
        if record is None:
            raise CacheMiss(
                f"no stored extraction for {key}. A replay must resolve entirely "
                "from the cache; calling the API would produce a second "
                "experiment, not a reproduction."
            )
        return record


class FilesystemExtractionCache(ExtractionCache):
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Shard by the first two characters to keep directories manageable at
        # 7.5M pages per cycle.
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            # A corrupt cache entry is a real problem: it means the audit
            # record for that page is gone. Do not treat it as a miss and
            # quietly re-call the API.
            raise RuntimeError(f"corrupt cache entry {path}: {exc}") from exc

    def put(self, key: str, record: Dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)  # atomic: a half-written audit record is worse than none


def page_to_record(page: Page, raw_response: Any) -> Dict[str, Any]:
    return {
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "page": {
            "lines": [asdict(line) for line in page.lines],
            "page_confidence": page.page_confidence,
            "provider": page.provider,
            "model_id": page.model_id,
            "prompt_version": page.prompt_version,
            "page_number": page.page_number,
            "page_sha256": page.page_sha256,
            "extraction_sha256": page.extraction_sha256,
            "rasterize_version": page.rasterize_version,
            "raw_response_sha256": page.raw_response_sha256,
            "warnings": list(page.warnings),
        },
        "raw_response": raw_response,
    }


def record_to_page(record: Dict[str, Any]) -> Page:
    p = record["page"]
    return Page(
        lines=tuple(
            Line(
                text=l["text"],
                confidence=l.get("confidence"),
                bbox=tuple(l["bbox"]) if l.get("bbox") else None,
                script=l.get("script"),
            )
            for l in p["lines"]
        ),
        page_confidence=p.get("page_confidence"),
        provider=p["provider"],
        model_id=p["model_id"],
        prompt_version=p["prompt_version"],
        page_number=p["page_number"],
        page_sha256=p["page_sha256"],
        extraction_sha256=p["extraction_sha256"],
        rasterize_version=p["rasterize_version"],
        raw_response_sha256=p.get("raw_response_sha256"),
        warnings=tuple(p.get("warnings", ())),
    )
