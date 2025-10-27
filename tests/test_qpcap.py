from pathlib import Path
from zipfile import ZipFile

from qns_shark.qer import QuantumEvent, QuantumEventKind
from qns_shark.qpcap import QPCAPWriter


def test_qpcap_writer_creates_archive(tmp_path: Path):
    events = [
        QuantumEvent(
            source="netsquid:run42",
            t_ns=10,
            kind=QuantumEventKind.ENTANGLEMENT_ATTEMPT,
            payload={"pair_id": "p1", "left_node": "A", "right_node": "B"},
        ),
        QuantumEvent(
            source="netsquid:run42",
            t_ns=20,
            kind=QuantumEventKind.ENTANGLEMENT_SUCCESS,
            payload={"pair_id": "p1", "F": 0.92, "lifetime_ns": 1_000_000},
        ),
    ]

    output = tmp_path / "capture.qpcap"
    writer = QPCAPWriter(output)
    manifest = writer.write(events)

    assert output.exists()
    assert manifest.event_batches[0].count == 2

    with ZipFile(output) as archive:
        assert "meta/manifest.json" in archive.namelist()
        assert any(name.startswith("events/") for name in archive.namelist())
