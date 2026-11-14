# Replay and deployment helpers

Use the pinned versions and settings in [configuration.json](../configuration.json). Paths in that file are placeholders for local installations. The replay clients operate on an already-running loopback service. Model selection and runtime startup for each ABBA round remain explicit operator steps.

## Matched speed

Run from `scripts/speed`. Python and `psutil` are required.

```powershell
python -m pip install -r requirements.txt
python bench.py --port 18089 --label edge0-replay --full --rounds 2
```

Repeat against the original Strata service with a different label and the same two prompts. The local endpoint port above is a portable example. Each main comparison should begin with a freshly restarted runtime. The harness performs a warmup, eight small code-gate tasks and four sustained requests, then writes results beside the script. It records cache usage and samples GPU/system memory approximately every 1.5 seconds. It also queries `/v1/status`, which the tested Strata services implement.

`bench.py`, `cases.py` and `grade.py` are preserved from the recorded speed harness. Its host-specific workload location was replaced by adjacent `workload.json`; that file contains the exact two original synthetic prompt bodies. `--tune` accepts the original per-request `strata_tune` JSON used for screens. Runtime-level variants are captured in the configuration snapshot.

## Expanded quality

Run from `scripts/quality` using Python's standard library.

```powershell
python grade_code.py --selftest
python replay.py --port 18089 --label edge0 --round 1
python replay.py --port 18089 --label edge0 --round 2
```

For matched ABBA reproduction, run Edge0 round 1, Strata round 1, Strata round 2, then Edge0 round 2, restarting the selected runtime between rounds. Record each startup separately. `replay.py` is a new portable command-line entry point around the original `benchmark.run_round`; the benchmark, fixed prompts, expected answers, tool simulator and code grader are otherwise preserved. A prior results file resumes completed tasks, so use a new label for a new independent measurement. Generated outputs and JSON results are written beside the script.

Code grading uses AST checks, a standard-library allowlist and a subprocess timeout of 15 seconds. Simulated tools update only in-memory synthetic data. Saved responses allow independent regrading without loading either model.

## Edge0 startup, shutdown and conversation

The deployment scripts retain the tested command and memory settings. Their installation and CUDA roots are now explicit parameters. Prepare this relative installation layout using the official pinned build and model files.

```text
<install-root>/repo/edge0-infer/build/windows/bin/edge0-infer.exe
<install-root>/repo/edge0-strata/build/strata.exe
<install-root>/models/Edge0-145B-NVFP4/
```

```powershell
./deployment/Start-Edge0.ps1 -InstallRoot <install-root> -CudaRoot <cuda-root>
python ./deployment/Chat-Edge0.py
./deployment/Stop-Edge0.ps1 -InstallRoot <install-root>
```

Replace angle-bracket placeholders with your own quoted paths before running. The startup helper binds to `127.0.0.1:18089`, uses model alias `edge0-145b-nvfp4`, and writes a PID file under the installation root. The 25,000 MiB free-VRAM check is the original measured-profile startup guard. The script generates operational logs locally; these are outside the published evidence archive. Shutdown checks that the stored PID belongs to the expected executable.

Example OpenAI-compatible request to the local loopback default follows.

```python
import json
from urllib.request import Request, urlopen

payload = {"model": "edge0-145b-nvfp4",
           "messages": [{"role": "user", "content": "用中文介绍你自己。"}],
           "max_tokens": 256, "stream": False}
request = Request("http://127.0.0.1:18089/v1/chat/completions",
                  data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
with urlopen(request, timeout=120) as response:
    print(json.load(response)["choices"][0]["message"]["content"])
```

The publication checks compile the replay files and rerun the offline graders. The portable deployment wrappers were syntax-checked. They were not used to restart the running production service during archival.
