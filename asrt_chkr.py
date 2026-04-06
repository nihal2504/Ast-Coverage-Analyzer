# asrt_chkr.py — Assertion Checker
# Executes the modified Python file statement-by-statement,
# collects both hard assert failures and soft-assert probe results.

import ast
import sys
import traceback
from types import CodeType


def compile_node(node, filename):
    """Compile a single AST node into a code object preserving line numbers."""
    mod = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(mod)
    return compile(mod, filename, "exec")


def run_and_collect(mod_file):
    try:
        with open(mod_file, "r") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"File not found: {mod_file}")
        return

    # Parse AST once
    try:
        tree = ast.parse(source, filename=mod_file)
    except SyntaxError as e:
        print("Syntax error while parsing the file:")
        print(e)
        return

    namespace = {}
    hard_failures = []   # (lineno, reason) — from hard assert statements
    other_errors = []    # (lineno, exc_type, message)

    # Set __name__ to '__main__' so the main guard will execute
    namespace['__name__'] = '__main__'

    # Execute top-level statements one by one
    for node in tree.body:
        lineno = getattr(node, "lineno", None)
        try:
            code_obj = compile_node(node, mod_file)
            exec(code_obj, namespace)
        except AssertionError as e:
            # Extract traceback info to get the exact failing line
            tb = traceback.extract_tb(sys.exc_info()[2])
            if tb:
                tb_line = tb[-1].lineno
            else:
                tb_line = lineno
            reason = str(e) if str(e) else "<no message>"
            hard_failures.append((tb_line, reason))
            # continue executing remaining top-level nodes
        except Exception as e:
            tb = traceback.extract_tb(sys.exc_info()[2])
            if tb:
                tb_line = tb[-1].lineno
            else:
                tb_line = lineno
            other_errors.append((tb_line, type(e).__name__, str(e)))
            # continue executing remaining top-level nodes

    # Collect soft-assert failures recorded by __soft_assert()
    soft_failures = []
    recorded = namespace.get("__assert_failures")
    if isinstance(recorded, list):
        for item in recorded:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                soft_failures.append((item[0], item[1]))

    # Merge all failures and sort by line number
    all_failures = hard_failures + soft_failures
    all_failures.sort(key=lambda x: (x[0] if x[0] is not None else 0))
    other_errors.sort(key=lambda x: (x[0] if x[0] is not None else 0))

    # Deduplicate for unique branch count
    unique_failures = list(dict.fromkeys((ln, reason) for ln, reason in all_failures))

    # Find all injected soft asserts to determine the missed ones
    all_injected = []
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.Call):
            func = ast_node.func
            if getattr(func, "id", None) == "__soft_assert":
                if len(ast_node.args) >= 3:
                    ln_arg = ast_node.args[1]
                    msg_arg = ast_node.args[2]
                    ln = getattr(ln_arg, "value", getattr(ln_arg, "n", 0)) # fallback for older python
                    msg = getattr(msg_arg, "value", getattr(msg_arg, "s", "<unknown>"))
                    all_injected.append((ln, msg))

    unique_injected = list(dict.fromkeys(all_injected))
    covered_set = set((ln, reason) for ln, reason in unique_failures)
    missed_assertions = [item for item in unique_injected if item not in covered_set]
    total_injected = len(unique_injected)

    # Print summary
    print("\n=== Assertion Summary ===")
    if not all_failures:
        print("No assertion violations.")
    else:
        print(f"Total assertion violations: {len(all_failures)}")
        print(f"Unique assertions covered: {len(unique_failures)}")
        print(f"Total tracked assertions: {total_injected}")
        for ln, reason in unique_failures:
            print(f" - Line {ln}: {reason}")

    if missed_assertions:
        print(f"\nMissed (Passed) Assertions: {len(missed_assertions)}")
        for ln, msg in missed_assertions:
            print(f" - Line {ln}: [MISSED] {msg}")

    if other_errors:
        print("\n=== Other runtime errors (non-assert) ===")
        for ln, exc_type, msg in other_errors:
            print(f" - Line {ln}: {exc_type}: {msg}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 asrt_chkr.py <mod_file.py>")
        sys.exit(1)
    run_and_collect(sys.argv[1])
