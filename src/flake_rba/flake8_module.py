import ast
from typing import NamedTuple, Iterator, List, Any, Union


class Frame(list):
    pass


class ReferencedBeforeAssignmentNodeVisitor(ast.NodeVisitor):
    default_names = list(__builtins__.keys())

    def __init__(self):
        super().__init__()
        self.stack: List[Frame] = []
        self.errors = []

    def visit_Assign(self, node: ast.Assign) -> Any:
        targets = node.targets
        self.stack[-1].append(targets[0].id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.stack[-1].append(node.name)
        try:
            self.stack.append(Frame())
            for arg in node.args.args:
                self.stack[-1].append(arg.arg)
            self.generic_visit(node)
        finally:
            self.stack.pop()

    def visit_For(self, node: ast.For) -> Any:
        frame = Frame()
        self.stack.append(frame)
        try:
            frame.append(node.target.id)
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)
        finally:
            self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        pass

    def _visit_Import(self, node: Union[ast.Import, ast.ImportFrom]):
        self.stack[-1].extend([
            sub_node.asname if sub_node.asname is not None else sub_node.name
            for sub_node in node.names
        ])
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        self._visit_Import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        self._visit_Import(node)

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
            self.errors.append(
                Flake8ASTErrorInfo(
                    node.lineno,
                    node.col_offset,
                    self.msg,
                    type(node)
                )
            )
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
            self.errors.append(
                Flake8ASTErrorInfo(
                    node.lineno,
                    node.col_offset,
                    self.msg,
                    type(node)
                )
            )
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

    @property
    def msg(self):
        return "RBA101 referenced_before_assignment"


class Flake8ASTErrorInfo(NamedTuple):
    line_number: int
    offset: int
    msg: str
    cls: type  # unused as for now


class ReferencedBeforeAssignmentASTPlugin:
    name = 'rba_ast'
    version = '0.0.0'

    def __init__(self, tree: ast.AST):
        self._tree = tree

    def run(self) -> Iterator[Flake8ASTErrorInfo]:
        visitor = ReferencedBeforeAssignmentNodeVisitor()
        visitor.visit(self._tree)
        yield from visitor.errors
