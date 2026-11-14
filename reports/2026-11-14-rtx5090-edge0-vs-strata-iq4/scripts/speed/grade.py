"""Run code unit cases in bounded child processes and summarize paired speed measurements."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import re
from statistics import median
import subprocess
import sys

from cases import CALLS, CODE


ROOT = Path(__file__).resolve().parent
SAFE_NAMES = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "isinstance", "len", "list",
    "max", "min", "pow", "range", "reversed", "set", "sorted", "str", "sum", "tuple", "zip",
    "ValueError", "TypeError",
}
SAFE_METHODS = {
    "add", "append", "clear", "copy", "count", "discard", "extend", "get", "index", "insert", "items",
    "join", "keys", "pop", "remove", "reverse", "setdefault", "sort", "strip", "update", "values",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate(source, name):
    block = re.search(r"```(?:python|py)?\s*\n(.*?)```", source, re.DOTALL | re.IGNORECASE)
    code = (block.group(1) if block else source).strip()
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Global, ast.Nonlocal, ast.With,
                             ast.AsyncWith, ast.AsyncFunctionDef)):
            raise ValueError(f"unsupported syntax for built-ins-only test: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("private runtime name")
        if isinstance(node, ast.Attribute) and node.attr not in SAFE_METHODS:
            raise ValueError(f"unsupported method: {node.attr}")
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            raise ValueError("decorators are outside this test")
    namespace = {"__builtins__": {key: getattr(__import__("builtins"), key) for key in SAFE_NAMES}}
    exec(compile(tree, "<candidate>", "exec"), namespace)
    for index, (args, expected) in enumerate(CODE[name][1], start=1):
        arguments = deepcopy(args)
        result = namespace[name](*arguments)
        if result != expected:
            return {"pass": False, "reason": f"unit case {index}: wrong result"}
        if arguments != args:
            return {"pass": False, "reason": f"unit case {index}: input mutated"}
    return {"pass": True, "reason": ""}


def grade(source, name, result):
    if not result["ok"]:
        return {"pass": False, "reason": result["error"]}
    try:
        proc = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), str(source), name],
                              cwd=ROOT, capture_output=True, text=True, timeout=6)
        if proc.returncode:
            return {"pass": False, "reason": f"grader child exit {proc.returncode}"}
        return json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"pass": False, "reason": "unit tests timed out"}


def gather_perf(runs):
    if len(runs) != 2:
        return {"exact": 0, "expected": 0}
    c = runs[0]["c"]
    assert c in (1, 8) and all(len(r["requests"]) == c for r in runs)
    good = [req for run in runs for req in run["requests"] if req["ok"]]
    exact = sum(req["usage"]["completion_tokens"] == 1024 for req in good)
    stats = {"exact": exact, "expected": 2 * c, "http_ok": len(good),
             "lengths": [req["usage"]["completion_tokens"] for req in good],
             "cache_tokens": [int((req.get("timings") or {}).get("cache_n") or 0) for req in good]}
    if exact != 2 * c:
        return stats
    if c == 1:
        rates = [(run["requests"][0]["usage"]["completion_tokens"] - 1)
                 / run["requests"][0]["decode_wall_s"] for run in runs]
        tps = (1024 - 1) * 2 / sum(req["decode_wall_s"] for req in good)
    else:
        rates = [1024 * c / run["wall_s"] for run in runs]
        tps = 1024 * c * 2 / sum(run["wall_s"] for run in runs)
    return {**stats, "tps": tps, "round_tps": rates, "ttft_ms": median(req["ttft_s"] for req in good) * 1000}


def report(folder=ROOT):
    inputs = {"strata": folder / "strata-bench.json", "basalt": ROOT / "basalt-bench.json"}
    raw = {label: load(path) for label, path in inputs.items()}
    assert all(set(d["code"]) == set(CODE) and len(d["tools"]) == len(CALLS) for d in raw.values())
    matched_tools = [name for name in raw["strata"]["tools"]
                     if all(d["tools"][name]["pass"] for d in raw.values())]
    rows = {}
    for label, d in raw.items():
        code = {name: grade(inputs[label], name, answer) for name, answer in d["code"].items()}
        row = {"model": d["model"], "code": code, "code_pass": sum(item["pass"] for item in code.values()),
               "code_total": len(CODE),
               "tool_pass": sum(item["pass"] for item in d["tools"].values()), "tool_total": len(CALLS),
               "tool_failures": {k: v["reason"] for k, v in d["tools"].items() if not v["pass"]},
               "tool_paired_cases": len(matched_tools),
               "tool_paired_p50_ms": median(d["tools"][k]["wall_s"] * 1000 for k in matched_tools)
               if matched_tools else None}
        for c in (1, 8):
            row[f"c{c}"] = gather_perf([r for r in d["perf"] if r["c"] == c])
        rows[label] = row
    output = json.dumps(rows, ensure_ascii=False, indent=2)
    (folder / "comparison.json").write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        source, name = sys.argv[1:]
        try:
            verdict = evaluate(load(Path(source))["code"][name]["text"], name)
        except Exception as error:
            verdict = {"pass": False, "reason": f"{type(error).__name__}: {error}"}
        print(json.dumps(verdict))
    elif len(sys.argv) == 2:
        report(Path(sys.argv[1]).resolve())
    else:
        report()
