"""Quantum Event Record (QER) data structures.

This module provides a typed representation of QER events described in the
QN-Shark product specification. The goal is to make it straightforward for
adapters to emit strongly validated events while leaving room for future
extension. We implement a single :class:`QuantumEvent` model that contains a
``payload`` dictionary validated against per-kind schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Mapping, MutableMapping
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

QER_VERSION = "0.3"


class QuantumEventKind(str, Enum):
    """Enumerated event kinds supported by QN-Shark."""

    EMIT_PHOTON = "emit_photon"
    DETECT_PHOTON = "detect_photon"
    ENTANGLEMENT_ATTEMPT = "entanglement_attempt"
    ENTANGLEMENT_SUCCESS = "entanglement_success"
    DISTILLATION_STEP = "distillation_step"
    SWAP = "swap"
    MEMORY_UPDATE = "memory_update"
    QKD_MESSAGE = "qkd_message"
    QKD_SIFTING_RESULT = "qkd_sifting_result"
    ETSI_QKD004_API = "etsi_qkd004_api"
    SDN_CONTROL = "sdn_control"


class QuantumEvent(BaseModel):
    """Pydantic model for a Quantum Event Record entry."""

    event_id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    source: str = Field(..., description="Adapter identifier, e.g. netsquid:run42")
    clock_id: str | None = Field(
        default=None,
        description="Logical clock identifier; enables drift calibration.",
    )
    t_ns: int = Field(..., ge=0, description="Timestamp in nanoseconds relative to source clock")
    kind: QuantumEventKind = Field(..., description="Event kind enum value")
    node: str | None = Field(default=None, description="Node associated with the event")
    link_id: str | None = Field(
        default=None,
        description="Link identifier for link-oriented events",
    )
    correlation_id: str | None = Field(
        default=None, description="Identifier used to tie related events together"
    )
    notes: Dict[str, Any] = Field(
        default_factory=dict, description="Free-form metadata for adapters"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Event-kind specific fields"
    )

    @field_serializer("event_id")
    def _serialise_event_id(self, value: UUID) -> str:
        return str(value)

    @model_validator(mode="after")
    def _validate_payload(self) -> "QuantumEvent":
        """Validate the payload against event-kind specific requirements."""

        validators = {
            QuantumEventKind.EMIT_PHOTON: self._validate_emit_photon,
            QuantumEventKind.DETECT_PHOTON: self._validate_detect_photon,
            QuantumEventKind.ENTANGLEMENT_ATTEMPT: self._require_fields(
                {"pair_id", "left_node", "right_node"}
            ),
            QuantumEventKind.ENTANGLEMENT_SUCCESS: self._require_fields(
                {"pair_id", "F", "lifetime_ns"}
            ),
            QuantumEventKind.DISTILLATION_STEP: self._require_fields(
                {"in_pairs", "success", "F_out"}
            ),
            QuantumEventKind.SWAP: self._require_fields(
                {"left_pair", "right_pair", "success", "F_out"}
            ),
            QuantumEventKind.MEMORY_UPDATE: self._require_fields(
                {"mem_id", "state", "age_ns"}
            ),
            QuantumEventKind.QKD_MESSAGE: self._require_fields(
                {"protocol", "msg_type"}
            ),
            QuantumEventKind.QKD_SIFTING_RESULT: self._require_fields(
                {"Ncomp", "Ndiff", "QBER"}
            ),
            QuantumEventKind.ETSI_QKD004_API: self._require_fields(
                {"operation", "KSID", "QoS", "status"}
            ),
            QuantumEventKind.SDN_CONTROL: self._require_fields({"operation", "status"}),
        }

        validator = validators.get(self.kind)
        if validator is None:
            raise ValueError(f"Unsupported event kind: {self.kind}")

        validator()
        return self

    def _require_fields(self, required: set[str]):
        def validator() -> None:
            missing = sorted(required - self.payload.keys())
            if missing:
                raise ValueError(
                    f"Missing required payload fields for {self.kind}: {', '.join(missing)}"
                )

        return validator

    def _validate_emit_photon(self) -> None:
        required = {"wavelength_nm", "basis", "bit", "pulse_id"}
        self._require_fields(required)()

    def _validate_detect_photon(self) -> None:
        required = {"detector_id", "outcome"}
        self._require_fields(required)()

    @field_validator("payload")
    @classmethod
    def _ensure_payload_mutable(
        cls, value: Mapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Ensure we always store payload as a mutable dictionary."""

        return dict(value)


__all__ = ["QuantumEvent", "QuantumEventKind", "QER_VERSION"]
