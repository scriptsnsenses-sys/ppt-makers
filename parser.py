"""DGSL parser — token stream -> AST (nested dicts with line numbers).

The grammar is intentionally permissive at this stage: most statements are
`keyword [argument] [{ ... }]` or `key value`. Unknown element names and
misplaced constructs are reported with source lines. Semantic checks
(variables, components, enums) happen in the compiler.
"""

import difflib

from .errors import DGSLError
from .lexer import (ASSIGN, BOOL, COMMA, DOT, DURATION, EOF, EQ,
                    GT, GTE, IDENT, LBRACE, LBRACKET, LPAREN, LT, LTE,
                    MINUS, NEQ, NUMBER, RBRACE, RBRACKET, RPAREN, STRING)

MAX_NODES = 20_000

#: Element kinds the renderer understands (others warn at compile time).
KNOWN_ELEMENTS = {
    "text", "run", "rect", "rounded_rect", "circle", "ellipse",
    "triangle", "diamond", "star", "hexagon", "pentagon", "chevron",
    "arrow", "callout", "image", "video", "audio", "icon", "line",
    "connector", "table", "chart", "group", "button", "border",
    "shadow", "header", "borders", "background", "theme", "animate",
}


class Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.pos = 0
        self.nodes = 0

    # -- cursor helpers -------------------------------------------------
    def peek(self):
        return self.toks[self.pos]

    def peek2(self):
        if self.pos + 1 < len(self.toks):
            return self.toks[self.pos + 1]
        return (EOF, None, self.peek()[2])

    def next(self):
        tok = self.toks[self.pos]
        if tok[0] != EOF:
            self.pos += 1
        return tok

    def expect(self, ttype, what):
        tok = self.peek()
        if tok[0] != ttype:
            raise DGSLError(
                f"expected {what} but found "
                f"{_describe(tok)}", line=tok[2])
        return self.next()

    def at(self, ttype):
        return self.peek()[0] == ttype

    def _node(self, node):
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise DGSLError(
                "presentation is too complex "
                f"(over {MAX_NODES} syntax nodes)")
        return node

    # -- entry point ----------------------------------------------------
    def parse(self):
        tok = self.peek()
        if tok[0] != IDENT or tok[1] != "presentation":
            raise DGSLError(
                "a DGSL file must start with "
                'presentation "Name" { ... }', line=tok[2])
        self.next()
        name_tok = self.expect(STRING, "a presentation name in quotes")
        self.expect(LBRACE, "'{' to open the presentation")
        items = self.parse_items()
        self.expect(RBRACE, "'}' to close the presentation")
        self.expect(EOF, "end of file")
        return self._node({"kind": "presentation", "name": name_tok[1],
                           "line": tok[2], "items": items})

    # -- blocks ---------------------------------------------------------
    def parse_items(self):
        items = []
        while True:
            tok = self.peek()
            if tok[0] in (RBRACE, EOF):
                return items
            items.append(self.parse_statement())

    def parse_statement(self):
        tok = self.peek()
        if tok[0] == LBRACKET:
            return self.parse_row()
        if tok[0] != IDENT:
            raise DGSLError(f"unexpected {_describe(tok)} — "
                            "expected an element or property", line=tok[2])
        kw = tok[1]
        if kw == "let":
            return self.parse_let()
        if kw == "for":
            return self.parse_for()
        if kw == "if":
            return self.parse_if()
        if kw == "import":
            return self.parse_import()
        if kw == "component":
            return self.parse_component()
        if kw == "use":
            return self.parse_use()
        if kw == "parameter":
            return self.parse_parameter()
        if kw == "goto":
            return self.parse_goto()
        if kw == "slide":
            return self.parse_slide()
        if kw == "data":
            return self.parse_data()
        return self.parse_generic()

    def parse_data(self):
        tok = self.next()  # data
        name = self.expect(IDENT, "a name after 'data'")
        self.expect(LBRACE, "'{' to open the data block")
        children = self.parse_items()
        self.expect(RBRACE, "'}' to close the data block")
        return self._node({"kind": "data", "name": name[1],
                           "children": children, "line": tok[2]})

    def parse_slide(self):
        tok = self.next()  # slide
        if self.peek()[0] == STRING:
            name = self.next()[1]
        elif self.peek()[0] == IDENT:
            name = self.next()[1]
        else:
            raise DGSLError("a slide needs a name, e.g. "
                            'slide "Intro" { ... }', line=self.peek()[2])
        self.expect(LBRACE, "'{' to open the slide")
        children = self.parse_items()
        self.expect(RBRACE, "'}' to close the slide")
        return self._node({"kind": "slide", "name": name,
                           "children": children, "line": tok[2]})

    def parse_let(self):
        tok = self.next()  # let
        name = self.expect(IDENT, "a variable name after 'let'")
        self.expect(ASSIGN, "'=' after the variable name")
        value = self.parse_value()
        return self._node({"kind": "let", "name": name[1],
                           "value": value, "line": tok[2]})

    def parse_for(self):
        tok = self.next()  # for
        var = self.expect(IDENT, "a loop variable after 'for'")
        in_tok = self.expect(IDENT, "'in' after the loop variable")
        if in_tok[1] != "in":
            raise DGSLError(f"expected 'in' after loop variable, "
                            f"found {in_tok[1]!r}", line=in_tok[2])
        it = self.parse_value()
        self.expect(LBRACE, "'{' to open the for body")
        body = self.parse_items()
        self.expect(RBRACE, "'}' to close the for body")
        return self._node({"kind": "for", "var": var[1], "iter": it,
                           "body": body, "line": tok[2]})

    def parse_if(self):
        tok = self.next()  # if
        cond = self.parse_condition()
        self.expect(LBRACE, "'{' to open the if body")
        then = self.parse_items()
        self.expect(RBRACE, "'}' to close the if body")
        else_ = []
        if self.at(IDENT) and self.peek()[1] == "else":
            self.next()
            self.expect(LBRACE, "'{' to open the else body")
            else_ = self.parse_items()
            self.expect(RBRACE, "'}' to close the else body")
        return self._node({"kind": "if", "cond": cond, "then": then,
                           "else": else_, "line": tok[2]})

    def parse_import(self):
        tok = self.next()
        path = self.expect(STRING, "a file path after 'import'")
        return self._node({"kind": "import", "path": path[1], "line": tok[2]})

    def parse_component(self):
        tok = self.next()
        name = self.expect(IDENT, "a ComponentName after 'component'")
        if not (name[1][:1].isupper() or "_" in name[1] or name[1][:1].isupper()):
            pass  # convention only; any identifier is accepted
        self.expect(LBRACE, "'{' to open the component")
        body = self.parse_items()
        self.expect(RBRACE, "'}' to close the component")
        params = [i["name"] for i in body if i["kind"] == "parameter"]
        return self._node({"kind": "component", "name": name[1],
                           "params": params, "body": body, "line": tok[2]})

    def parse_use(self):
        tok = self.next()
        name = self.expect(IDENT, "a ComponentName after 'use'")
        args = {}
        if self.at(LBRACE):
            self.next()
            for item in self.parse_items():
                if item["kind"] != "prop":
                    raise DGSLError(
                        f"only parameter assignments are allowed inside "
                        f"use {name[1]} (found {item['kind']})",
                        line=item.get("line", tok[2]))
                args[item["key"]] = item["value"]
            self.expect(RBRACE, "'}' to close the use block")
        return self._node({"kind": "use", "name": name[1], "args": args,
                           "line": tok[2]})

    def parse_parameter(self):
        tok = self.next()
        name = self.expect(IDENT, "a parameter name after 'parameter'")
        return self._node({"kind": "parameter", "name": name[1],
                           "line": tok[2]})

    def parse_goto(self):
        tok = self.next()
        slide_kw = self.expect(IDENT, "'slide' after 'goto'")
        if slide_kw[1] != "slide":
            raise DGSLError(f"expected 'slide' after 'goto', "
                            f"found {slide_kw[1]!r}", line=slide_kw[2])
        target = self.expect(STRING, "a slide name after 'goto slide'")
        return self._node({"kind": "goto", "target": target[1],
                           "line": tok[2]})

    def parse_row(self):
        tok = self.next()  # [
        items = self.parse_array_items()
        self.expect(RBRACKET, "']' to close the row")
        return self._node({"kind": "row", "items": items, "line": tok[2]})

    def parse_generic(self):
        """`keyword [value ...] [{ children }]` or `key value`."""
        key = self.next()
        line = key[2]
        # `run "Some text"` without a block is still a run element.
        if key[1] == "run":
            arg = self.parse_value() if self._is_value_start() else None
            children = []
            if self.at(LBRACE):
                self.next()
                children = self.parse_items()
                self.expect(RBRACE, "'}' to close the run")
            return self._node({"kind": "element", "name": "run",
                               "arg": arg, "children": children,
                               "line": line})
        # background has a two-token prefix form: background image "x" {
        if key[1] == "background" and self.at(IDENT) and \
                self.peek()[1] == "image":
            self.next()
            src = self.expect(STRING, "an image path after 'background image'")
            return self._finish_block(
                "background",
                {"t": "imagebg", "src": src[1], "line": src[2]}, line)
        if self._is_value_start():
            first = self.parse_value()
            # background gradient { / chart bar { / text "x" { / text var {
            if self.at(LBRACE):
                self.next()
                children = self.parse_items()
                self.expect(RBRACE, "'}' to close the block")
                return self._node({"kind": "element", "name": key[1],
                                   "arg": first, "children": children,
                                   "line": line})
            # key value  (property)
            return self._node({"kind": "prop", "key": key[1],
                               "value": first, "line": line})
        if self.at(LBRACE):
            self.next()
            children = self.parse_items()
            self.expect(RBRACE, "'}' to close the block")
            return self._node({"kind": "element", "name": key[1], "arg": None,
                               "children": children, "line": line})
        raise DGSLError(f"'{key[1]}' needs a value or a '{{ ... }}' block",
                        line=line)

    def _finish_block(self, name, arg, line):
        children = []
        if self.at(LBRACE):
            self.next()
            children = self.parse_items()
            self.expect(RBRACE, "'}' to close the block")
        return self._node({"kind": "element", "name": name, "arg": arg,
                           "children": children, "line": line})

    def _is_value_start(self):
        t = self.peek()[0]
        if t in (STRING, NUMBER, DURATION, BOOL, LBRACKET):
            return True
        if t == MINUS and self.peek2()[0] == NUMBER:
            return True
        if t == IDENT and self.peek()[1] not in ("else", "in"):
            return True
        return False

    # -- values ---------------------------------------------------------
    def parse_value(self):
        tok = self.peek()
        if tok[0] == STRING:
            self.next()
            return {"t": "str", "v": tok[1], "line": tok[2]}
        if tok[0] == NUMBER:
            self.next()
            return {"t": "num", "v": tok[1], "line": tok[2]}
        if tok[0] == DURATION:
            self.next()
            return {"t": "dur", "ms": tok[1], "line": tok[2]}
        if tok[0] == BOOL:
            self.next()
            return {"t": "bool", "v": tok[1], "line": tok[2]}
        if tok[0] == MINUS:
            self.next()
            num = self.expect(NUMBER, "a number after '-'")
            v = num[1]
            return {"t": "num", "v": -v, "line": tok[2]}
        if tok[0] == LBRACKET:
            self.next()
            items = self.parse_array_items()
            end = self.expect(RBRACKET, "']' to close the list")
            return {"t": "arr", "items": items, "line": tok[2]}
        if tok[0] == IDENT:
            return self.parse_ref()
        raise DGSLError(f"unexpected {_describe(tok)} — "
                        "expected a value", line=tok[2])

    def parse_array_items(self):
        items = []
        while not self.at(RBRACKET):
            if self.at(EOF):
                raise DGSLError("unterminated list — expected ']'",
                                line=self.peek()[2])
            items.append(self.parse_value())
            if self.at(COMMA):
                self.next()
        return items

    def parse_ref(self):
        tok = self.next()
        node = {"t": "ref", "name": tok[1], "line": tok[2]}
        while True:
            if self.at(DOT):
                self.next()
                attr = self.expect(IDENT, "a name after '.'")
                node = {"t": "dot", "base": node,
                        "attr": attr[1], "line": tok[2]}
            elif self.at(LBRACKET):
                self.next()
                idx = self.expect(NUMBER, "an index inside '[...]'")
                if isinstance(idx[1], float) or idx[1] < 0:
                    raise DGSLError("list indexes must be "
                                    "non-negative integers", line=idx[2])
                self.expect(RBRACKET, "']' after the index")
                node = {"t": "idx", "base": node, "index": int(idx[1]),
                        "line": tok[2]}
            else:
                return node

    # -- conditions -----------------------------------------------------
    def parse_condition(self):
        return self.parse_or()

    def parse_or(self):
        node = self.parse_and()
        while self.at(IDENT) and self.peek()[1] == "or":
            tok = self.next()
            node = {"t": "or", "l": node, "r": self.parse_and(),
                    "line": tok[2]}
        return node

    def parse_and(self):
        node = self.parse_not()
        while self.at(IDENT) and self.peek()[1] == "and":
            tok = self.next()
            node = {"t": "and", "l": node, "r": self.parse_not(),
                    "line": tok[2]}
        return node

    def parse_not(self):
        if self.at(IDENT) and self.peek()[1] == "not":
            tok = self.next()
            return {"t": "not", "of": self.parse_not(), "line": tok[2]}
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_operand()
        tok = self.peek()
        ops = {EQ: "==", NEQ: "!=", GT: ">", LT: "<", GTE: ">=", LTE: "<="}
        if tok[0] in ops:
            self.next()
            return {"t": "cmp", "op": ops[tok[0]], "l": left,
                    "r": self.parse_operand(), "line": tok[2]}
        return left

    def parse_operand(self):
        if self.at(LPAREN):
            self.next()
            node = self.parse_condition()
            self.expect(RPAREN, "')' to close the condition")
            return node
        return self.parse_value()


def _describe(tok):
    t, v, _ = tok
    if t == IDENT:
        return f"keyword {v!r}"
    if t == STRING:
        return f"string {v!r}"
    if t == EOF:
        return "end of file"
    return f"{v!r}"


def suggest_element(name):
    matches = difflib.get_close_matches(name, sorted(KNOWN_ELEMENTS),
                                        n=1, cutoff=0.6)
    return matches[0] if matches else None
