"""Yarn Spinner expressions: a tokenizer and recursive-descent evaluator (no eval)."""
import re

from .errors import DialogueError

_WORD_OPS = {
    "and": "and",
    "or": "or",
    "xor": "xor",
    "not": "not",
    "is": "==",
    "eq": "==",
    "neq": "!=",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
}
_SYMBOL_OPS = {
    "==": "==",
    "!=": "!=",
    ">=": ">=",
    "<=": "<=",
    "&&": "and",
    "||": "or",
    ">": ">",
    "<": "<",
    "!": "not",
    "^": "xor",
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
}
_TOKEN_RE = re.compile(
    r"""
    (?P<space>\s+)
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<var>\$[A-Za-z_][A-Za-z0-9_.]*)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_.]*)
  | (?P<op>==|!=|>=|<=|&&|\|\||[><!^+\-*/%])
  | (?P<punct>[(),])
    """,
    re.VERBOSE,
)


def tokenize(text, source=None, line=None):
    tokens = []
    pos = 0
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if not match:
            raise DialogueError(f"Unexpected character {text[pos]!r} in expression {text!r}", source, line)
        pos = match.end()
        kind = match.lastgroup
        value = match.group()
        if kind == "space":
            continue
        if kind == "num":
            tokens.append(("num", float(value) if "." in value else int(value)))
        elif kind == "str":
            tokens.append(("str", re.sub(r"\\(.)", r"\1", value[1:-1])))
        elif kind == "var":
            tokens.append(("var", value[1:]))
        elif kind == "ident":
            lowered = value.lower()
            if lowered in _WORD_OPS:
                tokens.append(("op", _WORD_OPS[lowered]))
            elif lowered in ("true", "false"):
                tokens.append(("bool", lowered == "true"))
            else:
                tokens.append(("ident", value))
        elif kind == "op":
            tokens.append(("op", _SYMBOL_OPS[value]))
        else:
            tokens.append((value, value))
    tokens.append(("eof", None))
    return tokens


class Literal:
    def __init__(self, value):
        self.value = value

    def evaluate(self, env):
        return self.value


class Variable:
    def __init__(self, name):
        self.name = name

    def evaluate(self, env):
        return env.get_var(self.name)


class Call:
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def evaluate(self, env):
        return env.call(self.name, [arg.evaluate(env) for arg in self.args])


class Unary:
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def evaluate(self, env):
        value = self.operand.evaluate(env)
        if self.op == "not":
            return not value
        return -value


class Binary:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, env):
        op = self.op
        if op == "and":
            return bool(self.left.evaluate(env)) and bool(self.right.evaluate(env))
        if op == "or":
            return bool(self.left.evaluate(env)) or bool(self.right.evaluate(env))
        a = self.left.evaluate(env)
        b = self.right.evaluate(env)
        if op == "xor":
            return bool(a) != bool(b)
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if op == "+":
            if isinstance(a, str) or isinstance(b, str):
                return to_text(a) + to_text(b)
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b
        if op == "%":
            return a % b
        if op == "<":
            return a < b
        if op == ">":
            return a > b
        if op == "<=":
            return a <= b
        return a >= b


# Lowest to highest precedence.
_LEVELS = [
    ("or", "xor"),
    ("and",),
    ("==", "!="),
    ("<", ">", "<=", ">="),
    ("+", "-"),
    ("*", "/", "%"),
]


class _Parser:
    def __init__(self, text, source, line):
        self.text = text
        self.source = source
        self.line = line
        self.tokens = tokenize(text, source, line)
        self.pos = 0

    def error(self, message):
        return DialogueError(f"{message} in expression {self.text!r}", self.source, self.line)

    def peek(self):
        return self.tokens[self.pos]

    def take(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, kind):
        token = self.take()
        if token[0] != kind:
            raise self.error(f"Expected {kind!r}")
        return token

    def parse(self):
        expr = self.binary(0)
        if self.peek()[0] != "eof":
            raise self.error(f"Unexpected {self.peek()[1]!r}")
        return expr

    def binary(self, level):
        if level == len(_LEVELS):
            return self.unary()
        left = self.binary(level + 1)
        while self.peek()[0] == "op" and self.peek()[1] in _LEVELS[level]:
            op = self.take()[1]
            left = Binary(op, left, self.binary(level + 1))
        return left

    def unary(self):
        token = self.peek()
        if token[0] == "op" and token[1] in ("not", "-"):
            self.take()
            return Unary(token[1], self.unary())
        return self.primary()

    def primary(self):
        kind, value = self.take()
        if kind in ("num", "str", "bool"):
            return Literal(value)
        if kind == "var":
            return Variable(value)
        if kind == "ident":
            self.expect("(")
            args = []
            if self.peek()[0] != ")":
                args.append(self.binary(0))
                while self.peek()[0] == ",":
                    self.take()
                    args.append(self.binary(0))
            self.expect(")")
            return Call(value, args)
        if kind == "(":
            expr = self.binary(0)
            self.expect(")")
            return expr
        if kind == "eof":
            raise self.error("Unexpected end")
        raise self.error(f"Unexpected {value!r}")


def parse_expression(text, source=None, line=None):
    return _Parser(text, source, line).parse()


def to_text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if value is None:
        return ""
    return str(value)
