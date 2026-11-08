# Experiment title

Template only — replace placeholders with measured facts before publication.

- Date:
- Hardware ID and profile link:
- Engine versions / revisions:
- Model family, exact weight names and quantizations:
- Configuration snapshot:
- Data and chart links:

## Question and conditions

What is being compared? Record actual prompt lengths, configured context maximum, output cap, sampling, reasoning budget, engine slots, concurrent clients, cache state, placement and power settings. Identify differences that affect interpretation.

## Coverage

List each input length, client count and repeat count. Mark untested combinations and explain why. Separate speed runs from cache and capability checks.

## Results

Publish only measured results: success/total, TTFT, stream decode rate, burst throughput and effective cold prefill where applicable. Include units, aggregation and sample sizes. Link the sanitized per-request and per-burst data.

## Interpretation and limits

Explain quantization differences, queueing, cache behavior, omitted tests and uncertainty. Do not infer quality or energy efficiency without corresponding measurements.

## Reproduction and corrections

Provide portable settings, benchmark procedure and dataset provenance. Keep private endpoints, keys, local paths and operational logs out of the public report. Record corrections with their date and reason.
