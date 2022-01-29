# Flake module for detection of 'referenced-before-assignment'

-- WIP --

To the best of my knowledge, flake8/pylint/pyflakes are still lacking reliable 
detection of 'referenced-before-assignment'.

`pyflakes` is able to detect omitted `nonclocal` or `global` keywords:

```python3
def make_counter():
    count = 0
    def inner():
        count += 1
        return count
    return inner
```
-- got ` local variable 'count' defined in enclosing scope on line 4 
referenced before assignment`.

But it doesn't handle variables, assigned in `for` loops, within `if/else` 
scopes or `try/except` clauses.

It's possible to use external tools like static analysis tools embedded in 
IDE or `pyright`. But for some use cases flake8 plugin might be a better 
choice. 

![Tests](https://github.com/mishc9/flake_rba/actions/workflows/tests.yml/badge.svg)
