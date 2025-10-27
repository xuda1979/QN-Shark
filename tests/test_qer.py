import json
from pathlib import Path

import pytest

from qns_shark.qer import QuantumEvent, QuantumEventKind


def test_qer_requires_payload_fields():
    with pytest.raises(ValueError):
        QuantumEvent(
            source="sequence:exp1",
            t_ns=1,
            kind=QuantumEventKind.ENTANGLEMENT_SUCCESS,
            payload={"pair_id": "p1", "F": 0.9},
        )


def test_qer_serialisation(tmp_path: Path):
    event = QuantumEvent(
        source="sequence:exp1",
        t_ns=42,
        kind=QuantumEventKind.QKD_SIFTING_RESULT,
        payload={"Ncomp": 100, "Ndiff": 5, "QBER": 0.05},
    )
    data = event.model_dump(mode="json")
    path = tmp_path / "event.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = QuantumEvent(**json.loads(path.read_text(encoding="utf-8")))
    assert loaded.payload["Ncomp"] == 100
