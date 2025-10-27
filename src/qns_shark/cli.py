"""Command line interface for QN-Shark utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.table import Table

from .qer import QuantumEvent
from .qpcap import Manifest, ManifestBatch, ManifestSource, QPCAPWriter

app = typer.Typer(help="Utilities for working with Quantum Event Records")
console = Console()


def _load_events(path: Path) -> List[QuantumEvent]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise typer.BadParameter("Input JSON must be a list of event objects")
    events: List[QuantumEvent] = []
    for idx, item in enumerate(data):
        try:
            events.append(QuantumEvent(**item))
        except ValueError as exc:  # pragma: no cover - exercised indirectly via CLI
            raise typer.BadParameter(f"Invalid event at index {idx}: {exc}") from exc
    return events


@app.command("create-qpcap")
def create_qpcap(
    input_json: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Argument(...),
    compression: str = typer.Option(
        "zstd", help="Compression codec for Parquet batches"
    ),
):
    """Create a .qpcap capture from a JSON list of events."""

    events = _load_events(input_json)
    writer = QPCAPWriter(output, compression=compression)
    manifest = writer.write(events)
    _print_manifest(manifest)
    console.print(f"[green]Wrote {output} with {manifest.event_batches[0].count} events[/green]")


@app.command()
def show_manifest(path: Path = typer.Argument(..., exists=True, readable=True)):
    """Show the manifest from an existing .qpcap file without extracting it."""

    with QPCAPReader(path) as reader:
        manifest = reader.manifest
    _print_manifest(manifest)


class QPCAPReader:
    """Lightweight reader that exposes the manifest of a .qpcap archive."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(path)
        self.manifest = self._load_manifest()

    def __enter__(self) -> "QPCAPReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - nothing to cleanup
        return None

    def _load_manifest(self) -> Manifest:
        from zipfile import ZipFile

        with ZipFile(self.path) as archive:
            with archive.open("meta/manifest.json") as manifest_file:
                manifest_data = json.load(manifest_file)
        sources = [
            ManifestSource(id=item.get("id", ""), clock=item.get("clock"))
            for item in manifest_data.get("sources", [])
        ]
        batches = [
            ManifestBatch(
                path=entry["path"],
                count=int(entry["count"]),
                sha256=entry["sha256"],
            )
            for entry in manifest_data.get("event_batches", [])
        ]
        manifest = Manifest(
            version=manifest_data["version"],
            created=manifest_data["created"],
            sources=sources,
            event_batches=batches,
            qer_schema=manifest_data["qer_schema"],
        )
        return manifest


def _print_manifest(manifest: Manifest) -> None:
    table = Table(title=".qpcap manifest")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Version", manifest.version)
    table.add_row("Created", manifest.created)
    table.add_row("QER Schema", manifest.qer_schema)

    src_table = Table(title="Sources")
    src_table.add_column("ID")
    src_table.add_column("Clock")
    for source in manifest.sources:
        src_table.add_row(source.id, source.clock or "-")

    batch_table = Table(title="Event Batches")
    batch_table.add_column("Path")
    batch_table.add_column("Count")
    batch_table.add_column("SHA-256")
    for batch in manifest.event_batches:
        batch_table.add_row(batch.path, str(batch.count), batch.sha256)

    console.print(table)
    console.print(src_table)
    console.print(batch_table)


if __name__ == "__main__":
    app()
