import ast
import textwrap

from flake_rba.plugin import ReferencedBeforeAssignmentASTPlugin


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
    expected = {'3:6 F823'}
    assert actual == expected


def test_access_not_imported():
    code = textwrap.dedent("""
    import ast
    print(walk)
    """)
    actual = get_errors(code)
    expected = {'3:6 F823'}
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
    expected = {'3:12 F823'}
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
    expected = {'5:6 F823'}
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
    expected = {'5:6 F823', '6:0 F823'}
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
    expected = {'5:10 F823', '6:4 F823'}
    assert actual == expected


def test_assign_value():
    code = textwrap.dedent("""
    val = 1
    val_ += 2
    """)
    actual = get_errors(code)
    expected = {'3:0 F823'}
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
    expected = {'6:11 F823'}
    assert actual == expected


def test_function_variable_mentioned_in_header():
    code = textwrap.dedent("""
    def run_fn(value):
        values = [1, 2, 3]
        for value in values:
            print(value)
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_method_definition_normal():
    code = textwrap.dedent("""
    class Foo:
        def run(self, value):
            values = [1, 2, 3]
            for value in values:
                print(value)
            return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_method_definition_for_loop_no_firm_reference():
    code = textwrap.dedent("""
    class Foo:
        def run(self):
            values = [1, 2, 3]
            for value in values:
                print(value)
            return value
    """)
    actual = get_errors(code)
    expected = {'7:15 F823'}
    assert actual == expected


def test_class_with_two_methods_normal():
    code = textwrap.dedent("""
    class Foo:
        class_att = 1
        
        def bar(self, inp):
            if inp:
                return 1
            self.foo(inp)
            
        def foo(self, inp):
            if not inp:
                return 0
            self.bar(inp)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_case_if_else_uncertain():
    code = textwrap.dedent("""
    def foo(cond):
        if cond:
            value = 1
        else:
            print("spam")
        return value
    """)
    actual = get_errors(code)
    expected = {"7:11 F823"}
    assert actual == expected


def test_case_if_elif_uncertain():
    code = textwrap.dedent("""
    def foo(cond):
        if cond == 1:
            value = 1
        elif cond == 2:
            value = 2
        return value
    """)
    actual = get_errors(code)
    expected = {"7:11 F823"}
    assert actual == expected


def test_case_if_multiple_elif_uncertain():
    code = textwrap.dedent("""
    def foo(cond):
        if cond == 1:
            value = 1
        elif cond == 2:
            value = 2
        elif cond == 3:
            value = 3
        return value
    """)
    actual = get_errors(code)
    expected = {"9:11 F823"}
    assert actual == expected


def test_case_if_multiple_elif_set_ok():
    code = textwrap.dedent("""
    def foo(cond):
        if cond == 1:
            value = 1
        elif cond == 2:
            value = 2
        elif cond == 3:
            value = 3
        else:
            value = 4
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_simple_if_else_set_ok():
    code = textwrap.dedent("""
    def foo(cond):
        if cond == 1:
            value = 1
        else:
            value = 2
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_if_else_embedded_if_else_ok():
    code = textwrap.dedent("""
    def bar(cond1, cond2):
        if cond1:
            if cond2:
                value = 1
            else:
                value = 2
        else:
            value = 3
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_if_else_embedded_if_else_uncertain():
    code = textwrap.dedent("""
    def bar(cond1, cond2):
        if cond1:
            if cond2 > 0:
                value = 1
            elif cond2 < 0:
                value = 2
        else:
            value = 3
        return value
    """)
    actual = get_errors(code)
    expected = {"10:11 F823"}
    assert actual == expected


def test_if_else_multiple_embedded_if_else_uncertain():
    code = textwrap.dedent("""
    def bar(cond1, cond2):
        if cond1:
            if cond2 > 0:
                value = 1
            elif cond2 < 0:
                value = 2
        else:
            if cond2 > 0:
                value = 1
            elif cond2 < 0:
                value = 2
        return value
    """)
    actual = get_errors(code)
    expected = {"13:11 F823"}
    assert actual == expected


def test_if_else_only_else_set():
    code = textwrap.dedent("""
    def bar(cond1):
        if cond1:
            print("hello")
        else:
            value = 1
        return value
    """)
    actual = get_errors(code)
    expected = {"7:11 F823"}
    assert actual == expected
