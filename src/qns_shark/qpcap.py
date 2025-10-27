"""Utilities for working with the .qpcap container format.

The writer implemented here follows the specification in the product design:
- Event batches are stored as Apache Parquet files inside ``events/``.
- A manifest capturing provenance and hashes lives under ``meta/``.
- Everything is zipped into a single archive with the ``.qpcap`` extension.

The goal is to give developers a convenient way to persist Quantum Event
Records (QER) for analysis and replay.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable, List, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

import pyarrow as pa
import pyarrow.parquet as pq

from .qer import QER_VERSION, QuantumEvent


@dataclass
class ManifestSource:
    """Metadata about an event source contributing to the capture."""

    id: str
    clock: str | None = None

    def as_dict(self) -> dict:
        return {"id": self.id, "clock": self.clock}


@dataclass
class ManifestBatch:
    """Metadata describing a single Parquet batch inside a .qpcap archive."""

    path: str
    count: int
    sha256: str

    def as_dict(self) -> dict:
        return {"path": self.path, "count": self.count, "sha256": self.sha256}


@dataclass
class Manifest:
    """Top-level manifest describing a .qpcap archive."""

    version: str
    created: str
    sources: List[ManifestSource]
    event_batches: List[ManifestBatch]
    qer_schema: str

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "created": self.created,
            "sources": [src.as_dict() for src in self.sources],
            "event_batches": [batch.as_dict() for batch in self.event_batches],
            "qer_schema": self.qer_schema,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)


class QPCAPWriter:
    """High level helper for writing Quantum Event Records to .qpcap files."""

    def __init__(self, output_path: str | Path, *, compression: str = "zstd") -> None:
        self.output_path = Path(output_path)
        self.compression = compression

    def write(
        self,
        events: Sequence[QuantumEvent],
        *,
        sources: Iterable[ManifestSource] | None = None,
    ) -> Manifest:
        """Write a set of events to ``self.output_path``.

        Parameters
        ----------
        events:
            A sequence of :class:`QuantumEvent` instances to serialise.
        sources:
            Optional iterable describing contributing sources. If omitted we derive
            a set from the ``source`` field of the events.
        """

        if not events:
            raise ValueError("Cannot write empty event set to qpcap")

        tmpdir = Path(tempfile.mkdtemp(prefix="qpcap-"))
        try:
            events_dir = tmpdir / "events"
            events_dir.mkdir(parents=True, exist_ok=True)
            manifest_dir = tmpdir / "meta"
            manifest_dir.mkdir(parents=True, exist_ok=True)

            table = pa.Table.from_pylist([self._event_to_dict(evt) for evt in events])
            parquet_path = events_dir / "0001.parquet"
            pq.write_table(table, parquet_path, compression=self.compression)

            batch_hash = self._sha256_file(parquet_path)
            manifest = Manifest(
                version="0.3",
                created=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                sources=self._derive_sources(events) if sources is None else list(sources),
                event_batches=[
                    ManifestBatch(
                        path=f"events/{parquet_path.name}",
                        count=table.num_rows,
                        sha256=batch_hash,
                    )
                ],
                qer_schema=f"https://qns.dev/qer/{QER_VERSION}",
            )

            manifest_path = manifest_dir / "manifest.json"
            manifest_path.write_text(manifest.to_json(), encoding="utf-8")

            with ZipFile(self.output_path, "w", ZIP_DEFLATED) as archive:
                for file_path in self._iter_files(tmpdir):
                    archive.write(file_path, file_path.relative_to(tmpdir))

            return manifest
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @staticmethod
    def _event_to_dict(event: QuantumEvent) -> dict:
        data = event.model_dump(mode="json")
        if not data.get("notes"):
            data["notes"] = None
        if not data.get("payload"):
            data["payload"] = None
        return data

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _derive_sources(events: Sequence[QuantumEvent]) -> List[ManifestSource]:
        unique = {}
        for evt in events:
            clock_id = evt.clock_id or "mono"
            unique.setdefault(evt.source, ManifestSource(id=evt.source, clock=clock_id))
        return list(unique.values())

    @staticmethod
    def _iter_files(root: Path):
        for path in root.rglob("*"):
            if path.is_file():
                yield path


__all__ = ["QPCAPWriter", "Manifest", "ManifestSource", "ManifestBatch"]
