import ast
from typing import List, Any


class Frame(list):
    pass


class CFVisitor(ast.NodeVisitor):
    default_names = list(__builtins__.keys())

    def __init__(self):
        super().__init__()
        self.stack: List[Frame] = []
        self.errors = []

    def visit_Assign(self, node: ast.Assign) -> Any:
        targets = node.targets
        self.stack[-1].append(targets[0].id)
        print(self.stack)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.stack[-1].append(node.name)
        print(self.stack)
        try:
            self.stack.append(Frame())
            self.generic_visit(node)
        finally:
            self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        pass

    def visit_Import(self, node: ast.Import) -> Any:
        pass

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        pass

    def visit_Module(self, node: ast.Module) -> Any:
        frame = Frame()
        self.stack.append(frame)
        try:
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)
        finally:
            self.stack.pop()

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if hasattr(node, 'id') and not (
                node.id in self.default_names or self._check_stack(node.id)):
            print(self.stack)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def visit_Call(self, node: ast.Call) -> Any:
        if hasattr(node, 'id') and not (
                node.id in self.default_names or self._check_stack(node.id)):
            print(self.stack)
            self.errors.append()
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def _check_stack(self, name):
        for frame in self.stack:
            for entry in frame:
                if entry == name:
                    return True
        return False
