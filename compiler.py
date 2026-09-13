"""DGSL compiler — AST -> resolved IR (plain dicts).

Resolves variables (let), themes, components (component/use), data tables,
for loops, and if conditions. Everything else passes through as
declarative data for the renderer. No code is ever executed.
"""

from .errors import DGSLError
from .parser import suggest_element

MAX_SLIDES = 60
MAX_ELEMENTS_PER_SLIDE = 200
MAX_EXPANSIONS = 5_000

#: Presentation-level metadata keys.
META_KEYS = {"title", "author", "subject", "keywords", "language"}

#: Element kinds the renderer draws. Anything else parses fine but is
#: rendered as a labelled placeholder (with a warning) so content never
#: vanishes silently.
RENDERED_KINDS = {
    "text", "rect", "rounded_rect", "circle", "ellipse", "triangle",
    "diamond", "star", "hexagon", "pentagon", "chevron", "arrow",
    "callout", "image", "line", "table", "chart", "group", "button",
}

PLACEHOLDER_KINDS = {"video", "audio", "icon", "connector"}


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}

    def child(self):
        return Scope(self)

    def lookup(self, name):
        scope = self
        while scope is not None:
            if name in scope.vars:
                return scope.vars[name]
            scope = scope.parent
        return None


class Compiler:
    def __init__(self):
        self.warnings = []
        self._warned = set()
        self.themes = {}
        self.components = {}
        self.data = {}
        self.expansions = 0
        self._theme_defaults = {}

    def warn(self, message, line=None):
        text = f"line {line}: {message}" if line is not None else message
        if text not in self._warned:
            self._warned.add(text)
            self.warnings.append(text)

    @staticmethod
    def _attach(node, scope):
        """Bind the resolution scope to an expanded AST node."""
        import copy
        node = copy.deepcopy(node)
        node["__scope"] = scope
        return node

    # -- values -------------------------------------------------------
    def eval_value(self, node, scope):
        t = node["t"]
        if t == "str":
            return node["v"]
        if t == "num":
            return node["v"]
        if t == "bool":
            return node["v"]
        if t == "dur":
            return node["ms"]
        if t == "arr":
            return [self.eval_value(i, scope) for i in node["items"]]
        if t == "neg":
            return -self.eval_value(node["of"], scope)
        if t == "ref":
            found = scope.lookup(node["name"]) if scope else None
            if found is not None:
                return found
            # Bare identifiers double as enum literals (center, cover…).
            return node["name"]
        if t == "dot":
            base = self.eval_value(node["base"], scope)
            attr = node["attr"]
            if isinstance(base, dict) and attr in base:
                return base[attr]
            if isinstance(base, (list, tuple)):
                if attr == "name" and len(base) > 0:
                    return base[0]
                if attr == "value" and len(base) > 1:
                    return base[1]
                raise DGSLError(
                    f"cannot read .{attr} from a list "
                    f"(use [0], [1], … or .name/.value for pairs)",
                    line=node["line"])
            raise DGSLError(f"cannot read .{attr} from "
                            f"{_typename(base)}", line=node["line"])
        if t == "idx":
            base = self.eval_value(node["base"], scope)
            if not isinstance(base, (list, tuple)):
                raise DGSLError("can only index into a list",
                                line=node["line"])
            if node["index"] >= len(base):
                raise DGSLError(
                    f"index [{node['index']}] is out of range "
                    f"(list has {len(base)} items)", line=node["line"])
            return base[node["index"]]
        raise DGSLError(f"unsupported value", line=node.get("line"))

    def eval_cond(self, node, scope):
        t = node["t"]
        if t == "or":
            return self.truthy(self.eval_cond(node["l"], scope)) or \
                self.truthy(self.eval_cond(node["r"], scope))
        if t == "and":
            return self.truthy(self.eval_cond(node["l"], scope)) and \
                self.truthy(self.eval_cond(node["r"], scope))
        if t == "not":
            return not self.truthy(self.eval_cond(node["of"], scope))
        if t == "cmp":
            left = self.eval_operand(node["l"], scope)
            right = self.eval_operand(node["r"], scope)
            return _compare(node["op"], left, right, node["line"])
        return self.truthy(self.eval_operand(node, scope))

    def eval_operand(self, node, scope):
        if node["t"] in ("or", "and", "not", "cmp"):
            return self.eval_cond(node, scope)
        return self.eval_value(node, scope)

    @staticmethod
    def truthy(value):
        if value is None or value is False:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, (str, list, tuple, dict)):
            return len(value) > 0
        return True

    # -- top level ----------------------------------------------------
    def compile(self, program):
        scope = Scope()
        title = program["name"]
        meta = {}
        slides = []
        for item in program["items"]:
            kind = item["kind"]
            if kind == "let":
                scope.vars[item["name"]] = self.eval_value(item["value"],
                                                           scope)
            elif kind == "element" and item["name"] == "theme":
                self._theme_statement(item, scope, meta)
            elif kind == "component":
                self.components[item["name"]] = item
            elif kind == "data":
                self.data[item["name"]] = self._eval_data(item, scope)
            elif kind == "slide":
                slides.append(self.compile_slide(item, scope))
            elif kind == "for":
                for sub in self._expand_body(item, scope, want="slides"):
                    slides.append(self.compile_slide(sub, scope))
            elif kind == "if":
                branch = item["then"] if self.eval_cond(
                    item["cond"], scope) else item["else"]
                for sub in self._expand_statements(branch, scope,
                                                   want="slides"):
                    slides.append(self.compile_slide(sub, scope))
            elif kind == "import":
                raise DGSLError(
                    f"import of {item['path']!r} is not supported in the "
                    f"web editor — paste the contents into this file instead",
                    line=item["line"])
            elif kind == "prop":
                if item["key"] in META_KEYS:
                    meta[item["key"]] = self.eval_value(item["value"], scope)
                elif item["key"] == "theme":
                    # theme "Name" — activate defaults for all slides.
                    tname = self._coerce_text(
                        self.eval_value(item["value"], scope), item)
                    self._theme_defaults.update(
                        self.apply_theme_use(tname, scope, item["line"]))
                else:
                    self.warn(f"unknown presentation property "
                              f"'{item['key']}' ignored", item["line"])
            elif kind == "use":
                raise DGSLError("'use' must appear inside a slide, not at "
                                "the top level", line=item["line"])
            elif kind == "element":
                raise DGSLError(
                    f"'{item['name']}' must appear inside a slide, not at "
                    f"the top level", line=item["line"])
            else:
                raise DGSLError(f"unexpected {kind} here", line=item["line"])

        if not slides:
            raise DGSLError("the presentation needs at least one slide")
        if len(slides) > MAX_SLIDES:
            raise DGSLError(f"too many slides ({len(slides)}, max "
                            f"{MAX_SLIDES})")
        if "title" not in meta:
            meta["title"] = title
        return {"title": title, "meta": meta, "slides": slides,
                "warnings": self.warnings}

    # -- themes -------------------------------------------------------
    def _theme_statement(self, node, scope, meta):
        arg = node.get("arg")
        if arg is not None:
            # theme "Name" { ... } — a definition.
            name = self._arg_string(arg, scope, what="theme name")
            props = {}
            for child in node["children"]:
                if child["kind"] == "prop":
                    props[child["key"]] = self.eval_value(child["value"],
                                                          scope)
                else:
                    self.warn(f"ignored inside theme {name!r}: "
                              f"{child['kind']}", child.get("line"))
            self.themes[name] = props
            return
        # bare `theme "Name"` — not valid at presentation level without
        # being inside the presentation… handled by generic path below.
        self.warn("empty theme block ignored", node["line"])

    def apply_theme_use(self, name, scope, line):
        theme = self.themes.get(name)
        if theme is None:
            known = ", ".join(sorted(self.themes)) or "none defined yet"
            raise DGSLError(f"unknown theme {name!r} "
                            f"(defined: {known})", line=line)
        return dict(theme)

    # -- data ---------------------------------------------------------
    def _eval_data(self, node, scope):
        rows = []
        for child in node["children"]:
            if child["kind"] == "row":
                rows.append([self.eval_value(i, scope)
                             for i in child["items"]])
            elif child["kind"] == "prop" and child["key"] == "row" and \
                    isinstance(child["value"], dict) and \
                    child["value"]["t"] == "arr":
                # Lenient: row ["a", 1] also accepted inside data.
                rows.append([self.eval_value(i, scope)
                             for i in child["value"]["items"]])
            else:
                raise DGSLError(f"only rows like [\"a\", 1] are allowed "
                                f"inside data (found {child['kind']})",
                                line=child.get("line"))
        return rows

    # -- expansion (for / if / use) -----------------------------------
    def _expand_statements(self, items, scope, want):
        """Expand for/if/use items; yield slide- or element-AST nodes."""
        out = []
        for item in items:
            kind = item["kind"]
            if kind == "let":
                scope.vars[item["name"]] = self.eval_value(item["value"],
                                                           scope)
            elif kind == "for":
                out.extend(self._expand_body(item, scope, want))
            elif kind == "if":
                branch = item["then"] if self.eval_cond(
                    item["cond"], scope) else item["else"]
                out.extend(self._expand_statements(branch, scope, want))
            elif kind == "use":
                if want != "elements":
                    raise DGSLError("'use' must appear inside a slide",
                                    line=item["line"])
                out.extend(self._instantiate(item, scope))
            else:
                out.append(item)
        return out

    def _expand_body(self, node, scope, want):
        self.expansions += 1
        if self.expansions > MAX_EXPANSIONS:
            raise DGSLError("too many generated blocks — check for loops "
                            "over large data", line=node["line"])
        it = node["iter"]
        if it["t"] == "ref" and it["name"] in self.data:
            seq = self.data[it["name"]]
        else:
            seq = self.eval_value(it, scope)
        if isinstance(seq, str) or not isinstance(seq, (list, tuple)):
            raise DGSLError("for loops need a list (data table, variable, "
                            "or [ ... ])", line=node["line"])
        out = []
        for row in seq:
            child = scope.child()
            child.vars[node["var"]] = row
            for item in self._expand_statements(node["body"], child, want):
                # Each iteration gets its own copy bound to its own scope
                # (nested expansions keep their deeper scope).
                if "__scope" not in item:
                    item = self._attach(item, child)
                out.append(item)
        return out

    def _instantiate(self, node, scope):
        comp = self.components.get(node["name"])
        if comp is None:
            known = ", ".join(sorted(self.components)) or "none defined yet"
            raise DGSLError(f"unknown component {node['name']!r} "
                            f"(defined: {known})", line=node["line"])
        missing = [p for p in comp["params"] if p not in node["args"]]
        if missing:
            raise DGSLError(f"use {node['name']} is missing parameters: "
                            f"{', '.join(missing)}", line=node["line"])
        child = scope.child()
        for pname in comp["params"]:
            child.vars[pname] = self.eval_value(node["args"][pname], scope)
        out = []
        for item in comp["body"]:
            if item["kind"] == "parameter":
                continue
            if item["kind"] in ("for", "if"):
                expanded = self._expand_statements([item], child,
                                                   want="elements")
            elif item["kind"] == "use":
                expanded = self._instantiate(item, child)
            else:
                expanded = [item]
            for sub in expanded:
                # Bind the parameter scope (nested expansions keep theirs).
                if "__scope" not in sub:
                    sub = self._attach(sub, child)
                out.append(sub)
        return out

    # -- slides -------------------------------------------------------
    def compile_slide(self, node, scope):
        if node["kind"] != "slide":
            raise DGSLError(f"expected a slide here, found "
                            f"{node['kind']}", line=node.get("line"))
        # Slides generated by for/if carry their own scope.
        scope = node.get("__scope", scope)
        local = scope.child()
        background = None
        transition = None
        notes = ""
        elements = []
        theme_defaults = dict(self._theme_defaults)
        raw_items = self._expand_statements(node.get("children", []),
                                            local, want="elements")
        for item in raw_items:
            kind = item["kind"]
            # Items from for/use carry the scope their names resolve in.
            eff = item.get("__scope", local)
            if kind == "prop":
                key = item["key"]
                if key == "background":
                    background = {"kind": "solid",
                                  "color": self.eval_value(item["value"],
                                                           eff)}
                elif key == "notes":
                    notes = self._coerce_text(
                        self.eval_value(item["value"], eff), item)
                elif key == "transition":
                    transition = self.eval_value(item["value"], eff)
                    self.warn("slide transitions are parsed but not "
                              "rendered in DGSL v1", item["line"])
                elif key == "theme":
                    tname = self._coerce_text(
                        self.eval_value(item["value"], eff), item)
                    theme_defaults.update(
                        self.apply_theme_use(tname, eff, item["line"]))
                else:
                    self.warn(f"unknown slide property '{key}' ignored",
                              item["line"])
            elif kind == "element" and item["name"] == "background":
                background = self._compile_background(item, eff)
            elif kind == "element" and item["name"] == "theme":
                if item["children"]:
                    self._theme_statement(item, eff, None)
                else:
                    tname = self._arg_string(item.get("arg"), eff,
                                             what="theme name")
                    theme_defaults.update(
                        self.apply_theme_use(tname, eff, item["line"]))
            elif kind == "element" and item["name"] == "animate":
                target = self._arg_string(item.get("arg"), eff,
                                          what="animation target")
                self.warn(f"animation on {target!r} is parsed but not "
                          f"rendered in DGSL v1", item["line"])
            elif kind == "element":
                elements.append(self.compile_element(
                    item, eff, theme_defaults))
            elif kind == "slide":
                raise DGSLError("slides cannot be nested inside slides",
                                line=item["line"])
            else:
                raise DGSLError(f"unexpected {kind} inside a slide",
                                line=item.get("line"))
        if len(elements) > MAX_ELEMENTS_PER_SLIDE:
            raise DGSLError(
                f"slide {node.get('name', '?')!r} has too many elements "
                f"({len(elements)}, max {MAX_ELEMENTS_PER_SLIDE})",
                line=node.get("line"))
        return {"name": node.get("name", ""), "background": background,
                "transition": transition, "notes": notes,
                "elements": elements, "line": node.get("line")}

    # -- backgrounds --------------------------------------------------
    def _compile_background(self, node, scope):
        arg = node.get("arg")
        props = self._props_dict(node.get("children", []), scope,
                                 allow_blocks=False)
        if arg is None:
            raise DGSLError("background needs a color, gradient, or image",
                            line=node["line"])
        if arg["t"] == "str":
            return {"kind": "solid", "color": arg["v"]}
        if arg["t"] == "ref" and arg["name"] == "gradient":
            frm = props.get("from")
            to = props.get("to")
            if not isinstance(frm, str) or not isinstance(to, str):
                raise DGSLError("gradient needs from \"...\" and to \"...\" "
                                "colors", line=node["line"])
            angle = props.get("angle", 90)
            if not isinstance(angle, (int, float)):
                raise DGSLError("gradient angle must be a number",
                                line=node["line"])
            return {"kind": "gradient", "from": frm, "to": to,
                    "angle": float(angle)}
        if arg["t"] == "imagebg":
            fit = props.get("fit", "cover")
            if fit not in ("cover", "contain"):
                raise DGSLError('background fit must be cover or contain',
                                line=node["line"])
            return {"kind": "image", "src": arg["src"], "fit": fit}
        if arg["t"] == "ref":
            resolved = scope.lookup(arg["name"])
            if isinstance(resolved, str):
                return {"kind": "solid", "color": resolved}
        raise DGSLError("background must be a color, gradient { ... }, or "
                        'image "..." { ... }', line=node["line"])

    # -- elements -----------------------------------------------------
    def compile_element(self, node, scope, theme_defaults):
        kind = node["name"]
        line = node.get("line")
        if kind not in RENDERED_KINDS and kind not in PLACEHOLDER_KINDS:
            hint = suggest_element(kind)
            msg = f"unknown element '{kind}'"
            if hint:
                msg += f" — did you mean '{hint}'?"
            raise DGSLError(msg, line=line)
        if kind in PLACEHOLDER_KINDS:
            self.warn(f"'{kind}' is parsed but rendered as a placeholder "
                      f"in DGSL v1", line)

        el = {"kind": kind, "text": None, "props": {}, "runs": [],
              "border": None, "shadow": None, "header": None,
              "borders_cfg": None, "columns": [], "rows": [],
              "labels": [], "values": [], "chart_type": None,
              "children": [], "id": None, "link": None, "alt": None,
              "language": None, "target": None, "line": line}

        # Argument: default text / source path / chart type / group label.
        arg = node.get("arg")
        if arg is not None:
            if kind in ("text", "run", "button"):
                el["text"] = self._arg_text(arg, scope, kind, line)
            elif kind in ("image", "video", "audio", "icon"):
                el["src"] = self._arg_string(arg, scope,
                                             what=f"{kind} source")
            elif kind == "chart":
                ctype = self._arg_string(arg, scope, what="chart type")
                if ctype not in ("bar", "column", "line", "area", "pie",
                                 "doughnut"):
                    raise DGSLError(
                        f"unsupported chart type {ctype!r} (supported: bar, "
                        f"column, line, area, pie, doughnut)", line=line)
                el["chart_type"] = ctype
            elif kind == "group":
                el["label"] = self._arg_string(arg, scope,
                                               what="group label")
            elif kind == "animate":
                pass  # handled by caller
            else:
                self.warn(f"ignored argument on '{kind}'", line)

        # for / if / use can appear anywhere elements can (slide or group).
        children = self._expand_statements(node.get("children", []), scope,
                                           want="elements")
        for child in children:
            ckind = child["kind"]
            cscope = child.get("__scope", scope)
            if ckind == "prop":
                self._apply_prop(el, child, cscope, theme_defaults)
            elif ckind == "element" and child["name"] == "run":
                if kind != "text":
                    raise DGSLError("'run' blocks are only allowed inside "
                                    "text", line=child["line"])
                el["runs"].append(self._compile_run(child, cscope,
                                                    theme_defaults))
            elif ckind == "element" and child["name"] == "border":
                el["border"] = self._sub_block(child, cscope,
                                               {"color", "width", "radius"})
            elif ckind == "element" and child["name"] == "shadow":
                el["shadow"] = self._sub_block(child, cscope,
                                               {"x", "y", "blur", "opacity"})
                self.warn("shadows are parsed but rendered flat in DGSL "
                          "v1", child["line"])
            elif ckind == "element" and child["name"] == "header":
                el["header"] = self._sub_block(
                    child, cscope, {"fill", "color", "bold", "size", "font"})
            elif ckind == "element" and child["name"] == "borders":
                el["borders_cfg"] = self._sub_block(child, cscope,
                                                    {"color", "width"})
            elif ckind == "element" and child["name"] == "goto":
                target = self._arg_string(child.get("arg"), cscope,
                                          what="goto target")
                el["target"] = target
            elif ckind == "goto":
                el["target"] = child["target"]
            elif ckind == "element" and kind == "group":
                el["children"].append(self.compile_element(
                    child, cscope, theme_defaults))
            else:
                self.warn(f"ignored inside '{kind}': {ckind}",
                          child.get("line"))

        # Theme defaults fill gaps (explicit props always win).
        if theme_defaults:
            if kind == "text":
                el["props"].setdefault("font", theme_defaults.get("font"))
                el["props"].setdefault("color",
                                       theme_defaults.get("foreground"))
            for run in el["runs"]:
                run.setdefault("font", theme_defaults.get("font"))
                run.setdefault("color", theme_defaults.get("foreground"))
        el["props"] = {k: v for k, v in el["props"].items()
                       if v is not None}
        return el

    def _apply_prop(self, el, child, scope, theme_defaults):
        key = child["key"]
        value = self.eval_value(child["value"], scope)
        line = child["line"]
        if key in ("columns", "labels", "values"):
            if not isinstance(value, list):
                raise DGSLError(f"'{key}' needs a list like [...]",
                                line=line)
            el[key] = value
        elif key == "row":
            if not isinstance(value, list):
                raise DGSLError("'row' needs a list like [...]", line=line)
            el["rows"].append(value)
        elif key == "id":
            el["id"] = self._coerce_text(value, child)
        elif key == "link":
            el["link"] = self._coerce_text(value, child)
        elif key == "alt":
            el["alt"] = self._coerce_text(value, child)
        elif key == "language":
            el["language"] = self._coerce_text(value, child)
        else:
            el["props"][key] = value

    def _compile_run(self, node, scope, theme_defaults):
        run = {}
        arg = node.get("arg")
        if arg is not None:
            run["text"] = self._arg_text(arg, scope, "run", node["line"])
        else:
            run["text"] = ""
        for child in node.get("children", []):
            if child["kind"] != "prop":
                raise DGSLError(f"only formatting properties are allowed "
                                f"inside run (found {child['kind']})",
                                line=child.get("line"))
            run[child["key"]] = self.eval_value(child["value"], scope)
        # Runs inherit the parent text formatting at render time; only
        # keep what was stated.
        return run

    def _sub_block(self, node, scope, allowed):
        out = {}
        for child in node.get("children", []):
            if child["kind"] != "prop":
                raise DGSLError(f"only properties are allowed inside "
                                f"{node['name']} (found {child['kind']})",
                                line=child.get("line"))
            if child["key"] not in allowed:
                self.warn(f"unknown '{node['name']}' property "
                          f"'{child['key']}' ignored", child["line"])
                continue
            out[child["key"]] = self.eval_value(child["value"], scope)
        return out

    def _props_dict(self, children, scope, allow_blocks=True):
        out = {}
        for child in children:
            if child["kind"] == "prop":
                out[child["key"]] = self.eval_value(child["value"], scope)
            elif allow_blocks:
                out[child["name"]] = True
            else:
                self.warn(f"ignored '{child['kind']}' here",
                          child.get("line"))
        return out

    # -- small helpers ------------------------------------------------
    def _arg_string(self, arg, scope, what="value"):
        if arg is None:
            raise DGSLError(f"missing {what}", line=None)
        if arg["t"] == "str":
            return arg["v"]
        if arg["t"] == "ref":
            found = scope.lookup(arg["name"]) if scope else None
            if isinstance(found, str):
                return found
            return arg["name"]
        raise DGSLError(f"{what} must be a quoted string",
                        line=arg.get("line"))

    def _arg_text(self, arg, scope, kind, line):
        if arg is None:
            return ""
        if arg["t"] == "str":
            return arg["v"]
        if arg["t"] in ("ref", "dot", "idx"):
            value = self.eval_value(arg, scope)
            if isinstance(value, str):
                return value
            if arg["t"] == "ref":
                # Component parameter used as content, e.g. `text title`.
                raise DGSLError(
                    f"unknown name '{arg['name']}' — define it with let, "
                    f"a component parameter, or quote it as text",
                    line=arg.get("line", line))
            raise DGSLError(f"{kind} text must be a string",
                            line=arg.get("line", line))
        raise DGSLError(f"{kind} text must be a quoted string",
                        line=arg.get("line", line))

    @staticmethod
    def _coerce_text(value, node):
        if not isinstance(value, str):
            raise DGSLError("this needs a quoted string",
                            line=node.get("line"))
        return value


def _typename(value):
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, (list, tuple)):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return "a value"


def _compare(op, left, right, line):
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    # Ordering comparisons are numbers-only in DGSL v1 (bools excluded:
    # in Python True == 1, which would be surprising here).
    if isinstance(left, bool) or isinstance(right, bool) or \
            not isinstance(left, (int, float)) or \
            not isinstance(right, (int, float)):
        raise DGSLError(f"cannot compare {_typename(left)} with "
                        f"{_typename(right)} using '{op}' "
                        f"(ordering needs two numbers)", line=line)
    try:
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
    except Exception:
        raise DGSLError(f"cannot compare values with '{op}'", line=line)
    raise DGSLError(f"unknown operator '{op}'", line=line)
