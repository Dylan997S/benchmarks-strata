# Measurement method / 测试方法

[首页](../README.md) · [首份完整实验](../reports/2026-11-08-r9700-radiance-vs-strata/README.md)

每次对比记录硬件编号、GPU 数量和显存、CPU/内存、软件版本、权重名称与量化、功率设置、上下文上限、实际输入长度、输出额度、思考预算、引擎槽数与 HTTP 客户端数。未知项明确写未知。

| Metric | Definition |
|---|---|
| TTFT | Barrier release to first nonempty content delta; includes queueing, transport, prefill and first decode. |
| Stream decode tok/s | `(completion_tokens - 1) / (last_content_time - first_content_time)`; approximate with SSE chunking. Under concurrency it includes scheduling pauses and interleaved prefill. |
| Total output tok/s | Sum of actual completion tokens divided by concurrent burst wall time; includes prefill and queueing. |
| Effective cold prefill tok/s | Uncached prompt tokens divided by TTFT for a single client; API-visible rate, not pure kernel throughput. |
| Request success | HTTP 200, complete SSE termination, nonempty content, and expected usage/finish checks; not a semantic quality score. |

Use the same saved prompts and generation conditions for paired tests. Record actual API token counts and cache hits. Measure cold prefixes and cache reuse separately. State whether weights differ, and do not infer equal quality from speed.

Clients are not engine slots. Report both, including queueing and admission limits. Keep maximum configured context separate from actual input length. Publish the tested matrix, repeat count and omitted combinations; never imply every context/concurrency combination passed.

Retain request and burst data with units. Explain aggregation explicitly: the first report uses medians across burst throughputs and pooled request summaries. Small one-round samples do not establish stable tail latency. Capability smoke checks remain separate from broad quality evaluations.

Publish only sanitized performance fields, portable settings and charts. Exclude credentials, internal endpoints, machine/account names, private prompts, generated private content and operational logs. Preserve old results; document any correction.
