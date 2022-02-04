import ast
import textwrap

from flake_rba import ReferencedBeforeAssignmentASTPlugin


def get_errors(s: str):
    tree = ast.parse(s)
    plugin = ReferencedBeforeAssignmentASTPlugin(tree)
    return {f'{line}:{col} {msg.partition(" ")[0]}' for line, col, msg, _ in plugin.run()}


def test_fn_cross_reference():
    code = textwrap.dedent("""
    a = 1

    async def foo():
        print("foo")
        bar()


    def bar():
        print("bar")
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_return_value_defined_in_async_for():
    code = textwrap.dedent("""
    async def f(values):
        async for value in values:
            print(value)
        return value
    """)
    actual = get_errors(code)
    expected = {'5:11 F823'}
    assert actual == expected


def test_function_variable_mentioned_async_for_in_args():
    code = textwrap.dedent("""
    async def run_fn(values):
        value = 0
        async for value in values:
            print(value)
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_async_with_clause_ok():
    code = textwrap.dedent("""
    fname = 'file.txt'
    async with open(fname) as f:
        f.read()
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_async_with_clause_undefined():
    code = textwrap.dedent("""
    filename = 'file.txt'
    async with open(filename) as f:
        g.read()
    """)
    actual = get_errors(code)
    expected = {"4:4 F823"}
    assert actual == expected


def test_async_with_clause_variables_accessible_after():
    code = textwrap.dedent("""
    fname = 'file.txt'
    async with open(fname) as f:
        f.read()
        k = 1
    print(k)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected
