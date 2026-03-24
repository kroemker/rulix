from dataclasses import dataclass
from enum import Enum, auto


class TT(Enum):
    """Token types."""
    # Literals
    IDENT   = auto()
    INT     = auto()
    FLOAT   = auto()
    STRING       = auto()
    INTERP_STRING = auto()  # string containing {expr} holes
    # Keywords
    TRUE    = auto()
    FALSE   = auto()
    NULL    = auto()
    RULE    = auto()
    AND     = auto()
    OR      = auto()
    NOT     = auto()
    DISABLE = auto()
    STOP    = auto()
    # Operators
    ARROW   = auto()  # =>
    ASSIGN  = auto()  # =
    EQ      = auto()  # ==
    NEQ     = auto()  # !=
    LT      = auto()  # <
    GT      = auto()  # >
    LTE     = auto()  # <=
    GTE     = auto()  # >=
    PLUS    = auto()  # +
    MINUS   = auto()  # -
    STAR    = auto()  # *
    SLASH   = auto()  # /
    PERCENT = auto()  # %
    # Punctuation
    LPAREN  = auto()  # (
    RPAREN  = auto()  # )
    COMMA   = auto()  # ,
    LBRACE   = auto()  # {
    RBRACE   = auto()  # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COLON    = auto()  # :
    DOT      = auto()  # .
    # Structure
    NEWLINE = auto()
    EOF     = auto()


_KEYWORDS: dict[str, TT] = {
    "true":    TT.TRUE,
    "false":   TT.FALSE,
    "null":    TT.NULL,
    "rule":    TT.RULE,
    "and":     TT.AND,
    "or":      TT.OR,
    "not":     TT.NOT,
    "disable": TT.DISABLE,
    "stop":    TT.STOP,
}

_SINGLE: dict[str, TT] = {
    "=": TT.ASSIGN,
    "<": TT.LT,
    ">": TT.GT,
    "+": TT.PLUS,
    "-": TT.MINUS,
    "*": TT.STAR,
    "/": TT.SLASH,
    "%": TT.PERCENT,
    "(": TT.LPAREN,
    ")": TT.RPAREN,
    ",": TT.COMMA,
    "{": TT.LBRACE,
    "}": TT.RBRACE,
    "[": TT.LBRACKET,
    "]": TT.RBRACKET,
    ":": TT.COLON,
    ".": TT.DOT,
}


class LexError(Exception):
    pass


@dataclass(frozen=True)
class Token:
    type:  TT
    value: object
    line:  int


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1

    while i < len(source):
        c = source[i]

        # Whitespace (not newlines)
        if c in (" ", "\t", "\r"):
            i += 1
            continue

        # Comments
        if c == "#":
            while i < len(source) and source[i] != "\n":
                i += 1
            continue

        # Newlines — collapse consecutive runs into one token
        if c == "\n":
            if not tokens or tokens[-1].type != TT.NEWLINE:
                tokens.append(Token(TT.NEWLINE, "\n", line))
            line += 1
            i += 1
            continue

        # Two-character tokens (checked before single-char so '=>' beats '=')
        two = source[i : i + 2]
        two_map: dict[str, TT] = {
            "=>": TT.ARROW,
            "==": TT.EQ,
            "!=": TT.NEQ,
            "<=": TT.LTE,
            ">=": TT.GTE,
        }
        if two in two_map:
            tokens.append(Token(two_map[two], two, line))
            i += 2
            continue

        # Single-character tokens
        if c in _SINGLE:
            tokens.append(Token(_SINGLE[c], c, line))
            i += 1
            continue

        # String literals
        if c == '"':
            i += 1
            chars: list[str] = []
            has_interp = False
            while i < len(source) and source[i] != '"':
                if source[i] == "\\" and i + 1 < len(source):
                    i += 1
                    esc = source[i]
                    chars.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(esc, esc))
                else:
                    # Detect interpolation: '{' not followed by another '{'
                    if (source[i] == "{"
                            and i + 1 < len(source)
                            and source[i + 1] != "{"):
                        has_interp = True
                    chars.append(source[i])
                i += 1
            if i >= len(source):
                raise LexError(f"Unterminated string at line {line}")
            i += 1  # closing "
            raw = "".join(chars)
            tt = TT.INTERP_STRING if has_interp else TT.STRING
            tokens.append(Token(tt, raw, line))
            continue

        # Numbers
        if c.isdigit():
            start = i
            while i < len(source) and source[i].isdigit():
                i += 1
            if (i < len(source) and source[i] == "."
                    and i + 1 < len(source) and source[i + 1].isdigit()):
                i += 1  # consume '.'
                while i < len(source) and source[i].isdigit():
                    i += 1
                tokens.append(Token(TT.FLOAT, float(source[start:i]), line))
            else:
                tokens.append(Token(TT.INT, int(source[start:i]), line))
            continue

        # Identifiers and keywords
        if c.isalpha() or c == "_":
            start = i
            while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            tt = _KEYWORDS.get(word, TT.IDENT)
            if tt == TT.IDENT:
                value: object = word
            elif tt == TT.TRUE:
                value = True
            elif tt == TT.FALSE:
                value = False
            elif tt == TT.NULL:
                value = None
            else:
                value = word
            tokens.append(Token(tt, value, line))
            continue

        raise LexError(f"Unexpected character {c!r} at line {line}")

    tokens.append(Token(TT.EOF, None, line))
    return tokens
