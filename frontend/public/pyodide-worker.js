// Runs the learner's Python in the browser (Pyodide = CPython compiled to WebAssembly).
// It lives in a Web Worker so an infinite loop can be stopped by terminating the worker,
// and untrusted code never runs on the backend machine.
//
// Message in:  { id, code, functionName, tests: [{args, expected}] }
// Message out: { id, ok: true, results: [{passed, args, expected, got, error, stdout}] }
//           or { id, ok: false, error }

const PYODIDE_VERSION = "0.27.7";
importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`);

const pyodideReady = loadPyodide();

const HARNESS = `
import copy, io, json, math, sys, traceback

def _same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b if isinstance(a, bool) and isinstance(b, bool) else False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    return a == b

def _jsonable(value):
    try:
        return json.loads(json.dumps(value))
    except Exception:
        return repr(value)

def _run(code, function_name, tests_json):
    namespace = {"__name__": "__solution__"}
    try:
        exec(compile(code, "solution.py", "exec"), namespace)
    except Exception:
        return json.dumps({"ok": False, "error": traceback.format_exc(limit=1)})
    fn = namespace.get(function_name)
    if not callable(fn):
        return json.dumps({"ok": False, "error": f"Define a function called {function_name}()."})
    results = []
    for test in json.loads(tests_json):
        out = io.StringIO()
        sys.stdout = out
        try:
            got = fn(*copy.deepcopy(test["args"]))
            results.append({"passed": _same(got, test["expected"]), "args": test["args"], "expected": test["expected"],
                            "got": _jsonable(got), "error": None, "stdout": out.getvalue()[-500:]})
        except Exception as exc:
            results.append({"passed": False, "args": test["args"], "expected": test["expected"], "got": None,
                            "error": f"{type(exc).__name__}: {exc}", "stdout": out.getvalue()[-500:]})
        finally:
            sys.stdout = sys.__stdout__
    return json.dumps({"ok": True, "results": results})
`;

let harnessLoaded = false;

self.onmessage = async (event) => {
  const { id, code, functionName, tests } = event.data;
  try {
    const pyodide = await pyodideReady;
    if (!harnessLoaded) {
      pyodide.runPython(HARNESS);
      harnessLoaded = true;
    }
    const run = pyodide.globals.get("_run");
    const output = run(code, functionName, JSON.stringify(tests));
    run.destroy();
    self.postMessage({ id, ...JSON.parse(output) });
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error && error.message ? error.message : error) });
  }
};
