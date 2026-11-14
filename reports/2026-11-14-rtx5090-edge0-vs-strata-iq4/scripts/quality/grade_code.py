import ast
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_cases as q

ALLOWED_IMPORTS = {
    "__future__", "bisect", "collections", "copy", "dataclasses", "decimal", "fractions", "functools",
    "heapq", "itertools", "json", "math", "operator", "re", "statistics", "typing",
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "input", "__import__", "breakpoint", "globals", "locals", "vars"}


def check_function(function, name):
    total = 0
    for args in q.code_tests()[name]:
        untouched = deepcopy(args)
        actual_args = deepcopy(args)
        expected = getattr(q, name)(*deepcopy(args))
        actual = function(*actual_args)
        total += 1
        if actual != expected:
            return {"pass": False, "passed_cases": total - 1, "reason": f"case {total}: wrong result",
                    "input": untouched, "expected": expected, "actual": actual}
        if actual_args != untouched:
            return {"pass": False, "passed_cases": total - 1, "reason": f"case {total}: input mutated"}
        if name == "reconcile_events":
            before = deepcopy(actual_args)
            for value in actual["values"].values():
                if isinstance(value, dict):
                    value["alias_probe"] = True
            if actual_args != before:
                return {"pass": False, "passed_cases": total - 1, "reason": f"case {total}: output aliases input"}
    for args in q.INVALID_CODE_TESTS.get(name, []):
        total += 1
        try:
            function(*deepcopy(args))
        except ValueError:
            continue
        return {"pass": False, "passed_cases": total - 1, "reason": f"case {total}: expected ValueError"}
    return {"pass": True, "passed_cases": total, "reason": ""}


def grade(path, name):
    text = Path(path).read_text(encoding="utf-8")
    fence = chr(96) * 3
    blocks = re.findall(fence + r"(?:python|py)?\s*\n(.*?)" + fence, text, re.DOTALL | re.IGNORECASE)
    source = next((b for b in blocks if f"def {name}" in b), text).strip()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            roots = [x.name.split(".")[0] for x in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]]
            if any(root not in ALLOWED_IMPORTS for root in roots):
                raise ValueError(f"Unsupported import: {roots}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Runtime introspection is outside the pure-function task")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            raise ValueError(f"Unsupported runtime call: {node.func.id}")
    module = types.ModuleType("candidate")
    sys.modules["candidate"] = module
    namespace = module.__dict__
    exec(compile(tree, str(path), "exec"), namespace)
    function = namespace.get(name)
    if not callable(function):
        raise ValueError(f"Missing function {name}")
    return check_function(function, name)


if __name__ == "__main__":
    try:
        if sys.argv[1] == "--selftest":
            result = {name: check_function(getattr(q, name), name) for name in q.CODE_PROMPTS}
            assert all(v["pass"] for v in result.values())
        else:
            result = grade(sys.argv[1], sys.argv[2])
    except Exception as error:
        result = {"pass": False, "reason": f"{type(error).__name__}: {error}"}
    print(json.dumps(result, ensure_ascii=False))
