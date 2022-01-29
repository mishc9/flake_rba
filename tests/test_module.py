import ast
import textwrap

from flake_rba.flake8_module import ReferencedBeforeAssignmentASTPlugin


def get_errors(s: str):
    tree = ast.parse(s)
    plugin = ReferencedBeforeAssignmentASTPlugin(tree)
    return {f'{line}:{col} {msg.partition(" ")[0]}' for line, col, msg, _ in plugin.run()}


def test_reference_not_imported():
    code = textwrap.dedent("""
    from ast import walk
    print(a)
    """)
    actual = get_errors(code)
    expected = {'3:6 RBA101'}
    assert actual == expected


def test_access_not_imported():
    code = textwrap.dedent("""
    import ast
    print(walk)
    """)
    actual = get_errors(code)
    expected = {'3:6 RBA101'}
    assert actual == expected


def test_import_is_valid():
    code = textwrap.dedent("""
    import ast
    print(ast)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_import_from_is_valid():
    code = textwrap.dedent("""
    from ast import walk
    print(walk)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_multiple_import_from_are_valid():
    code = textwrap.dedent("""
    from ast import walk, iter_fields
    print(walk, iter_fields)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_access_renamed_import_from_fail():
    code = textwrap.dedent("""
    from ast import walk, iter_fields as itf
    print(walk, iter_fields)
    """)
    actual = get_errors(code)
    expected = {'3:12 RBA101'}
    assert actual == expected


def test_access_renamed_import_from_normal():
    code = textwrap.dedent("""
    from ast import iter_fields as itf
    print(itf)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_check_normal_fn_definition():
    code = textwrap.dedent("""
    def foo():
        return "bar"
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_check_fn_definition_with_values():
    code = textwrap.dedent("""
    def foo():
        value = 1
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_access_local_variable():
    code = textwrap.dedent("""
    def foo():
        value = 1
        return value
    print(value)
    """)
    actual = get_errors(code)
    expected = {'5:6 RBA101'}
    assert actual == expected


def test_use_value_after_for_loop():
    code = textwrap.dedent("""
    values = [1, 2, 3]
    for value in values:
        print(value)
    print(value)
    value += 1
    """)
    actual = get_errors(code)
    expected = {'5:6 RBA101', '6:0 RBA101'}
    assert actual == expected


def test_use_value_after_for_loop_in_function():
    code = textwrap.dedent("""
    def fn(values):
        for value in values:
            print(value)
        print(value)
        value += 1
    """)
    actual = get_errors(code)
    expected = {'5:10 RBA101', '6:4 RBA101'}
    assert actual == expected


def test_assign_value():
    code = textwrap.dedent("""
    val = 1
    val_ += 2
    """)
    actual = get_errors(code)
    expected = {'3:0 RBA101'}
    assert actual == expected


def test_return_value_defined_in_for():
    code = textwrap.dedent("""
    x = 1
    def f(values):
        for value in values:
            print(value)
        return value
    """)
    actual = get_errors(code)
    expected = {'6:11 RBA101'}
    assert actual == expected
