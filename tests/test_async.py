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
