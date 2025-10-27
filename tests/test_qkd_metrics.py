from qns_shark.metrics.qkd import aggregate_sifting, binary_entropy, secure_key_rate
from qns_shark.qer import QuantumEvent, QuantumEventKind


def _sifting_event(compared: int, differing: int):
    return QuantumEvent(
        source="sequence:exp1",
        t_ns=compared,
        kind=QuantumEventKind.QKD_SIFTING_RESULT,
        payload={"Ncomp": compared, "Ndiff": differing, "QBER": differing / compared if compared else 0},
    )


def test_aggregate_sifting():
    events = [_sifting_event(100, 4), _sifting_event(50, 2)]
    aggregate = aggregate_sifting(events)
    assert aggregate.compared_bits == 150
    assert aggregate.differing_bits == 6
    assert abs(aggregate.qber - 0.04) < 1e-6


def test_secure_key_rate_monotonic():
    rate_low_noise = secure_key_rate(1e6, 0.01)
    rate_high_noise = secure_key_rate(1e6, 0.08)
    assert rate_low_noise > rate_high_noise


def test_binary_entropy_limits():
    assert binary_entropy(0.0) == 0.0
    assert binary_entropy(1.0) == 0.0
