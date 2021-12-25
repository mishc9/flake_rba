from src.py_template.template import hello_world


def test_template(fixture_template):
    assert hello_world() == fixture_template
