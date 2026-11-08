# Benchmark repository instructions

This repository publishes independent hardware and local-inference measurements. The original engine source is retained on the archive branch.

- Preserve historical measurements and configuration snapshots. Record corrections explicitly.
- Add hardware profiles and dated experiments using the templates; update the indexes.
- Report measured versions, quantizations, actual input lengths, cache state, client counts and engine slot counts.
- Do not invent results, imply equal model quality from speed, or present effective API prefill as kernel throughput.
- Publish only sanitized data. Never include keys, private prompts, internal endpoints, account names or service logs.
- Documentation changes do not authorize running benchmarks, stopping inference services or changing production settings.
