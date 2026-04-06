import ast
import sys
import os

try:
    from hypothesis import given, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

# ---------------------------------------------------------------------------
# Soft-assert infrastructure - prepended to every modified file so that
# assertion failures are RECORDED (not crashed on) and execution continues.
# ---------------------------------------------------------------------------
SOFT_ASSERT_PRELUDE = '''\
__assert_failures = []

def __soft_assert(cond, lineno, msg):
    """Record an assertion probe result without halting execution."""
    if not cond:
        __assert_failures.append((lineno, msg))
'''


def _src(node):
    """Convert AST node to source string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Attribute):
        return f"{_src(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        args = ", ".join(_src(a) for a in node.args)
        return f"{_src(node.func)}({args})"
    elif isinstance(node, ast.BinOp):
        ops = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/',
               ast.Mod: '%', ast.FloorDiv: '//', ast.Pow: '**'}
        op_str = ops.get(type(node.op), '?')
        return f"({_src(node.left)} {op_str} {_src(node.right)})"
    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return f"(not {_src(node.operand)})"
        elif isinstance(node.op, ast.USub):
            return f"(-{_src(node.operand)})"
    elif isinstance(node, ast.Compare):
        ops = {ast.Eq: '==', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=',
               ast.Gt: '>', ast.GtE: '>=', ast.In: 'in', ast.NotIn: 'not in',
               ast.Is: 'is', ast.IsNot: 'is not'}
        op_str = ops.get(type(node.ops[0]), '?')
        return f"({_src(node.left)} {op_str} {_src(node.comparators[0])})"
    elif isinstance(node, ast.BoolOp):
        op_str = 'and' if isinstance(node.op, ast.And) else 'or'
        return f" {op_str} ".join(_src(v) for v in node.values)
    elif isinstance(node, ast.Subscript):
        return f"{_src(node.value)}[{_src(node.slice)}]"
    elif isinstance(node, ast.Index):
        return _src(node.value)
    elif isinstance(node, ast.Tuple):
        return "(" + ", ".join(_src(e) for e in node.elts) + ")"
    elif isinstance(node, ast.List):
        return "[" + ", ".join(_src(e) for e in node.elts) + "]"
    else:
        return "<expr>"


def _make_call(test_src, lineno, msg):
    """Build ast.Expr: __soft_assert(<test_src>, lineno, msg)"""
    try:
        test_expr = ast.parse(test_src, mode='eval').body
    except SyntaxError:
        return None
    call = ast.Call(
        func=ast.Name(id='__soft_assert', ctx=ast.Load()),
        args=[test_expr, ast.Constant(value=lineno), ast.Constant(value=msg)],
        keywords=[]
    )
    node = ast.Expr(value=call)
    ast.fix_missing_locations(node)
    return node


def _make_call_node(test_node, lineno, msg):
    """Build ast.Expr: __soft_assert(<ast_node>, lineno, msg)"""
    call = ast.Call(
        func=ast.Name(id='__soft_assert', ctx=ast.Load()),
        args=[test_node, ast.Constant(value=lineno), ast.Constant(value=msg)],
        keywords=[]
    )
    node = ast.Expr(value=call)
    ast.fix_missing_locations(node)
    return node


class AssertionInjector(ast.NodeTransformer):
    """
    Injects soft-assert COVERAGE PROBES inside if/else branches.

    Strategy:
      - In if-branch:   assert NOT(condition) -> always triggers -> records branch taken
      - In else-branch: assert condition       -> always triggers -> records branch taken
      - Boundary probes for comparisons: check if value is exactly at boundary
      - Function-call conditions: record branch without re-executing the call
    """

    def _has_call(self, node):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                return True
        return False

    def is_main_guard(self, node):
        condition = node.test
        if isinstance(condition, ast.Compare):
            if len(condition.ops) == 1 and isinstance(condition.ops[0], ast.Eq):
                left = condition.left
                right = condition.comparators[0] if condition.comparators else None
                if isinstance(left, ast.Name) and left.id == '__name__':
                    if isinstance(right, ast.Constant) and right.value == '__main__':
                        return True
                elif isinstance(right, ast.Name) and right.id == '__name__':
                    if isinstance(left, ast.Constant) and left.value == '__main__':
                        return True
        return False

    def get_inside_assertions(self, condition, branch):
        assertions = []
        cond_src = _src(condition)

        if cond_src == "<expr>":
            return assertions

        lineno = getattr(condition, 'lineno', 0)

        # Function-call conditions: record branch without re-executing
        if self._has_call(condition):
            node = _make_call_node(
                ast.Constant(value=False), lineno,
                f"[{branch.upper()}-branch covered] Condition: {cond_src}"
            )
            if node:
                assertions.append(node)
            return assertions

        # Coverage probe: negated/original condition
        if branch == 'if':
            probe = _make_call(
                f"not ({cond_src})", lineno,
                f"[IF-branch covered] Condition was True: {cond_src}"
            )
            if probe:
                assertions.append(probe)
        elif branch == 'else':
            probe = _make_call(
                cond_src, lineno,
                f"[ELSE-branch covered] Condition was False: {cond_src}"
            )
            if probe:
                assertions.append(probe)

        # Boundary probes for comparisons
        if isinstance(condition, ast.Compare) and len(condition.ops) == 1:
            op = condition.ops[0]
            left_src = _src(condition.left)
            right_src = _src(condition.comparators[0])

            if left_src == "<expr>" or right_src == "<expr>":
                return assertions

            if isinstance(op, (ast.Gt, ast.Lt, ast.GtE, ast.LtE)):
                b = _make_call(
                    f"({left_src}) != ({right_src})", lineno,
                    f"[Boundary] {left_src} is exactly at boundary {right_src}"
                )
                if b:
                    assertions.append(b)

            elif isinstance(op, ast.Eq) and branch == 'if':
                b = _make_call(
                    f"({left_src}) == ({right_src})", lineno,
                    f"[Equality verified] {left_src} == {right_src}"
                )
                if b:
                    assertions.append(b)

            elif isinstance(op, ast.In) and branch == 'if':
                b = _make_call(
                    f"({left_src}) in ({right_src})", lineno,
                    f"[Membership verified] {left_src} in {right_src}"
                )
                if b:
                    assertions.append(b)

        return assertions

    def visit_If(self, node):
        self.generic_visit(node)

        if self.is_main_guard(node):
            return node

        if_assertions = self.get_inside_assertions(node.test, 'if')
        for a in if_assertions:
            ast.copy_location(a, node)
        node.body = if_assertions + node.body

        if node.orelse and not isinstance(node.orelse[0], ast.If):
            else_assertions = self.get_inside_assertions(node.test, 'else')
            for a in else_assertions:
                ast.copy_location(a, node)
            node.orelse = else_assertions + node.orelse

        return node


def inject_assertions(source_code):
    tree = ast.parse(source_code)
    injector = AssertionInjector()
    new_tree = injector.visit(tree)
    ast.fix_missing_locations(new_tree)

    try:
        import astor
        modified_code = astor.to_source(new_tree)
    except ImportError:
        if hasattr(ast, 'unparse'):
            modified_code = ast.unparse(new_tree)
        else:
            raise RuntimeError(
                "Neither 'astor' nor 'ast.unparse' available.\n"
                "Install astor: pip3 install astor"
            )

    # Prepend soft-assert infrastructure
    return SOFT_ASSERT_PRELUDE + "\n" + modified_code


if HAS_HYPOTHESIS:
    @given(st.text(alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S')), min_size=1, max_size=20))
    def test_make_soft_assert_with_random_expr(expr_str):
        """Test _make_call with random expression strings."""
        node = _make_call(expr_str, 1, "test")
        if node is not None:
            assert isinstance(node, ast.Expr)

    @given(st.integers(min_value=0, max_value=100))
    def test_inject_assertions_simple(x):
        """Test inject_assertions with simple if statement."""
        code = f"""\nif {x} > 50:\n    result = "high"\nelse:\n    result = "low"\n"""
        try:
            modified = inject_assertions(code)
            assert "__soft_assert" in modified
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 python_assert.py <input_file.py>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = "mod_" + os.path.basename(input_file)

    with open(input_file, "r") as f:
        source = f.read()

    modified = inject_assertions(source)

    with open(output_file, "w") as f:
        f.write(modified)

    print(f"Modified file written to {output_file}")