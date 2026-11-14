"""Matched local API benchmark using the original November 10 code prompts."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

import psutil

from cases import CODE

ROOT = Path(__file__).resolve().parent
WORKLOAD = ROOT / "workload.json"
SYSTEM = ("Implement the requested function in Python. Return only Python code, with no tests or explanation. "
          "Use only built-ins and no imports. A fenced Python block is acceptable.")


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as response:
        return json.load(response)


def chat(port, model, messages, tune=None):
    body = {
        "model": model, "messages": messages, "temperature": 0, "seed": 42,
        "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": False},
        "stream": True, "stream_options": {"include_usage": True},
    }
    if tune:
        body["strata_tune"] = tune
    encoded = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", encoded,
                                 {"Content-Type": "application/json"})
    start = time.perf_counter()
    first = last = None
    text, usage, timings, finish = [], None, None, None
    with urllib.request.urlopen(req, timeout=240) as response:
        for raw in response:
            now = time.perf_counter() - start
            if raw.strip() == b"data: [DONE]":
                break
            if not raw.startswith(b"data: "):
                continue
            event = json.loads(raw[6:])
            if event.get("error"):
                raise RuntimeError(event["error"])
            usage = event.get("usage") or usage
            timings = event.get("timings") or timings
            for choice in event.get("choices", []):
                piece = choice.get("delta", {}).get("content")
                if piece:
                    first = now if first is None else first
                    last = now
                    text.append(piece)
                finish = choice.get("finish_reason") or finish
    wall = time.perf_counter() - start
    if first is None or not usage or finish is None:
        raise RuntimeError("Incomplete streaming response")
    if not timings:
        timings = get(port, "/v1/status").get("last_timings")
    result = {
        "text": "".join(text), "usage": usage, "timings": timings, "finish": finish,
        "wall_s": wall, "ttft_s": first, "decode_wall_s": last - first,
        "request_sha256": hashlib.sha256(encoded).hexdigest(),
        "messages": messages, "tune": tune,
    }
    result["client_decode_tok_s"] = (usage["completion_tokens"] - 1) / (last - first) if last > first else None
    return result


def sample(stop, samples):
    while not stop.is_set():
        start = time.monotonic()
        vm = psutil.virtual_memory()
        row = {"at": time.time(), "available_mib": vm.available / 2**20}
        try:
            values = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used,memory.free,temperature.gpu,power.draw",
                 "--format=csv,noheader,nounits"], text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).splitlines()[0].split(",")
            row.update(zip(("gpu_used_mib", "gpu_free_mib", "gpu_temp_c", "gpu_power_w"),
                           map(float, values)))
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        samples.append(row)
        stop.wait(max(0.1, 1.5 - (time.monotonic() - start)))


def run(port, label, full, rounds, tune):
    model = get(port, "/v1/models")["data"][0]["id"]
    output = ROOT / (label + ".json")
    results = {"label": label, "model": model, "started": time.time(), "code": {}, "perf": []}
    samples = []
    stop = threading.Event()
    sampler = threading.Thread(target=sample, args=(stop, samples))
    sampler.start()

    def save():
        results["memory_samples"] = samples
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        results["warmup"] = chat(port, model, [{"role": "user", "content": "Say READY."}])
        if full:
            for name, (prompt, _) in CODE.items():
                result = chat(port, model, [{"role": "system", "content": SYSTEM},
                                           {"role": "user", "content": prompt}], tune)
                results["code"][name] = {"ok": True, **result}
                save()
                proc = subprocess.run(
                    [sys.executable, "-B", str(ROOT / "grade.py"), str(output), name],
                    capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                result["verdict"] = json.loads(proc.stdout) if proc.returncode == 0 else {
                    "pass": False, "reason": proc.stderr[-300:]}
                results["code"][name]["verdict"] = result["verdict"]
                print(f"{label} code {name} pass={result['verdict']['pass']}", flush=True)
                save()
        workload = json.loads(WORKLOAD.read_text(encoding="utf-8-sig"))["groups"]["python_code"]
        for round_index in range(1, rounds + 1):
            order = list(range(len(workload)))
            if round_index % 2 == 0:
                order.reverse()
            for index in order:
                prompt = f"Benchmark case R{round_index} C1 S{index}.\n\n{workload[index]}"
                result = chat(port, model, [{"role": "user", "content": prompt}], tune)
                result.update(round=round_index, case=index)
                results["perf"].append(result)
                print(f"{label} r{round_index} p{index}: {result['client_decode_tok_s']:.1f} tok/s "
                      f"n={result['usage']['completion_tokens']} ttft={result['ttft_s']:.3f}", flush=True)
                save()
        results["status_after"] = get(port, "/v1/status")
    finally:
        stop.set()
        sampler.join()
        save()
    tokens = sum(x["usage"]["completion_tokens"] - 1 for x in results["perf"])
    elapsed = sum(x["decode_wall_s"] for x in results["perf"])
    results["summary"] = {
        "client_decode_tok_s": tokens / elapsed, "rounds": rounds,
        "requests": len(results["perf"]),
        "all_1024": all(x["usage"]["completion_tokens"] == 1024 for x in results["perf"]),
        "cached_tokens": [x["usage"].get("prompt_tokens_details", {}).get("cached_tokens", 0)
                          for x in results["perf"]],
        "code_pass": sum(x.get("verdict", {}).get("pass", False) for x in results["code"].values()),
        "code_total": len(results["code"]),
    }
    save()
    print(json.dumps(results["summary"]), flush=True)
    return results["summary"]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--full", action="store_true")
    p.add_argument("--rounds", type=int, default=1)
    p.add_argument("--tune")
    a = p.parse_args()
    run(a.port, a.label, a.full, a.rounds, json.loads(a.tune) if a.tune else None)
