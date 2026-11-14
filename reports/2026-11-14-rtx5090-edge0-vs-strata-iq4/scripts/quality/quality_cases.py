"""Frozen prompts and deterministic reference implementations for this comparison."""
from copy import deepcopy
from fractions import Fraction
import itertools
import json
import random
import re


CODE_PROMPTS = {
    "interval_overlay": (
        "实现 interval_overlay(updates, lo, hi)。updates 是按到达顺序排列的字典列表，每项包含 "
        "start、end（整数，左闭右开）、priority（整数）和 value（字符串）。在 [lo, hi) 内，"
        "每一点取覆盖它的最高 priority 更新；同优先级取列表中较晚的一项。没有更新覆盖时 value 为 None。"
        "输出覆盖整个区间的 [start,end,value] 列表，相邻 value 相同必须合并。忽略零长度更新；lo==hi 返回 []。"
        "保证 start<=end、lo<=hi。不能修改输入，不能逐个整数点枚举，要求基于区间端点计算。"),
    "atomic_patch": (
        "实现 atomic_patch(initial, ops)。initial 是字符串键到整数值的字典，ops 按顺序执行。"
        "操作为 {'op':'set'|'add'|'delete'|'assert','key':字符串,'value':整数}，delete 不需要 value。"
        "set 赋值；add 在当前值上相加，缺失按0；delete 缺失键也成功；assert 必须键存在且等于 value。"
        "未知 op、缺失或非字符串 key、set/add/assert 的 value 不是严格的 int（bool 不算 int）、"
        "assert 不满足，均使整个事务失败。成功返回 {'committed':True,'state':最终字典,'failed_at':None}；"
        "失败返回 {'committed':False,'state':原始字典副本,'failed_at':首个失败操作的0起始下标}。"
        "输入保证 ops 元素是字典。不得改变 initial 或 ops。"),
    "schedule_tasks": (
        "实现 schedule_tasks(tasks, workers)。tasks 为 {任务名:{'duration':非负整数,'deps':[任务名,...]}}，"
        "workers 为正整数。依赖可重复，按集合处理。缺失依赖、依赖环或 workers<=0 必须抛 ValueError。"
        "从时刻0开始，先处理同一时刻全部完成任务，再把可执行任务按名称字典序分配给编号最小的空闲 worker。"
        "分配一个任务后若工期为0，则立即完成并重新计算可执行任务，再分配下一个；否则持续占用 worker。"
        "仅在当前没有进一步可分配的任务时跳到最近完成时刻。返回 {任务名:[开始,结束,worker编号]}。"
        "不能修改输入。特别处理空 tasks、零工期和多个任务同时完成。"),
    "capped_allocate": (
        "实现 capped_allocate(total, weights, caps)。等长非空整数列表，weights全为正数，caps均>=0，"
        "0<=total<=sum(caps)。按以下精确算法分配整数名额并返回列表，不能用浮点数："
        "维护未冻结项目和剩余名额。用权重比例计算各未冻结项目的精确份额。"
        "若某份额>=该项目cap，则同时把这些项目固定为cap、扣除名额并移出，重复。"
        "没有触顶项目时，对份额向下取整，余下名额按份额小数部分从大到小逐个加1，"
        "小数部分相同按原下标小者优先。total=0应全0，不可修改输入。"),
    "select_rows": (
        "实现 select_rows(rows, query)，返回满足布尔查询的行的0起始下标，保持输入顺序。"
        "语法为比较 atom: 标识符 == JSON字面量；字面量仅支持双引号字符串、整数、true、false、null。"
        "支持一元 !、二元 &、|、圆括号，优先级依次为 !、&、|。标识符符合 [A-Za-z_][A-Za-z0-9_]*。"
        "允许任意 token 间空白。字段缺失的比较始终 False；比较采用 JSON 类型和值，true 不能等于整数1。"
        "支持 JSON 字符串转义。空查询、非法字符、不完整表达式、尾随 token 均抛 ValueError。"
        "不能使用 eval/exec，不得修改 rows。允许 Python 标准库。"),
    "reconcile_events": (
        "实现 reconcile_events(events)。每条事件包含 id、key、version（非负整数）、source（字符串）、"
        "op（put或delete）；put另有value。全局相同id只处理第一次，后续同id即使内容不同也忽略。"
        "每个key由 (version,source) 字典序最大的事件决定；二者相同则较晚到达的有效事件胜出。"
        "delete 是墓碑，阻止较旧put复活。返回 {'values':可见键值字典,'versions':所有见过键到[version,source]字典}。"
        "value 可为嵌套 JSON，返回内容与输入不能互相共享可变对象。不能改变输入。"),
}


def interval_overlay(updates, lo, hi):
    if lo == hi:
        return []
    points = sorted({lo, hi, *(max(lo, min(hi, x[k])) for x in updates for k in ("start", "end"))})
    result = []
    for a, b in zip(points, points[1:]):
        active = [(x["priority"], i, x["value"]) for i, x in enumerate(updates)
                  if x["start"] <= a < x["end"]]
        value = max(active)[2] if active else None
        if result and result[-1][2] == value:
            result[-1][1] = b
        else:
            result.append([a, b, value])
    return result


def atomic_patch(initial, ops):
    state = dict(initial)
    for i, x in enumerate(ops):
        op, key = x.get("op"), x.get("key")
        bad = not isinstance(key, str) or op not in ("set", "add", "delete", "assert")
        bad |= op in ("set", "add", "assert") and type(x.get("value")) is not int
        if not bad and op == "assert":
            bad = key not in state or state[key] != x["value"]
        if bad:
            return {"committed": False, "state": dict(initial), "failed_at": i}
        if op == "set":
            state[key] = x["value"]
        elif op == "add":
            state[key] = state.get(key, 0) + x["value"]
        elif op == "delete":
            state.pop(key, None)
    return {"committed": True, "state": state, "failed_at": None}


def schedule_tasks(tasks, workers):
    if workers <= 0 or any(d not in tasks for t in tasks.values() for d in t["deps"]):
        raise ValueError()
    finished, started, active, result = set(), set(), {}, {}
    now = 0
    while len(finished) < len(tasks):
        ending = sorted(w for w, (_, end) in active.items() if end == now)
        for worker in ending:
            task, _ = active.pop(worker)
            finished.add(task)
        while True:
            free = sorted(set(range(workers)) - active.keys())
            ready = sorted(k for k, v in tasks.items() if k not in started and set(v["deps"]) <= finished)
            if not free or not ready:
                break
            task, worker = ready[0], free[0]
            end = now + tasks[task]["duration"]
            result[task] = [now, end, worker]
            started.add(task)
            if end == now:
                finished.add(task)
            else:
                active[worker] = (task, end)
        if not active:
            if len(finished) != len(tasks):
                raise ValueError()
            break
        now = min(end for _, end in active.values())
    return result


def capped_allocate(total, weights, caps):
    out, active, left = [0] * len(weights), set(range(len(weights))), total
    while active:
        scale = sum(weights[i] for i in active)
        shares = {i: Fraction(left * weights[i], scale) for i in active}
        hit = {i for i in active if shares[i] >= caps[i]}
        if hit:
            for i in hit:
                out[i] = caps[i]
                left -= caps[i]
            active -= hit
            continue
        for i in active:
            out[i] = shares[i].numerator // shares[i].denominator
        remaining = left - sum(out[i] for i in active)
        for i in sorted(active, key=lambda i: (-(shares[i] - out[i]), i))[:remaining]:
            out[i] += 1
        break
    return out


def select_rows(rows, query):
    token_re = re.compile(r'\s*(==|[!&|()]|"(?:\\.|[^"\\])*"|-?\d+|[A-Za-z_][A-Za-z0-9_]*)')
    tokens, pos = [], 0
    while pos < len(query):
        if not query[pos:].strip():
            break
        m = token_re.match(query, pos)
        if not m:
            raise ValueError()
        tokens.append(m.group(1))
        pos = m.end()
    at = 0

    def atom():
        nonlocal at
        if at >= len(tokens):
            raise ValueError()
        token = tokens[at]
        at += 1
        if token == "!":
            return ("not", atom())
        if token == "(":
            expr = expression()
            if at >= len(tokens) or tokens[at] != ")":
                raise ValueError()
            at += 1
            return expr
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            raise ValueError()
        if at + 1 >= len(tokens) or tokens[at] != "==":
            raise ValueError()
        at += 1
        literal = tokens[at]
        at += 1
        if literal not in ("true", "false", "null") and not literal.startswith('"') and not re.fullmatch(r"-?\d+", literal):
            raise ValueError()
        try:
            value = json.loads(literal)
        except (ValueError, TypeError) as error:
            raise ValueError() from error
        return ("eq", token, value)

    def conjunction():
        nonlocal at
        x = atom()
        while at < len(tokens) and tokens[at] == "&":
            at += 1
            x = ("and", x, atom())
        return x

    def expression():
        nonlocal at
        x = conjunction()
        while at < len(tokens) and tokens[at] == "|":
            at += 1
            x = ("or", x, conjunction())
        return x

    tree = expression()
    if at != len(tokens):
        raise ValueError()

    def evaluate(node, row):
        kind = node[0]
        if kind == "eq":
            return node[1] in row and type(row[node[1]]) is type(node[2]) and row[node[1]] == node[2]
        if kind == "not":
            return not evaluate(node[1], row)
        if kind == "and":
            return evaluate(node[1], row) and evaluate(node[2], row)
        return evaluate(node[1], row) or evaluate(node[2], row)

    return [i for i, row in enumerate(rows) if evaluate(tree, row)]


def reconcile_events(events):
    seen, best = set(), {}
    for x in events:
        if x["id"] in seen:
            continue
        seen.add(x["id"])
        key = x["key"]
        if key not in best or (x["version"], x["source"]) >= (best[key]["version"], best[key]["source"]):
            best[key] = x
    return {
        "values": {k: deepcopy(x["value"]) for k, x in best.items() if x["op"] == "put"},
        "versions": {k: [x["version"], x["source"]] for k, x in best.items()},
    }


def code_tests():
    rng = random.Random(20261114)
    cases = {name: [] for name in CODE_PROMPTS}
    cases["interval_overlay"] += [
        ([], 0, 0), ([], -5, 5),
        ([{"start": 0, "end": 10, "priority": 1, "value": "a"},
          {"start": 3, "end": 7, "priority": 1, "value": "b"},
          {"start": 4, "end": 6, "priority": 2, "value": "a"}], 0, 10),
        ([{"start": -10**12, "end": 10**12, "priority": 0, "value": "x"}], -10**12, 10**12),
    ]
    for _ in range(35):
        updates = []
        for i in range(rng.randrange(15)):
            a, b = sorted([rng.randrange(-8, 15), rng.randrange(-8, 15)])
            updates.append({"start": a, "end": b, "priority": rng.randrange(4), "value": rng.choice(["甲", "乙", "丙"])})
        cases["interval_overlay"].append((updates, -3, 10))
    cases["atomic_patch"] += [
        ({}, []),
        ({"a": 3}, [{"op": "add", "key": "a", "value": 2}, {"op": "assert", "key": "a", "value": 4}]),
        ({}, [{"op": "set", "key": "a", "value": True}]),
        ({}, [{"op": "delete", "key": "z"}]),
        ({}, [{"op": "add", "key": 1, "value": 1}]),
        ({}, [{"op": "unknown", "key": "a"}]),
    ]
    for _ in range(35):
        ops = [{"op": rng.choice(["set", "add", "delete", "assert"]), "key": rng.choice(["a", "b", "c"]),
                "value": rng.randrange(-3, 5)} for i in range(rng.randrange(12))]
        cases["atomic_patch"].append(({"a": 1, "b": 2}, ops))
    cases["schedule_tasks"] += [
        ({}, 2),
        ({"a": {"duration": 0, "deps": []}, "b": {"duration": 0, "deps": ["a"]},
          "c": {"duration": 1, "deps": []}}, 2),
        ({"a": {"duration": 2, "deps": []}, "b": {"duration": 2, "deps": []},
          "c": {"duration": 0, "deps": ["a", "b", "b"]}, "d": {"duration": 1, "deps": ["c"]}}, 2),
    ]
    for _ in range(25):
        names = list("abcdef")[:rng.randrange(1, 7)]
        tasks = {name: {"duration": rng.randrange(5), "deps": [p for p in names[:i] if rng.random() < 0.3]}
                 for i, name in enumerate(names)}
        cases["schedule_tasks"].append((tasks, rng.randrange(1, 4)))
    cases["capped_allocate"] += [(0, [1, 2], [0, 5]), (7, [1, 1, 1], [1, 10, 10]),
                                (2, [1, 1, 1], [10, 10, 10]), (10**18 + 1, [10**18, 1], [10**18, 2])]
    for _ in range(40):
        n = rng.randrange(1, 8)
        caps = [rng.randrange(15) for _ in range(n)]
        cases["capped_allocate"].append((rng.randrange(sum(caps) + 1), [rng.randrange(1, 12) for _ in range(n)], caps))
    rows = [{"a": 1, "b": True, "name": "甲|乙"}, {"a": True, "b": False, "name": 'x"y'},
            {"a": None, "name": "a\\b"}, {"b": True}, {"a": -2, "b": None}]
    queries = ['a == 1', 'a == true', 'a == null', '!(a == 1 | b == false)',
               'a == -2 | a == 1 & b == true', '(a == -2 | a == 1) & b == null',
               'name == "甲|乙"', 'name == "x\\"y"', 'name == "a\\\\b"', '!(missing == null)',
               '!!(b == true)', ' ( a == 1 )  ', 'a==1|a==true|a==null']
    cases["select_rows"] = [(rows, q) for q in queries]
    cases["reconcile_events"] = [([],), ([{"id": "x", "key": "a", "version": 2, "source": "b", "op": "delete"},
                                       {"id": "y", "key": "a", "version": 1, "source": "z", "op": "put", "value": {"n": [1]}}],)]
    for _ in range(35):
        events = []
        for i in range(rng.randrange(20)):
            events.append({"id": str(rng.randrange(10)), "key": rng.choice("abc"), "version": rng.randrange(4),
                           "source": rng.choice(["a", "b"]), "op": rng.choice(["put", "delete"]), "value": {"n": [i]}})
        cases["reconcile_events"].append((events,))
    return cases


INVALID_CODE_TESTS = {
    "schedule_tasks": [
        ({"a": {"duration": 1, "deps": ["z"]}}, 1),
        ({"a": {"duration": 1, "deps": ["b"]}, "b": {"duration": 0, "deps": ["a"]}}, 2),
        ({}, 0),
    ],
    "select_rows": [([], q) for q in ("", "a=", "a==", "a==1 a==2", "(a==1", "a==1)", "a==1&&a==2",
                                          'a=="unterminated', "a==unknown", "a==01", "a==1;")],
}


def reasoning_cases():
    result = []
    def add(name, prompt, expected):
        result.append({"name": name, "prompt": prompt + "\n只输出所要求的 JSON，不要加 Markdown。",
                       "expected": expected})
    add("库存去重与撤销",
        '仓库初始 A=30，B=20。按顺序处理事件，重复id只认第一次。事件 e1 给A加12；e2给A减7；'
        'e1再次给A加100；e3给B减6；e4撤销e2（只撤销一次）；e5给B加9；e6再次撤销e2。'
        '撤销不产生新数量事件。输出 {"A":整数,"B":整数}。', {"A": 42, "B": 23})
    solutions = []
    for jobs in itertools.permutations(["研发", "设计", "测试", "运维"]):
        assignment = dict(zip("甲乙丙丁", jobs))
        if (assignment["甲"] not in ("研发", "测试") and assignment["乙"] != "设计"
                and assignment["丙"] in ("研发", "设计") and assignment["丁"] != "运维"
                and assignment["乙"] == "运维"):
            solutions.append(assignment)
    # Add one explicit disambiguating constraint.
    solutions = [x for x in solutions if x["丁"] == "测试"]
    assert len(solutions) == 1
    add("岗位约束",
        '甲乙丙丁分别担任研发、设计、测试、运维，岗位各不相同。甲不是研发或测试；乙不是设计且是运维；'
        '丙是研发或设计；丁不是运维且负责测试。输出四人到岗位的JSON字典。', solutions[0])
    probability = Fraction(6 * 5, 10 * 9) / (1 - Fraction(4 * 3, 10 * 9))
    add("条件概率",
        '盒中6个红球、4个蓝球，无放回抽2个。已知两球至少一个是红球，求两球都是红球的条件概率。'
        '用最简分数输出 {"numerator":整数,"denominator":整数}。',
        {"numerator": probability.numerator, "denominator": probability.denominator})
    add("跨日时区",
        '某任务于北京时间2024-02-29 23:40开始，运行95分钟，然后等待35分钟再运行50分钟。'
        '东京比北京快1小时。输出最终完成时刻 {"beijing":"YYYY-MM-DD HH:MM","tokyo":"YYYY-MM-DD HH:MM"}。',
        {"beijing": "2024-03-01 02:40", "tokyo": "2024-03-01 03:40"})
    # Integer knapsack with two independent constraints.
    choices = [("甲", 4, 3, 11), ("乙", 3, 2, 8), ("丙", 5, 2, 12), ("丁", 2, 3, 7), ("戊", 1, 1, 3)]
    feasible = []
    for mask in range(1 << len(choices)):
        selected = [x for i, x in enumerate(choices) if mask & (1 << i)]
        if sum(x[1] for x in selected) <= 8 and sum(x[2] for x in selected) <= 6:
            feasible.append((sum(x[3] for x in selected), sum(x[1] for x in selected),
                             sum(x[2] for x in selected), [i for i in range(len(choices)) if mask & (1 << i)]))
    winner = min(feasible, key=lambda x: (-x[0], x[1], x[2], x[3]))
    add("双约束项目选择",
        '每个项目只能选一次，格式为(成本,工时,收益)：甲(4,3,11)、乙(3,2,8)、丙(5,2,12)、丁(2,3,7)、戊(1,1,3)。'
        '总成本<=8，总工时<=6，最大化总收益。同收益先选成本低的，再选工时低的，'
        '仍相同则选项目下标列表字典序较小的（甲到戊下标0到4）。'
        '输出 {"projects":[按甲乙丙丁戊顺序排列的项目名],"benefit":整数}。',
        {"projects": [choices[i][0] for i in winner[3]], "benefit": winner[0]})
    add("分层折扣与四舍五入",
        '订单商品原价合计12345分，先打八八折，结果按分四舍五入（0.5进位）；'
        '再使用满10000分减800分券（门槛看打折后金额），最后加运费650分。'
        '用户已付11000分。输出 {"discounted":打折后分数,"due":应付分数,"refund":应退分数}。',
        {"discounted": 10864, "due": 10714, "refund": 286})
    add("版本优先级",
        '规则：只采用 effective_day<=10 的记录，同名记录先比较 revision，再比较 arrival，数值较大者优先。'
        'A记录 (revision=2,day=8,arrival=1,value=40)、(3,12,2,90)、(2,9,3,55)；'
        'B记录(1,5,1,7)、(2,10,4,11)、(2,10,2,12)。输出 {"A":整数,"B":整数,"sum":整数}。',
        {"A": 55, "B": 11, "sum": 66})
    documents = ["【版本1】超时800毫秒，重试5次，批准人甲。"]
    for i in range(1, 151):
        documents.append(f"流水记录{i:03d}：服务svc-{i % 13}，监控采样值{i * 17}，此记录不改变配置。")
    documents.insert(73, "【版本2】仅把超时改为1200毫秒，批准人改为乙。")
    documents.append("【版本3，已撤销】把重试改为1次，超时改为999毫秒。")
    documents.append("【版本4】以最新未撤销配置为基础，仅把重试次数减2，批准人改为丙。")
    add("长材料中的有效修订",
        "\n".join(documents) + '\n版本号越大越新，已撤销版本从未生效。输出最终 {"timeout_ms":整数,"retries":整数,"approver":"姓名"}。',
        {"timeout_ms": 1200, "retries": 3, "approver": "丙"})
    return result


REASONING = reasoning_cases()
