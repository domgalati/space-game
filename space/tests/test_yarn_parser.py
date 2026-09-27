import pytest

from dialogue.errors import DialogueError
from dialogue.yarn_parser import (
    CommandStmt,
    IfStmt,
    JumpStmt,
    LineStmt,
    OptionGroup,
    SetStmt,
    StopStmt,
    parse_yarn,
)
from fakes import FakeContext


def test_nodes_headers_and_tags():
    program = parse_yarn(
        """
title: Start
tags: noexit intro
position: 10,20
---
Hello.
===

title: Other
---
Bye.
===
"""
    )
    assert set(program.nodes) == {"Start", "Other"}
    assert program.node("Start").tags == ["noexit", "intro"]
    assert program.node("Start").line == 2


def test_lines_speakers_interpolation_and_escapes():
    program = parse_yarn(
        r"""
title: Start
---
Sue: Hello {$name}, you have {$gold + 1} credits. // a comment
Just narration here. #line:abc
Time\: ten o'clock
{$who}: Braced speaker
===
"""
    )
    ctx = FakeContext()
    ctx.vars.update(name="Rook", gold=4, who="Hesk")
    first, second, third, fourth = program.node("Start").body
    assert isinstance(first, LineStmt)
    assert first.speaker.render(ctx) == "Sue"
    assert first.text.render(ctx) == "Hello Rook, you have 5 credits."
    assert second.speaker is None
    assert second.text.render(ctx) == "Just narration here."
    assert third.speaker is None
    assert third.text.render(ctx) == "Time: ten o'clock"
    assert fourth.speaker.render(ctx) == "Hesk"


def test_options_with_bodies_and_conditions():
    program = parse_yarn(
        """
title: Start
---
-> First
    Sue: One.
    -> Nested
        Sue: Deep.
-> Second <<if $ok>> #tag
    <<jump Start>>
-> Third
After.
===
"""
    )
    group, after = program.node("Start").body
    assert isinstance(group, OptionGroup)
    first, second, third = group.options
    assert len(first.body) == 2
    assert isinstance(first.body[1], OptionGroup)
    assert second.condition is not None
    assert isinstance(second.body[0], JumpStmt)
    assert third.body == []
    assert isinstance(after, LineStmt)


def test_if_elseif_else():
    program = parse_yarn(
        """
title: Start
---
<<if $a>>
    A
<<elseif $b>>
    B
<<else>>
    C
<<endif>>
===
"""
    )
    (stmt,) = program.node("Start").body
    assert isinstance(stmt, IfStmt)
    assert [cond is None for cond, _ in stmt.branches] == [False, False, True]


def test_set_declare_stop_and_commands():
    program = parse_yarn(
        """
title: Start
---
<<declare $count = 0 as number>>
<<set $count to $count + 1>>
<<set $flag = true>>
<<give "Rations" 2>>
<<rep assembly {$count * 5}>>
<<stop>>
===
"""
    )
    declare, add, flag, give, rep, stop = program.node("Start").body
    assert isinstance(declare, SetStmt) and declare.declare
    assert isinstance(add, SetStmt) and add.name == "count"
    assert flag.name == "flag"
    assert isinstance(give, CommandStmt)
    ctx = FakeContext()
    ctx.vars["count"] = 2
    assert [arg.evaluate(ctx) for arg in give.args] == ["Rations", 2]
    assert [arg.evaluate(ctx) for arg in rep.args] == ["assembly", 10]
    assert isinstance(stop, StopStmt)


@pytest.mark.parametrize(
    "body, message, line",
    [
        ("<<if $x>>\nA", "missing its <<endif>>", 4),
        ("<<endif>>", "without a matching <<if>>", 4),
        ("<<jump Nowhere>>", "doesn't exist", 4),
        ("<<set count to 1>>", "Expected <<set", 4),
        ("Hi {$x", "Unclosed", 4),
        ("<<give 1", "missing '>>'", 4),
        ("<<if $x>>\n<<else>>\n<<elseif $y>>\n<<endif>>", "after <<else>>", 6),
    ],
)
def test_errors_report_line_numbers(body, message, line):
    text = f"\ntitle: Start\n---\n{body}\n===\n"
    with pytest.raises(DialogueError, match=message) as info:
        parse_yarn(text, source="bad.yarn")
    assert info.value.source == "bad.yarn"
    assert info.value.line == line


def test_missing_terminator_and_duplicate_titles():
    with pytest.raises(DialogueError, match="closing ==="):
        parse_yarn("title: Start\n---\nHi\n")
    with pytest.raises(DialogueError, match="Duplicate"):
        parse_yarn("title: A\n---\n===\ntitle: A\n---\n===\n")
    with pytest.raises(DialogueError, match="no title"):
        parse_yarn("tags: x\n---\n===\n")
