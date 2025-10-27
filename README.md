# QN-Shark

Core utilities and reference implementation pieces for the QN-Shark quantum
network observability toolkit. This repository currently focuses on the
foundational data layer described in the product design:

- **Quantum Event Record (QER)** schema definitions with validation helpers.
- **.qpcap** archive writer to persist captures as Parquet batches + manifest.
- **Metrics helpers** for QKD (QBER aggregation, secure key rate estimates).
- **CLI tooling** to convert JSON event dumps into distributable `.qpcap` files.

## Installation

```bash
pip install -e .
```

The project targets Python 3.10+.

## Usage

### Create a `.qpcap` capture from JSON

```bash
qns-shark create-qpcap sample-events.json output.qpcap
```

The command validates each event against the QER schema, writes a Parquet batch,
and generates a manifest aligned with the specification (including SHA-256
hashes and schema URL).

### Inspect a manifest

```bash
qns-shark show-manifest output.qpcap
```

## Running tests

```bash
pytest
```

## Next steps

This repository contains a minimal but functional subset of the broader
QN-Shark design. Future milestones will add adapters (SeQUeNCe, NetSquid,
QuISP), session reconstruction engines, OTLP exporters, and the desktop UI
specified in the accompanying product document.
