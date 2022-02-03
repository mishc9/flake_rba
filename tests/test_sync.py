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


def test_fn_with_kwargs():
    code = textwrap.dedent("""
    def bar(cond1, cond2=3):
        if cond1:
            cond2 += 1
            value = cond2
        else:
            value = 1
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_with_args_list():
    code = textwrap.dedent("""
    def bar(cond1, *args):
        if cond1:
            args[0] += 1
            value = args[0]
        else:
            value = 1
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_with_kwargs_dict():
    code = textwrap.dedent("""
    def bar(cond1, **kwargs):
        if cond1:
            kwargs['bar'] += 1
            value = kwargs['bar']
        else:
            value = 1
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_with_args_kwargs_dict():
    code = textwrap.dedent("""
    def bar(cond1, *args, **kwargs):
        if cond1:
            kwargs['bar'] += args[0]
            value = kwargs['bar']
        else:
            value = 1
        return value
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_try_except_ok():
    code = textwrap.dedent("""
    try:
        value = 1
    except Exception:
        value = 1
    value += 1
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_try_except_uncertain():
    code = textwrap.dedent("""
    try:
        value = 1
    except Exception:
        print("fail")
        print("caught an exception")
    value += 1
    """)
    actual = get_errors(code)
    expected = {"7:0 F823"}
    assert actual == expected


def test_try_except_check_e():
    code = textwrap.dedent("""
    try:
        value = 1
    except Exception as e:
        print(e)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_try_except_e_is_missing():
    code = textwrap.dedent("""
    try:
        value = 1
    except Exception as e:
        print(e)
    print(e)
    """)
    actual = get_errors(code)
    expected = {"6:6 F823"}
    assert actual == expected


def test_embedded_try_except():
    code = textwrap.dedent("""
    values = {}
    try:
        value = 1
        try:
            print(values['a'])
        except KeyError:
            value = 2
    except RuntimeError:
        value = 0
    except Exception as e:
        print(e)
    value += 1
    """)
    actual = get_errors(code)
    expected = {"13:0 F823"}
    assert actual == expected


def test_try_except_finally_ok():
    code = textwrap.dedent("""
    try:
        value = 1
        print(value)
    except Exception as e:
        print(e)
    finally:
        value = 3
    print(value)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_try_except_else_ok():
    code = textwrap.dedent("""
    try:
        value = 1
        print(value)
    except Exception as e:
        print(e)
        value = 2
    finally:
        value = 3
    print(value)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_try_except_else_uncertain():
    code = textwrap.dedent("""
    try:
        value = 1
        print(value)
    except Exception as e:
        print(e)
    else:
        value = 3
    print(value)
    """)
    actual = get_errors(code)
    expected = {"9:6 F823"}
    assert actual == expected


def test_tuple_assign():
    code = textwrap.dedent("""
    k, v = 0, 1
    k += v
    v *= 2
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_for_unzip_tuples_ok():
    code = textwrap.dedent("""
    values = [(0, 1), (1, 2)]
    for k, v in values:
        k += v
        v *= 2
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_embedded_tuple_ok():
    code = textwrap.dedent("""
    first = [0, 1, 2]
    second = [3, 4, 5]
    for idx, (k, v) in enumerate(zip(first, second)):
        k += v * idx
        v *= 2
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_simple_set_comprehension_ok():
    code = textwrap.dedent("""
    values = [0, 1, 2]
    {i for i in values}
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_simple_set_comprehension_wrong():
    code = textwrap.dedent("""
    values = [0, 1, 2]
    {k for i in values}
    """)
    actual = get_errors(code)
    expected = {'3:1 F823'}
    assert actual == expected


def test_simple_list_comprehension_ok():
    code = textwrap.dedent("""
    values = [0, 1, 2]
    [i for i in values]
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_unpack_tuple_list_comprehension_ok():
    code = textwrap.dedent("""
    values = [(0, 1), (2, 3)]
    [(i, j) for i, j in values]
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_unpack_tuple_list_comprehension_wrong():
    code = textwrap.dedent("""
    values = [(0, 1), (2, 3)]
    [(i, k) for i, j in values]
    """)
    actual = get_errors(code)
    expected = {"3:5 F823"}
    assert actual == expected


def test_simple_gen_comprehension_ok():
    code = textwrap.dedent("""
    values = [0, 1, 2]
    (i for i in values)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_unpack_tuple_gen_comprehension_ok():
    code = textwrap.dedent("""
    values = [(0, 1), (2, 3)]
    ((i, j) for i, j in values)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_unpack_tuple_gen_comprehension_wrong():
    code = textwrap.dedent("""
    values = [(0, 1), (2, 3)]
    ((i, k) for i, j in values)
    """)
    actual = get_errors(code)
    expected = {"3:5 F823"}
    assert actual == expected


def test_dict_comprehension_ok():
    code = textwrap.dedent("""
    values = {0: 1, 2: 3}
    {j: i for i, j in values.items()}
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_dict_comprehension_wrong():
    code = textwrap.dedent("""
    values = {0: 1, 2: 3}
    {j: k for i, j in values.items()}
    """)
    actual = get_errors(code)
    expected = {"3:4 F823"}
    assert actual == expected


def test_with_clause_ok():
    code = textwrap.dedent("""
    fname = 'file.txt'
    with open(fname) as f:
        f.read()
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_with_clause_undefined():
    code = textwrap.dedent("""
    filename = 'file.txt'
    with open(filename) as f:
        g.read()
    """)
    actual = get_errors(code)
    expected = {"4:4 F823"}
    assert actual == expected


def test_with_clause_variables_accessible_after():
    code = textwrap.dedent("""
    fname = 'file.txt'
    with open(fname) as f:
        f.read()
        k = 1
    print(k)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_static_class_reference_wrong():
    code = textwrap.dedent("""
    class Foo:
        @staticmethod
        def bar():
            Baz.baz()

        @staticmethod
        def baz():
            print("spam")
    """)
    actual = get_errors(code)
    expected = {"5:8 F823"}
    assert actual == expected


def test_static_class_reference_ok():
    code = textwrap.dedent("""
    class Foo:
        @staticmethod
        def bar():
            Foo.baz()

        @staticmethod
        def baz():
            print("spam")
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_static_class_cross_reference_ok():
    code = textwrap.dedent("""
    class Foo:
        @staticmethod
        def bar():
            Bar.foo()

    class Bar:
        @staticmethod
        def foo():
            Foo.bar()
    """)
    # Endless recursion is not the case here
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_text_annotation_ok():
    code = textwrap.dedent("""
    from typing import List
    values: List[int] = [1, 2, 3]
    """)
    # Endless recursion is not the case here
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_text_annotation_bad_typing_import():
    code = textwrap.dedent("""
    from typing import Dict
    values: List[int] = [1, 2, 3]
    """)
    # Endless recursion is not the case here
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_assign_to_list():
    # Unfortunately, this is syntactically correct and we have to check this.
    code = textwrap.dedent("""
    [k, v] = 0, 1
    k += v
    v *= 2
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_if_else_return_ok():
    code = textwrap.dedent("""
    def fn(value):
        if value > 0:
            a = 1
        elif value < 0:
            a = 2
        else:
            return -1
        return a
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_if_else_raise_ok():
    code = textwrap.dedent("""
    def fn(value):
        if value > 0:
            a = 1
        elif value < 0:
            a = 2
        else:
            raise ValueError
        return a
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_if_else_return_failed():
    code = textwrap.dedent("""
    def fn(value):
        if value > 0:
            a = 1
        elif value < 0:
            a = 2
            return - 1
        else:
            b = 2
        return a
    """)
    actual = get_errors(code)
    expected = {'10:11 F823'}
    assert actual == expected


def test_try_except_return():
    code = textwrap.dedent("""
    def fn(value):
        try:
            a = 1
        except Exception as e:
            return -1
        return a
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_try_except_re_raise():
    code = textwrap.dedent("""
    def fn(value):
        try:
            a = 1
        except Exception as e:
            raise e
        return a
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_lambda():
    code = textwrap.dedent("""
    (lambda x: print(x))()
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_lambda_failed():
    code = textwrap.dedent("""
    (lambda y: print(x))()
    """)
    actual = get_errors(code)
    expected = {'2:17 F823'}
    assert actual == expected


def test_lambda_pair_args():
    code = textwrap.dedent("""
    (lambda x, y: print(x, y))()
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_type_annotated_parameters():
    code = textwrap.dedent("""
    def fn(y: int, x: str = 1):
        print(x, y)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_type_annotated_parameters_star_syntax():
    code = textwrap.dedent("""
    def fn(y: int, *, x: str = 1):
        print(x, y)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_type_annotated_parameters_args_syntax():
    code = textwrap.dedent("""
    def fn(y: int, *args, x: str = 1):
        print(x, y)
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected


def test_fn_cross_reference():
    code = textwrap.dedent("""
    a = 1

    def foo():
        print("foo")
        bar()


    def bar():
        print("bar")
        foo()
    """)
    actual = get_errors(code)
    expected = set()
    assert actual == expected
