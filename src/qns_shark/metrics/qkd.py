"""QKD-specific analytics helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from ..qer import QuantumEvent, QuantumEventKind


@dataclass
class SiftingAggregate:
    compared_bits: int
    differing_bits: int

    @property
    def qber(self) -> float:
        if self.compared_bits == 0:
            return 0.0
        return self.differing_bits / self.compared_bits


def aggregate_sifting(events: Iterable[QuantumEvent]) -> SiftingAggregate:
    """Aggregate QKD sifting results across events."""

    compared = 0
    differing = 0
    for event in events:
        if event.kind is not QuantumEventKind.QKD_SIFTING_RESULT:
            continue
        compared += int(event.payload.get("Ncomp", 0))
        differing += int(event.payload.get("Ndiff", 0))
    return SiftingAggregate(compared_bits=compared, differing_bits=differing)


def binary_entropy(prob: float) -> float:
    """Shannon binary entropy with safe domain handling."""

    if prob <= 0.0 or prob >= 1.0:
        return 0.0
    return -prob * math.log2(prob) - (1 - prob) * math.log2(1 - prob)


def secure_key_rate(
    sift_rate: float,
    qber: float,
    *,
    error_correction_efficiency: float = 1.15,
    privacy_amplification_leak: float = 0.02,
) -> float:
    """Estimate the asymptotic secure key rate.

    Parameters mirror the formula highlighted in the product specification and
    are intentionally configurable.
    """

    h_q = binary_entropy(qber)
    efficiency_term = error_correction_efficiency * h_q
    rate = sift_rate * max(0.0, 1 - efficiency_term - privacy_amplification_leak)
    return rate


__all__ = ["SiftingAggregate", "aggregate_sifting", "secure_key_rate", "binary_entropy"]
