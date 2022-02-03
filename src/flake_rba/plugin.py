import ast
from typing import NamedTuple, Iterator, List, Any, Union, Set


class Frame(list):  # type: ignore
    pass


class ReferencedBeforeAssignmentNodeVisitor(ast.NodeVisitor):
    default_names = list(__builtins__.keys())  # type: ignore

    def __init__(self):
        super().__init__()
        self.stack: List[Frame] = []
        self.errors = []
        # for if/else control flow. Todo: use single control flow stack
        self.tracking_stack = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> Any:
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        assign_target = node.target
        # Todo: add check for imports of non-annotated things
        self._visit_assign_target(assign_target, node)

    def visit_Assign(self, node: ast.Assign) -> Any:
        # Todo: check multiple targets
        assign_target = node.targets[0]
        self._visit_assign_target(assign_target, node)

    def _visit_assign_target(self, assign_target, node=None):
        # Todo: properly check these types below
        # Todo: add assignSub/assignAdd etc. operations
        if isinstance(assign_target, ast.Name):
            self.stack[-1].append(assign_target.id)
        elif isinstance(assign_target, ast.Tuple):
            for element in assign_target.elts:
                self._visit_assign_target(element, node)
        elif isinstance(assign_target, ast.Attribute):
            pass
        elif isinstance(assign_target, ast.Subscript):
            pass
        elif isinstance(assign_target, ast.List):
            for element in assign_target.elts:
                self._visit_assign_target(element, node)
        elif isinstance(assign_target, (ast.Dict, ast.Set)):
            pass
        elif isinstance(assign_target, ast.Starred):
            # Todo: add starred checks
            pass
        else:
            pass

    def visit_Return(self, node: ast.Return) -> Any:
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> Any:
        # Todo: merge if/else and try-except clause checks
        track: Set[str] = set()
        self.tracking_stack.append(track)

        first_try = True
        has_else = False

        while True:
            self.stack.append(Frame())
            self.generic_visit(node.test)  # type: ignore
            for expr in node.body:
                self.visit(expr)  # type: ignore

            hit_return = False
            for expr in node.body:
                if isinstance(expr, (ast.Return, ast.Raise)):
                    hit_return = True
                    break
            if not hit_return:
                self._track(track, first_try)

            self.stack.pop()

            if node.orelse:
                if isinstance(node.orelse[0], ast.If):
                    node = node.orelse[0]
                else:
                    self.stack.append(Frame())
                    for expr in node.orelse:
                        self.visit(expr)  # type: ignore

                    hit_return = False
                    for expr in node.orelse:
                        if isinstance(expr, (ast.Return, ast.Raise)):
                            hit_return = True
                            break
                    if not hit_return:
                        self._track(track, False)

                    self.stack.pop()
                    has_else = True
                    break
            else:
                break
            first_try = False

        if has_else:
            for variable in track:
                self.stack[-1].append(variable)

        self.tracking_stack.pop()

    def visit_Try(self, node: ast.Try) -> Any:
        # Todo: add values from the lower level to the track
        first_try = True
        track: Set[str] = set()

        self.stack.append(Frame())
        for expr in node.body:
            self.visit(expr)  # type: ignore
        self._track(track, first_try)
        self.stack.pop()
        first_try = False

        for handler in node.handlers:
            self.stack.append(Frame())
            if handler.name is not None:
                self.stack[-1].append(handler.name)
            # Todo: redundant check - bad control flow.
            hit_return = False
            for expr in handler.body:
                if isinstance(expr, (ast.Return, ast.Raise)):
                    hit_return = True
                    break
            self.visit(handler)  # type: ignore
            if not hit_return:
                self._track(track, first_try)
            self.stack.pop()

        if node.orelse:
            self.stack.append(Frame())
            hit_return = False
            for expr in node.orelse:
                self.visit(expr)  # type: ignore
                if isinstance(expr, (ast.Return, ast.Raise)):
                    hit_return = True
            if not hit_return:
                self._track(track, first_try)
            self.stack.pop()

        for variable in track:
            self.stack[-1].append(variable)

        if node.finalbody:
            for expr in node.finalbody:
                self.visit(expr)  # type: ignore

    def _track(self, track, first_try):
        if first_try:
            for variable in self.stack[-1]:
                track.add(variable)
        else:
            frame_set = set(self.stack[-1])
            to_remove = []
            for frame in track:
                if frame not in frame_set:
                    to_remove.append(frame)
            for frame in to_remove:
                track.remove(frame)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        # Todo: track kwargs, *args and **kwargs
        self.stack[-1].append(node.name)
        try:
            self.stack.append(Frame())
            for arg in node.args.args:
                self.stack[-1].append(arg.arg)
            if node.args.vararg is not None:
                self.stack[-1].append(node.args.vararg.arg)
            if node.args.kwarg is not None:
                self.stack[-1].append(node.args.kwarg.arg)
            if node.args.kwonlyargs is not None:
                self.stack[-1].extend([arg.arg for arg in node.args.kwonlyargs])

            self.generic_visit(node)
        finally:
            self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        # Todo: It seems like I have to add entire async support,
        #  i.e., async for, async with, ...
        self.stack[-1].append(node.name)
        try:
            self.stack.append(Frame())
            for arg in node.args.args:
                self.stack[-1].append(arg.arg)
            if node.args.vararg is not None:
                self.stack[-1].append(node.args.vararg.arg)
            if node.args.kwarg is not None:
                self.stack[-1].append(node.args.kwarg.arg)
            if node.args.kwonlyargs is not None:
                self.stack[-1].extend([arg.arg for arg in node.args.kwonlyargs])

            self.generic_visit(node)
        finally:
            self.stack.pop()

    def visit_For(self, node: ast.For) -> Any:
        frame = Frame()
        self.stack.append(frame)
        try:
            # frame.append(node.target.id)  # type: ignore
            self._visit_assign_target(node.target)
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)
        except AttributeError:
            print("Can't check For", node.lineno, node.col_offset)
        finally:
            self.stack.pop()

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)
        self.generic_visit(node)

    def _visit_import(self, node: Union[ast.Import, ast.ImportFrom]):
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
        self._visit_import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        self._visit_import(node)

    def visit_Module(self, node: ast.Module) -> Any:
        frame = Frame()
        self.stack.append(frame)
        self._visit_top_level(node)  # Needed to detect top-level module definitions
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

    def _visit_top_level(self, node):
        # Todo: it's definitely not enough to properly list all the fns,
        #  but just works for most cases
        for expr in node.body:
            if isinstance(expr, (ast.FunctionDef, ast.ClassDef)):
                self.stack[-1].append(expr.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        # Todo: add metaclass/superclass/etc analysis.
        self.stack[-1].append(node.name)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)  # type: ignore

    def visit_Name(self, node: ast.Name) -> Any:
        self._visit_names(node)

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        self._visit_names(node)

    def _visit_names(self, node: Union[ast.Name, ast.Tuple]):
        if isinstance(node, ast.Name):
            if hasattr(node, 'id') and not (
                    node.id in self.default_names or self._check_stack(node.id)):
                self.errors.append(
                    Flake8ASTErrorInfo(
                        node.lineno,
                        node.col_offset,
                        self.msg % str(node.id),
                        type(node)
                    )
                )
        elif isinstance(node, ast.Tuple):
            for element in node.elts:
                self._visit_names(element)  # type: ignore

    def visit_Call(self, node: ast.Call) -> Any:
        if hasattr(node, 'id') and not (
                node.id in self.default_names  # type: ignore
                or self._check_stack(node.id)):  # type: ignore
            self.errors.append(
                Flake8ASTErrorInfo(
                    node.lineno,
                    node.col_offset,
                    self.msg % str(node.id),  # type: ignore
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

    def visit_ListComp(self, node: ast.ListComp) -> Any:
        self.stack.append(Frame())
        for generator in node.generators:
            self._visit_assign_target(generator.target)
        self._visit_names(node.elt)  # type: ignore
        self.stack.pop()

    def visit_DictComp(self, node: ast.DictComp) -> Any:
        self.stack.append(Frame())
        for generator in node.generators:
            self._visit_assign_target(generator.target)
        # Todo: what's the problem?
        self._visit_names(node.key)  # type: ignore
        self._visit_names(node.value)  # type: ignore
        self.stack.pop()

    def visit_SetComp(self, node: ast.SetComp) -> Any:
        self.stack.append(Frame())
        for generator in node.generators:
            self._visit_assign_target(generator.target)
        self._visit_names(node.elt)  # type: ignore
        self.stack.pop()

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        self.stack.append(Frame())
        for generator in node.generators:
            self._visit_assign_target(generator.target)
        self._visit_names(node.elt)  # type: ignore
        self.stack.pop()

    def visit_With(self, node: ast.With) -> Any:
        self.stack.append(Frame())
        for withitem in node.items:
            if isinstance(withitem, ast.withitem) and withitem.optional_vars is not None:
                self._visit_assign_target(withitem.optional_vars)
        # Frame for variables defined within 'with' scope.
        self.stack.append(Frame())
        for expr in node.body:
            self.visit(expr)  # type: ignore
        # Pop variables to save them in the higher-level frame
        defined_within_with = self.stack.pop()
        self.stack.pop()
        for val in defined_within_with:
            self.stack[-1].append(val)

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        try:
            self.stack.append(Frame())
            for arg in node.args.args:
                self.stack[-1].append(arg.arg)
            if node.args.vararg is not None:
                self.stack[-1].append(node.args.vararg.arg)
            if node.args.kwarg is not None:
                self.stack[-1].append(node.args.kwarg.arg)
            self.visit(node.body)  # type: ignore
        finally:
            self.stack.pop()

    @property
    def msg(self):
        return "F823 variable '%s' referenced_before_assignment"


class Flake8ASTErrorInfo(NamedTuple):
    line_number: int
    offset: int
    msg: str
    cls: type  # unused as for now


class ReferencedBeforeAssignmentASTPlugin:
    name = 'flake_rba'
    version = '0.0.0'
    _code = 'F823'

    def __init__(self, tree: ast.AST):
        self._tree = tree

    def run(self) -> Iterator[Flake8ASTErrorInfo]:
        visitor = ReferencedBeforeAssignmentNodeVisitor()
        visitor.visit(self._tree)

        for error in visitor.errors:
            yield error
