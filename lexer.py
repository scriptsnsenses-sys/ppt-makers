"""DGSL lexer — source text -> token stream.

Tokens are (type, value, line) tuples. Whitespace (including newlines) is
insignificant; // line comments and /* block comments */ are skipped.
"""

from .errors import DGSLError


# Token types
LBRACE, RBRACE = "LBRACE", "RBRACE"
LBRACKET, RBRACKET = "LBRACKET", "RBRACKET"
LPAREN, RPAREN = "LPAREN", "RPAREN"
COMMA, DOT = "COMMA", "DOT"
ASSIGN = "ASSIGN"      # =
EQ, NEQ = "EQ", "NEQ"  # ==  !=
GT, LT, GTE, LTE = "GT", "LT", "GTE", "LTE"
MINUS = "MINUS"
STRING, NUMBER, BOOL, DURATION, IDENT, EOF = (
    "STRING", "NUMBER", "BOOL", "DURATION", "IDENT", "EOF")

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}


def lex(source):
    """Tokenise DGSL source. Raises DGSLError on bad input."""
    tokens = []
    i, n = 0, len(source)
    line = 1

    def err(msg):
        raise DGSLError(f"line {line}: {msg}", line=line)

    while i < n:
        ch = source[i]

        # Whitespace -----------------------------------------------------
        if ch in " \t\r\n":
            if ch == "\n":
                line += 1
            i += 1
            continue

        # Comments ------------------------------------------------------
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            start = line
            i += 2
            closed = False
            while i < n:
                if source[i] == "\n":
                    line += 1
                if source[i] == "*" and i + 1 < n and source[i + 1] == "/":
                    i += 2
                    closed = True
                    break
                i += 1
            if not closed:
                raise DGSLError(f"line {start}: unterminated /* comment */",
                                line=start)
            continue

        # Triple-quoted string (notes) ----------------------------------
        if source.startswith('"""', i):
            start = line
            i += 3
            buf = []
            closed = False
            while i < n:
                if source.startswith('"""', i):
                    i += 3
                    closed = True
                    break
                c = source[i]
                if c == "\n":
                    line += 1
                    buf.append(c)
                    i += 1
                elif c == "\\" and i + 1 < n and source[i + 1] in ('"', "\\"):
                    buf.append(source[i + 1])
                    i += 2
                else:
                    buf.append(c)
                    i += 1
            if not closed:
                raise DGSLError(f"line {start}: unterminated \"\"\" string \"\"\"",
                                line=start)
            tokens.append((STRING, "".join(buf), start))
            continue

        # Single-line string --------------------------------------------
        if ch == '"':
            start = line
            i += 1
            buf = []
            closed = False
            while i < n:
                c = source[i]
                if c == "\n":
                    err("unterminated string "
                        '(strings cannot span lines; use """ for multiline)')
                if c == "\\":
                    if i + 1 >= n:
                        break
                    nxt = source[i + 1]
                    if nxt == "u" and source[i + 2:i + 6].isascii() and \
                            len(source[i + 2:i + 6]) == 4:
                        try:
                            buf.append(chr(int(source[i + 2:i + 6], 16)))
                            i += 6
                            continue
                        except ValueError:
                            pass
                    buf.append(_ESCAPES.get(nxt, nxt))
                    i += 2
                    continue
                if c == '"':
                    i += 1
                    closed = True
                    break
                buf.append(c)
                i += 1
            if not closed:
                raise DGSLError(f"line {start}: unterminated string",
                                line=start)
            tokens.append((STRING, "".join(buf), start))
            continue

        # Numbers (with optional ms/s duration suffix) ------------------
        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            start = line
            j = i
            while j < n and (source[j].isdigit() or source[j] == "."):
                j += 1
            raw = source[i:j]
            if raw.count(".") > 1:
                err(f"bad number {raw!r}")
            value = float(raw) if "." in raw else int(raw)
            if source[j:j + 2] == "ms":
                tokens.append((DURATION, float(value), start))
                i = j + 2
            elif j < n and source[j] == "s" and (j + 1 >= n or not
                  (source[j + 1].isalnum() or source[j + 1] == "_")):
                tokens.append((DURATION, float(value) * 1000.0, start))
                i = j + 1
            else:
                tokens.append((NUMBER, value, start))
                i = j
            continue

        # Identifiers / booleans ----------------------------------------
        if ch.isalpha() or ch == "_":
            start = line
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            if word == "true":
                tokens.append((BOOL, True, start))
            elif word == "false":
                tokens.append((BOOL, False, start))
            else:
                tokens.append((IDENT, word, start))
            i = j
            continue

        # Two-char operators --------------------------------------------
        two = source[i:i + 2]
        if two == "==":
            tokens.append((EQ, "==", line))
            i += 2
            continue
        if two == "!=":
            tokens.append((NEQ, "!=", line))
            i += 2
            continue
        if two == ">=":
            tokens.append((GTE, ">=", line))
            i += 2
            continue
        if two == "<=":
            tokens.append((LTE, "<=", line))
            i += 2
            continue

        # Single chars ---------------------------------------------------
        simple = {
            "{": LBRACE, "}": RBRACE, "[": LBRACKET, "]": RBRACKET,
            "(": LPAREN, ")": RPAREN, ",": COMMA, ".": DOT, "=": ASSIGN,
            ">": GT, "<": LT, "-": MINUS,
        }
        if ch in simple:
            tokens.append((simple[ch], ch, line))
            i += 1
            continue

        err(f"unexpected character {ch!r}")

    tokens.append((EOF, None, line))
    return tokens
