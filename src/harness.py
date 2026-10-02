import ast, sys, io, json, math, time, traceback, collections

class BudgetExceeded(BaseException):
    pass

class _Meter:
    __slots__ = ("ops", "limit")

_M = _Meter()
_M.ops = 0
_M.limit = 10 ** 9

def _eh_t():
    _M.ops += 1
    if _M.ops > _M.limit:
        raise BudgetExceeded()
    return True

def _charge(n):
    if n:
        _M.ops += n
        if _M.ops > _M.limit:
            raise BudgetExceeded()

def _size(x):
    try:
        return len(x)
    except Exception:
        return 0

def _nlogn(n):
    return int(n * max(1.0, math.log2(n))) if n > 1 else n

_LINEAR = {id(f): f for f in (sum, min, max, list, tuple, set, frozenset, dict, any, all,
                              collections.Counter, collections.deque, bytes, bytearray)}
_SORT = {id(sorted): sorted}
_CONTAINERS = (list, tuple, str, dict, set, frozenset, bytes, bytearray,
               collections.Counter, collections.deque, collections.defaultdict, collections.OrderedDict)
_SELF_LINEAR = {"count", "index", "find", "rfind", "rindex", "remove", "insert", "replace", "split",
                "copy", "reverse", "most_common", "elements", "total", "strip", "lower", "upper",
                "startswith", "endswith", "values", "keys", "items"}
_ARG_LINEAR = {"join", "update", "extend", "subtract", "union", "intersection", "difference",
               "issubset", "issuperset"}

def _eh_c(f, *a, **k):
    fid = id(f)
    if fid in _LINEAR:
        if len(a) == 1:
            _charge(_size(a[0]))
    elif fid in _SORT:
        if a:
            _charge(_nlogn(_size(a[0])))
    else:
        s = getattr(f, "__self__", None)
        if s is not None and isinstance(s, _CONTAINERS):
            name = getattr(f, "__name__", "")
            if name == "sort":
                _charge(_nlogn(_size(s)))
            elif name == "pop":
                if a and a[0] == 0:
                    _charge(_size(s))
            elif name in ("values", "keys", "items"):
                pass
            elif name in _SELF_LINEAR:
                _charge(_size(s))
            elif name in _ARG_LINEAR:
                if a:
                    _charge(_size(a[0]))
    return f(*a, **k)

def _eh_sl(v, lo, hi, st):
    r = v[lo:hi:st]
    _charge(_size(r))
    return r

def _eh_in(x, y):
    if isinstance(y, (list, tuple, str, collections.deque)):
        _charge(len(y))
    return x in y

def _tick_call():
    return ast.Call(func=ast.Name(id="_eh_t", ctx=ast.Load()), args=[], keywords=[])

class _Instrument(ast.NodeTransformer):
    def _tick_body(self, node):
        self.generic_visit(node)
        node.body.insert(0, ast.copy_location(ast.Expr(value=_tick_call()), node.body[0] if node.body else node))
        return node

    visit_For = _tick_body
    visit_While = _tick_body
    visit_AsyncFor = _tick_body
    visit_FunctionDef = _tick_body
    visit_AsyncFunctionDef = _tick_body

    def visit_comprehension(self, node):
        self.generic_visit(node)
        node.ifs.insert(0, _tick_call())
        return node

    def visit_Lambda(self, node):
        self.generic_visit(node)
        node.body = ast.BoolOp(op=ast.And(), values=[_tick_call(), node.body])
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in ("super", "_eh_t"):
            return node
        return ast.copy_location(ast.Call(func=ast.Name(id="_eh_c", ctx=ast.Load()),
                                          args=[node.func] + node.args, keywords=node.keywords), node)

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and isinstance(node.slice, ast.Slice):
            sl = node.slice
            none = lambda: ast.Constant(value=None)
            return ast.copy_location(ast.Call(func=ast.Name(id="_eh_sl", ctx=ast.Load()),
                                              args=[node.value, sl.lower or none(), sl.upper or none(), sl.step or none()],
                                              keywords=[]), node)
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
            call = ast.Call(func=ast.Name(id="_eh_in", ctx=ast.Load()), args=[node.left, node.comparators[0]], keywords=[])
            if isinstance(node.ops[0], ast.NotIn):
                return ast.copy_location(ast.UnaryOp(op=ast.Not(), operand=call), node)
            return ast.copy_location(call, node)
        return node

def _fmt_error(e, filename):
    tb = traceback.extract_tb(e.__traceback__)
    line = None
    for fr in tb:
        if fr.filename == filename:
            line = fr.lineno
    msg = "".join(traceback.format_exception_only(type(e), e)).strip()
    return {"line": line, "message": msg}

def _normalize(kind, v):
    if kind == "point":
        if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(t, int) and not isinstance(t, bool) for t in v):
            return [int(v[0]), int(v[1])]
        return None
    if kind == "int":
        if isinstance(v, int) and not isinstance(v, bool):
            return int(v)
        return None
    if kind == "bool":
        if isinstance(v, bool):
            return v
        return None
    return None

def run_job(job_json):
    job = json.loads(job_json)
    filename = job["filename"]
    fn_name = job["fn"]
    kind = job["kind"]
    out = {"compile": None, "cases": []}
    try:
        tree = ast.parse(job["code"], filename=filename)
        tree = _Instrument().visit(tree)
        ast.fix_missing_locations(tree)
        code = compile(tree, filename, "exec")
    except SyntaxError as e:
        out["compile"] = {"line": e.lineno, "message": "SyntaxError: " + str(e.msg)}
        return json.dumps(out)
    except Exception as e:
        out["compile"] = {"line": None, "message": repr(e)}
        return json.dumps(out)

    g = {"__name__": "__contract__", "_eh_t": _eh_t, "_eh_c": _eh_c, "_eh_sl": _eh_sl, "_eh_in": _eh_in}
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        _M.ops = 0
        _M.limit = 10 ** 7
        exec(code, g)
    except BaseException as e:
        sys.stdout = old
        out["compile"] = _fmt_error(e, filename) if not isinstance(e, BudgetExceeded) else {"line": None, "message": "Module-level code ran out of budget"}
        return json.dumps(out)
    finally:
        sys.stdout = old
    f = g.get(fn_name)
    if not callable(f):
        out["compile"] = {"line": None, "message": "Define a function named %s(...)" % fn_name}
        return json.dumps(out)

    for case in job["cases"]:
        args = case["args"]
        if case.get("copy"):
            args = json.loads(json.dumps(args))
        buf = io.StringIO()
        sys.stdout = buf
        _M.ops = 0
        _M.limit = case.get("budget", 5 * 10 ** 7)
        res = {"id": case["id"]}
        t0 = time.perf_counter()
        try:
            v = f(*args)
            res["status"] = "ok"
            res["value"] = _normalize(kind, v)
            res["repr"] = repr(v)[:200]
        except BudgetExceeded:
            res["status"] = "budget"
        except RecursionError as e:
            res["status"] = "error"
            res["error"] = {"line": None, "message": "RecursionError: maximum recursion depth exceeded"}
        except BaseException as e:
            res["status"] = "error"
            res["error"] = _fmt_error(e, filename)
        finally:
            sys.stdout = old
        res["ops"] = _M.ops
        res["ms"] = round((time.perf_counter() - t0) * 1000, 1)
        res["stdout"] = buf.getvalue()[:1500]
        out["cases"].append(res)
    return json.dumps(out)
