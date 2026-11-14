"""Fixed prompts, hidden unit cases, and mock tool results for the matched benchmark."""

CODE = {
    "merge_windows": (
        "merge_windows(windows) receives a list of (start, end) integer tuples. "
        "Each start is <= end. Merge intervals that overlap or touch at an endpoint. "
        "Return a sorted list of tuples. Do not mutate the input.",
        [
            (([],), []),
            (([(7, 10), (1, 3), (3, 8), (20, 20)],), [(1, 10), (20, 20)]),
            (([(2, 2), (0, 1), (4, 9), (5, 7)],), [(0, 1), (2, 2), (4, 9)]),
            (([(-5, 3), (-2, -1), (3, 3), (4, 5)],), [(-5, 3), (4, 5)]),
        ],
    ),
    "schedule_jobs": (
        "schedule_jobs(deps) receives a dict mapping job names to lists of prerequisites. "
        "A prerequisite omitted as a dict key is still a job with no prerequisites. Return the "
        "lexicographically smallest valid topological order as a list, or None for any cycle. "
        "Treat repeated prerequisites as one dependency. Do not mutate the input.",
        [
            (({},), []),
            (({"c": ["b", "b"], "b": ["a"], "x": []},), ["a", "b", "c", "x"]),
            (({"c": ["a"], "b": [], "a": ["c"]},), None),
            (({"z": ["z"]},), None),
            (({"b": ["d"], "a": ["c"], "c": ["d"], "d": []},), ["d", "b", "c", "a"]),
        ],
    ),
    "retry_delays": (
        "retry_delays(results, base, cap) receives a list of booleans. A True means success and "
        "resets the failure streak. For each False append min(cap, base * 2**(streak-1)) where "
        "streak includes that failure. For each True append 0. Return the list. Do not mutate inputs.",
        [
            (([False, False, False, True, False, False, False, False], 3, 10), [3, 6, 10, 0, 3, 6, 10, 10]),
            (([True, True, False], 5, 2), [0, 0, 2]),
            (([], 1, 2), []),
            (([False, False, False], 0, 0), [0, 0, 0]),
        ],
    ),
    "merge_sorted_runs": (
        "merge_sorted_runs(runs) takes a list of lists of (priority, label) tuples, each list "
        "sorted by ascending integer priority. Merge into one list of tuples by ascending "
        "priority. Break ties by input run index then original position in that run. Do not mutate inputs.",
        [
            (([],), []),
            (([[(1, "z"), (1, "y"), (3, "a")], [(1, "a"), (2, "b")], []],),
             [(1, "z"), (1, "y"), (1, "a"), (2, "b"), (3, "a")]),
            (([[], [(0, "x")], [(-1, "j"), (0, "a")]],), [(-1, "j"), (0, "x"), (0, "a")]),
        ],
    ),
    "net_inventory": (
        "net_inventory(events) takes (event_id, sku, signed_delta) tuples in arrival order. "
        "Keep only the first event with each event_id globally. Sum quantities by SKU and return "
        "a sorted list of (sku, quantity) tuples, omitting quantities of zero. Do not mutate inputs.",
        [
            (([("e1", "b", 4), ("e1", "a", 2), ("e2", "b", -4), ("e3", "a", -2)],), [("a", -2)]),
            (([("1", "z", -3), ("2", "a", 1), ("3", "z", 7)],), [("a", 1), ("z", 4)]),
            (([],), []),
        ],
    ),
    "traverse_rooms": (
        "traverse_rooms(graph, start) receives an adjacency-list dict of directed room connections "
        "and a starting room name. Return a dict giving the minimum edge count from start to each "
        "reachable room. Missing dict keys have no outgoing edges. Include start at distance 0 "
        "even when absent. Do not mutate inputs.",
        [
            (({"a": ["b", "c"], "b": ["c", "d"], "c": ["a", "e"]}, "a"),
             {"a": 0, "b": 1, "c": 1, "d": 2, "e": 2}),
            (({"a": ["b"]}, "z"), {"z": 0}),
            (({"a": ["a", "c", "c"], "c": ["b"], "b": ["a", "c"]}, "a"), {"a": 0, "c": 1, "b": 2}),
        ],
    ),
    "parse_escaped_fields": (
        "parse_escaped_fields(text) splits a string on unescaped vertical bars and preserves empty "
        "fields. A backslash escapes the following character, whatever it is, removing that "
        "backslash. A final backslash with no following character is kept. Return a list of strings.",
        [
            (("",), [""]),
            (("a|b||c|",), ["a", "b", "", "c", ""]),
            (("a\\|b|c\\\\d|e\\q|f\\",), ["a|b", "c\\d", "eq", "f\\"]),
            (("|\\||",), ["", "|", ""]),
        ],
    ),
    "rolling_counts": (
        "rolling_counts(times, width) receives nondecreasing integer timestamps and positive integer "
        "width. For each arrival count the events seen so far with times in (time-width, time], "
        "including the current arrival and any earlier arrival at the same time. Return a list.",
        [
            (([0, 0, 2, 3, 5, 5], 3), [1, 2, 3, 2, 2, 3]),
            (([1, 2, 3, 3, 3], 1), [1, 1, 1, 2, 3]),
            (([-5, -4, 5], 20), [1, 2, 3]),
            (([], 4), []),
        ],
    ),
}


def tool(name, description, properties):
    return {"type": "function", "function": {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": list(properties), "additionalProperties": False},
    }}


STR = {"type": "string"}
INT = {"type": "integer"}
TOOLS = [
    tool("read_file", "Read a file by its exact project-relative path.", {"path": STR}),
    tool("search_repo", "Search a code repository without reading a specific file.",
         {"query": STR, "limit": INT}),
    tool("list_issues", "List issues by repository and state.",
         {"repo": STR, "state": {"type": "string", "enum": ["open", "closed"]}, "limit": INT}),
    tool("get_ticket", "Retrieve the record of an issue by its numeric ticket ID.", {"id": INT}),
    tool("get_build", "Read a CI build by the run ID string.", {"run_id": STR}),
    tool("compare_refs", "Compare two version control refs from base to head.",
         {"base": STR, "head": STR}),
    tool("convert_units", "Convert a numeric quantity between explicitly named units.",
         {"value": {"type": "number"}, "from_unit": STR, "to_unit": STR}),
    tool("get_artifact", "Read a build artifact by its artifact key.", {"artifact": STR}),
    tool("check_policy", "Read the currently active policy for an operation.", {"operation": STR}),
    tool("lookup_owner", "Find the responsible team for a service by name.", {"service": STR}),
    tool("health_check", "Check whether a named service is healthy in a region.",
         {"service": STR, "region": STR}),
    tool("get_log", "Read an exact number of lines from a service log.",
         {"service": STR, "lines": INT}),
]

# Each element in steps is the exact call and its mock return value.
CALLS = [
    ("file", "Read the file src/parser.py.", [("read_file", {"path": "src/parser.py"}, {})]),
    ("search", "Search the repository for the literal phrase stale lease and return at most 3 hits.",
     [("search_repo", {"query": "stale lease", "limit": 3}, {})]),
    ("issue_list", "List exactly up to 4 closed issues in repo runtime/worker.",
     [("list_issues", {"repo": "runtime/worker", "state": "closed", "limit": 4}, {})]),
    ("ticket", "Fetch ticket 817 by its numeric ticket ID.", [("get_ticket", {"id": 817}, {})]),
    ("refs", "Compare refs with base release/1.2 and head feature/retry.",
     [("compare_refs", {"base": "release/1.2", "head": "feature/retry"}, {})]),
    ("units", "Use the conversion tool to convert 12.5 ms to seconds. Use ms and s as the unit codes.",
     [("convert_units", {"value": 12.5, "from_unit": "ms", "to_unit": "s"}, {})]),
    ("health", "Check the billing-api service in region eu-west-2.",
     [("health_check", {"service": "billing-api", "region": "eu-west-2"}, {})]),
    ("log", "Read 17 log lines for the queue-reader service.",
     [("get_log", {"service": "queue-reader", "lines": 17}, {})]),
    ("build_chain", "Fetch ticket 903. Then fetch its CI build using the run ID returned by the ticket. "
     "After both tools finish, answer with only the build's confirmation code.",
     [("get_ticket", {"id": 903}, {"run_id": "ci-k7z91"}),
      ("get_build", {"run_id": "ci-k7z91"}, {"confirmation": "VFY-2861"})]),
    ("artifact_chain", "Fetch CI build run-42. Then read the artifact using the artifact key returned by that build. "
     "After both tools finish, answer with only the artifact's confirmation code.",
     [("get_build", {"run_id": "run-42"}, {"artifact": "retry/ea4ca"}),
      ("get_artifact", {"artifact": "retry/ea4ca"}, {"confirmation": "VFY-9052"})]),
    ("owner_chain", "Look up the owner of service cold-store. Then check the policy for the operation returned "
     "by the owner lookup. After both tools finish, answer with only the policy's confirmation code.",
     [("lookup_owner", {"service": "cold-store"}, {"operation": "unlock_archive"}),
      ("check_policy", {"operation": "unlock_archive"}, {"confirmation": "VFY-1127"})]),
    ("search_chain", "Search the repo for literal query token budget with limit 2. Then read the file at the "
     "first hit's path. After both tools finish, answer with only the file's confirmation code.",
     [("search_repo", {"query": "token budget", "limit": 2}, {"hits": [{"path": "src/limits.py"}]}),
      ("read_file", {"path": "src/limits.py"}, {"confirmation": "VFY-5280"})]),
]
