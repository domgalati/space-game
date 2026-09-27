"""Parser for the subset of Yarn Spinner 2 syntax this game supports.

Supported:
    title: / tags: headers, --- and === delimiters, // comments, trailing #hashtags
    Speaker: text lines with {expression} interpolation and \\ escapes
    -> option lines, indented option bodies, -> option <<if condition>>
    <<if>> <<elseif>> <<else>> <<endif>>
    <<set $x to expr>>  <<declare $x = expr>>  <<jump Node>>  <<stop>>
    any other <<command arg "arg" {expr}>> is handed to the game
"""
import re
from pathlib import Path

from .errors import DialogueError
from .expressions import Literal, parse_expression, to_text

_TITLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_ASSIGN_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_.]*)\s*(?:to|=)\s*(.+)$")
_TRAILING_TYPE_RE = re.compile(r"\s+as\s+\w+\s*$")
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


class Template:
    """Text with {expression} holes, rendered against a runtime environment."""

    def __init__(self, parts):
        self.parts = parts

    def render(self, env):
        return "".join(part if isinstance(part, str) else to_text(part.evaluate(env)) for part in self.parts)

    def evaluate(self, env):
        return self.render(env)


class LineStmt:
    def __init__(self, speaker, text, line):
        self.speaker = speaker
        self.text = text
        self.line = line


class OptionStmt:
    def __init__(self, text, condition, body, line):
        self.text = text
        self.condition = condition
        self.body = body
        self.line = line


class OptionGroup:
    def __init__(self, options, line):
        self.options = options
        self.line = line


class IfStmt:
    def __init__(self, branches, line):
        self.branches = branches  # [(condition or None for else, body)]
        self.line = line


class SetStmt:
    def __init__(self, name, expr, line, declare=False):
        self.name = name
        self.expr = expr
        self.line = line
        self.declare = declare


class JumpStmt:
    def __init__(self, target, line):
        self.target = target
        self.line = line


class StopStmt:
    def __init__(self, line):
        self.line = line


class CommandStmt:
    def __init__(self, name, args, line):
        self.name = name
        self.args = args
        self.line = line


class Node:
    def __init__(self, title, tags, body, source, line):
        self.title = title
        self.tags = tags
        self.body = body
        self.source = source
        self.line = line


class YarnProgram:
    def __init__(self, nodes, source):
        self.nodes = nodes
        self.source = source

    def node(self, title):
        return self.nodes.get(title)


def _scan(text, stop):
    """Index of the first unescaped char in ``stop`` outside {braces}, strings, and <<commands>>."""
    depth = 0
    command = False
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if in_string:
            if c == '"':
                in_string = False
        elif depth:
            if c == '"':
                in_string = True
            elif c == "}":
                depth -= 1
        elif command:
            if c == '"':
                in_string = True
            elif text.startswith(">>", i):
                command = False
                i += 1
        elif c == "{":
            depth += 1
        elif text.startswith("<<", i):
            command = True
            i += 1
        elif stop(text, i):
            return i
        i += 1
    return -1


def _strip_comment(text):
    index = _scan(text, lambda t, i: t.startswith("//", i))
    return text if index == -1 else text[:index]


def _strip_hashtags(text):
    index = _scan(text, lambda t, i: t[i] == "#" and (i == 0 or t[i - 1].isspace()))
    if index == -1:
        return text, []
    return text[:index].rstrip(), text[index:].split()


def _split_speaker(text):
    index = _scan(text, lambda t, i: t[i] == ":")
    if index <= 0:
        return None, text
    return text[:index].strip(), text[index + 1:].strip()


def _closing_brace(text, start):
    in_string = False
    i = start
    while i < len(text):
        c = text[i]
        if in_string:
            if c == "\\":
                i += 1
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
        elif c == "}":
            return i
        i += 1
    return -1


def parse_template(text, source=None, line=None):
    parts = []
    buf = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            buf.append(text[i + 1])
            i += 2
            continue
        if c == "{":
            end = _closing_brace(text, i + 1)
            if end == -1:
                raise DialogueError(f"Unclosed {{ in {text!r}", source, line)
            if buf:
                parts.append("".join(buf))
                buf = []
            parts.append(parse_expression(text[i + 1:end], source, line))
            i = end + 1
            continue
        buf.append(c)
        i += 1
    if buf:
        parts.append("".join(buf))
    return Template(parts)


def _split_args(text):
    args = []
    buf = []
    depth = 0
    in_string = False
    for c in text:
        if in_string:
            buf.append(c)
            if c == '"' and not (len(buf) > 1 and buf[-2] == "\\"):
                in_string = False
        elif c == '"':
            in_string = True
            buf.append(c)
        elif c == "{":
            depth += 1
            buf.append(c)
        elif c == "}":
            depth -= 1
            buf.append(c)
        elif c.isspace() and depth == 0:
            if buf:
                args.append("".join(buf))
                buf = []
        else:
            buf.append(c)
    if buf:
        args.append("".join(buf))
    return args


def _parse_arg(raw, source, line):
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return Literal(re.sub(r"\\(.)", r"\1", raw[1:-1]))
    if raw.startswith("{") and raw.endswith("}") and _closing_brace(raw, 1) == len(raw) - 1:
        return parse_expression(raw[1:-1], source, line)
    if _NUMBER_RE.match(raw):
        return Literal(float(raw) if "." in raw else int(raw))
    if "{" in raw:
        return parse_template(raw, source, line)
    return Literal(raw)


class _BodyParser:
    def __init__(self, lines, source):
        self.lines = lines  # [(indent, text, line_number)]
        self.source = source
        self.i = 0

    def error(self, message, line):
        return DialogueError(message, self.source, line)

    def command_parts(self, text, line):
        if not text.endswith(">>"):
            raise self.error(f"Command is missing '>>': {text!r}", line)
        inner = text[2:-2].strip()
        keyword, _, rest = inner.partition(" ")
        return keyword, rest.strip()

    def parse(self):
        body = self.block(0, ())
        if self.i < len(self.lines):
            _, text, line = self.lines[self.i]
            raise self.error(f"Unexpected {text!r}", line)
        return body

    def block(self, min_indent, stop_keywords):
        stmts = []
        while self.i < len(self.lines):
            indent, text, line = self.lines[self.i]
            if indent < min_indent:
                break
            if text.startswith("->"):
                stmts.append(self.option_group(indent))
                continue
            if text.startswith("<<"):
                keyword, rest = self.command_parts(text, line)
                if keyword in ("elseif", "else", "endif"):
                    if keyword in stop_keywords:
                        break
                    raise self.error(f"<<{keyword}>> without a matching <<if>>", line)
                self.i += 1
                stmts.append(self.command(keyword, rest, line, min_indent))
                continue
            self.i += 1
            stmts.append(self.dialogue_line(text, line))
        return stmts

    def dialogue_line(self, text, line):
        text, _tags = _strip_hashtags(text)
        speaker, body = _split_speaker(text)
        speaker_template = parse_template(speaker, self.source, line) if speaker else None
        return LineStmt(speaker_template, parse_template(body, self.source, line), line)

    def command(self, keyword, rest, line, min_indent):
        if keyword == "if":
            return self.if_block(rest, line, min_indent)
        if keyword in ("set", "declare"):
            rest = _TRAILING_TYPE_RE.sub("", rest) if keyword == "declare" else rest
            match = _ASSIGN_RE.match(rest)
            if not match:
                raise self.error(f"Expected <<{keyword} $name to value>>, got {rest!r}", line)
            expr = parse_expression(match.group(2), self.source, line)
            return SetStmt(match.group(1), expr, line, declare=keyword == "declare")
        if keyword == "jump":
            if not _TITLE_RE.match(rest):
                raise self.error(f"<<jump>> needs a node title, got {rest!r}", line)
            return JumpStmt(rest, line)
        if keyword == "stop":
            return StopStmt(line)
        if not keyword:
            raise self.error("Empty command", line)
        args = [_parse_arg(raw, self.source, line) for raw in _split_args(rest)]
        return CommandStmt(keyword, args, line)

    def if_block(self, condition_text, line, min_indent):
        if not condition_text:
            raise self.error("<<if>> needs a condition", line)
        branches = []
        condition = parse_expression(condition_text, self.source, line)
        seen_else = False
        while True:
            body = self.block(min_indent, ("elseif", "else", "endif"))
            branches.append((condition, body))
            if self.i >= len(self.lines):
                raise self.error("<<if>> is missing its <<endif>>", line)
            indent, text, at = self.lines[self.i]
            if indent < min_indent or not text.startswith("<<"):
                raise self.error("<<if>> is missing its <<endif>>", line)
            keyword, rest = self.command_parts(text, at)
            self.i += 1
            if keyword == "endif":
                return IfStmt(branches, line)
            if seen_else:
                raise self.error(f"<<{keyword}>> after <<else>>", at)
            if keyword == "else":
                seen_else = True
                condition = None
            else:
                condition = parse_expression(rest, self.source, at)

    def option_group(self, opt_indent):
        options = []
        first_line = self.lines[self.i][2]
        while self.i < len(self.lines):
            indent, text, line = self.lines[self.i]
            if indent != opt_indent or not text.startswith("->"):
                break
            self.i += 1
            option_text, _tags = _strip_hashtags(text[2:].strip())
            condition = None
            if option_text.endswith(">>"):
                start = option_text.rfind("<<")
                keyword, rest = self.command_parts(option_text[start:], line)
                if keyword != "if":
                    raise self.error(f"Options only support <<if>>, got <<{keyword}>>", line)
                condition = parse_expression(rest, self.source, line)
                option_text = option_text[:start].rstrip()
            if not option_text:
                raise self.error("Option has no text", line)
            body = self.block(opt_indent + 1, ())
            options.append(OptionStmt(parse_template(option_text, self.source, line), condition, body, line))
        return OptionGroup(options, first_line)


def parse_yarn(text, source="<yarn>"):
    nodes = {}
    headers = {}
    header_line = None
    body_lines = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw.expandtabs(4)).rstrip()
        stripped = line.strip()
        if body_lines is None:
            if not stripped:
                continue
            if stripped == "---":
                title = headers.get("title")
                if not title:
                    raise DialogueError("Node has no title: header", source, header_line or number)
                if not _TITLE_RE.match(title):
                    raise DialogueError(f"Invalid node title {title!r}", source, header_line)
                if title in nodes:
                    raise DialogueError(f"Duplicate node title {title!r}", source, header_line)
                body_lines = []
                continue
            key, sep, value = stripped.partition(":")
            if not sep:
                raise DialogueError(f"Expected a 'key: value' header or '---', got {stripped!r}", source, number)
            header_line = header_line or number
            headers[key.strip()] = value.strip()
            continue
        if stripped == "===":
            parser = _BodyParser(body_lines, source)
            title = headers["title"]
            nodes[title] = Node(title, headers.get("tags", "").split(), parser.parse(), source, header_line)
            headers = {}
            header_line = None
            body_lines = None
            continue
        if stripped:
            body_lines.append((len(line) - len(line.lstrip()), stripped, number))
    if body_lines is not None:
        raise DialogueError(f"Node {headers.get('title')!r} is missing its closing ===", source, header_line)
    if headers:
        raise DialogueError("Headers without a node body", source, header_line)

    program = YarnProgram(nodes, source)
    _check_jumps(program)
    return program


def _check_jumps(program):
    def walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, JumpStmt) and stmt.target not in program.nodes:
                raise DialogueError(f"<<jump {stmt.target}>> goes to a node that doesn't exist", program.source, stmt.line)
            if isinstance(stmt, IfStmt):
                for _, body in stmt.branches:
                    walk(body)
            elif isinstance(stmt, OptionGroup):
                for option in stmt.options:
                    walk(option.body)

    for node in program.nodes.values():
        walk(node.body)


def load_yarn(path):
    path = Path(path)
    return parse_yarn(path.read_text(encoding="utf-8"), source=path.name)
