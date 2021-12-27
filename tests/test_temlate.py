from py_template.template import hello_world


def test_template():
    assert hello_world() == "Hello World!"
