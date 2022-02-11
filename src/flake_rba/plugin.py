import ast
from typing import NamedTuple, Iterator, List, Any, Union


class Frame(list):  # type: ignore
    pass


class ReferencedBeforeAssignmentNodeVisitor(ast.NodeVisitor):
    # Assuming here that we always check a source code in files, and __file__ is defined.
    default_names = list(__builtins__.keys()) + ['__file__', '__builtins__']  # type: ignore

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
        self._visit_assign_target(assign_target)

    def visit_Assign(self, node: ast.Assign) -> Any:
        # Todo: check multiple targets
        self._visit_values(node.value)
        for assign_target in node.targets:
            self._visit_assign_target(assign_target)

    def _visit_values(self, value_target):
        if isinstance(value_target, list):
            for sub_node in value_target:
                self.visit(sub_node)
        else:
            self.visit(value_target)

    def _visit_assign_target(self, assign_target):
        # Todo: properly check these types below
        # Todo: add assignSub/assignAdd etc. operations
        if isinstance(assign_target, ast.Name):
            self.stack[-1].append(assign_target.id)
        elif isinstance(assign_target, ast.Tuple):
            for element in assign_target.elts:
                self._visit_assign_target(element)
        elif isinstance(assign_target, ast.Attribute):
            pass
        elif isinstance(assign_target, ast.Subscript):
            pass
        elif isinstance(assign_target, ast.List):
            for element in assign_target.elts:
                self._visit_assign_target(element)
        elif isinstance(assign_target, (ast.Dict, ast.Set)):
            pass
        elif isinstance(assign_target, ast.Starred):
            pass
        else:
            pass

    def visit_Return(self, node: ast.Return) -> Any:
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> Any:
        # Todo: merge if/else and try-except clause checks
        self._visit_if_helper(node)

    def _visit_if_helper(self, node: ast.If) -> Any:
        self.stack.append(Frame())
        self.visit(node.test)  # type: ignore

        abort_if_branch = False
        dead_branch = False
        for expr in node.body:
            if isinstance(expr, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                abort_if_branch = True
                self.visit(expr)  # type: ignore
                break
            if isinstance(expr, ast.If):
                dead_branch = self._visit_if_helper(expr)
            else:
                self.visit(expr)  # type: ignore
            if dead_branch:
                abort_if_branch = True
                break

        frame_state = {name for name in self.stack[-1]}
        self.stack[-1].clear()

        abort_else_branch = False
        dead_branch = False
        for expr in node.orelse:
            if isinstance(expr, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                self.visit(expr)  # type: ignore
                abort_else_branch = True
                break
            if isinstance(expr, ast.If):
                dead_branch = self._visit_if_helper(expr)
            else:
                self.visit(expr)  # type: ignore
            if dead_branch:
                abort_else_branch = True
                break

        orelse_frame_state = {name for name in self.stack[-1]}
        self.stack[-1].clear()

        dead_end_branch = False
        if not abort_else_branch and not abort_if_branch:
            intersection = frame_state.intersection(orelse_frame_state)
        elif abort_if_branch and not abort_else_branch:
            intersection = orelse_frame_state
        elif not abort_if_branch and abort_else_branch:
            intersection = frame_state
        else:
            intersection = set()
            dead_end_branch = True

        self.stack.pop()
        for name in intersection:
            self.stack[-1].append(name)
        return dead_end_branch

    def visit_Try(self, node: ast.Try) -> Any:
        self._visit_try_helper(node)

    def _visit_try_helper(self, node: ast.Try) -> Any:
        self.stack.append(Frame())

        scopes = []
        abort_try_branch = False
        dead_end = False
        for expr in node.body:
            if isinstance(expr, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                abort_try_branch = True
                self.visit(expr)  # type: ignore
                break
            if isinstance(expr, ast.Try):
                dead_end = self._visit_try_helper(expr)  # type: ignore
            if isinstance(expr, ast.If):
                dead_end = self._visit_if_helper(expr)  # type: ignore
            else:
                self.visit(expr)  # type: ignore

        if not abort_try_branch and not dead_end:
            frame_state = {name for name in self.stack[-1]}
            scopes.append(frame_state)
        self.stack[-1].clear()

        for handler in node.handlers:
            abort_handler_branch = False

            if handler.name is not None:
                self.stack[-1].append(handler.name)

            dead_end = False
            for expr in handler.body:
                if isinstance(expr, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                    abort_handler_branch = True
                    self.visit(expr)  # type: ignore
                    break
                if isinstance(expr, ast.Try):
                    dead_end = self._visit_try_helper(expr)  # type: ignore
                if isinstance(expr, ast.If):
                    dead_end = self._visit_if_helper(expr)  # type: ignore
                else:
                    self.visit(expr)  # type: ignore

            if not abort_handler_branch and not dead_end:
                handler_frame_state = {name for name in self.stack[-1]}
                scopes.append(handler_frame_state)
            self.stack[-1].clear()

        dead_end = False
        abort_else_branch = False
        for expr in node.orelse:
            if isinstance(expr, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                self.visit(expr)  # type: ignore
                abort_else_branch = True
                break
            if isinstance(expr, ast.Try):
                dead_end = self._visit_try_helper(expr)  # type: ignore
            if isinstance(expr, ast.If):
                dead_end = self._visit_if_helper(expr)
            else:
                self.visit(expr)  # type: ignore

        if not abort_else_branch and node.orelse and not dead_end:
            orelse_frame_state = {name for name in self.stack[-1]}
            scopes.append(orelse_frame_state)
        self.stack[-1].clear()

        for expr in node.finalbody:
            if isinstance(expr, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                self.visit(expr)  # type: ignore
                break
            if isinstance(expr, ast.If):
                self._visit_if_helper(expr)
            else:
                self.visit(expr)  # type: ignore

        self.stack.pop()
        scope_intersection = None
        for scope in scopes:
            if scope_intersection is None:
                scope_intersection = scope
                continue
            scope_intersection = scope_intersection.intersection(scope)  # type: ignore
        if scope_intersection is None:
            scope_intersection = set()

        for name in scope_intersection:
            self.stack[-1].append(name)

        if not scopes:
            return True
        return False

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

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
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
                        self.msg % str(node.id),  # type: ignore
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

    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:
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
