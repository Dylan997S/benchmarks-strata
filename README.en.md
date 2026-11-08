# Local Inference Benchmarks

[简体中文](README.md) · [Reports](reports/README.md) · [Hardware](hardware/README.md) · [Methodology](methodology/README.md)

Personal measurements of local LLM inference across hardware, models, quantizations, engines, input lengths and concurrency levels. The first published system uses four R9700 GPUs; the layout also supports future hardware without renaming the repository or mixing test records.

| Date | Hardware | Comparison | Report |
|---|---|---|---|
| 2026-11-08 | 4 × R9700 32 GB, EPYC 7452 | Radiance 1.15.1 vs Strata 0.1.58 / UD-Q4_K_XL; Qwen3.8-Flash-Next | [English](reports/2026-11-08-r9700-radiance-vs-strata/README.md) · [中文](reports/2026-11-08-r9700-radiance-vs-strata/README.zh-CN.md) |

Short-input single-client decode: **217.0 vs 139.3 tok/s**. Short-input 16-client total output: **1094.1 vs 329.7 tok/s**. Effective cold 16K prefill: **7786.6 vs 2776.7 tok/s**. These are different quantizations; Strata has eight active lanes, so sixteen clients include queueing. See the report for the coverage matrix and limitations.

- `hardware/`: measured system profiles with stable IDs.
- `reports/<date-hardware-experiment>/`: reports, configuration snapshots, sanitized CSV data and charts.
- `methodology/`: metric definitions and comparison requirements.
- `templates/`: starting points for future systems and experiments.

Add a [hardware profile](templates/hardware.json) and an [experiment report](templates/report.md), then update the two indexes. Retain each experiment's configuration snapshot when hardware or software changes. Do not publish placeholder performance results.

The original Strata source and history are preserved in the [archive branch](https://github.com/Dylan997S/benchmarks-strata/tree/archive/strata-source-20261108). The previously published report branch remains available. This is an independent benchmark repository, not an official engine release or certification.
