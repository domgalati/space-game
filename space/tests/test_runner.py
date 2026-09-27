import pytest

from dialogue import DialogueError, DialogueRunner, End, Line, Options, parse_yarn
from fakes import FakeContext, run_until_input

SCRIPT = """
title: Start
---
<<if visited("Start")>>
    Sue: Back again?
<<else>>
    Sue: Hello, stranger.
<<endif>>
<<jump Menu>>
===

title: Menu
tags: noexit
---
-> Ask about work
    Sue: I dig.
-> Secret <<if $trusted>>
    Sue: Between us...
    <<set $told to true>>
-> Leave
    <<stop>>
Sue: Anything else?
<<jump Menu>>
===

title: Gift
---
<<give "Rations" 2>>
Sue: Take these.
===
"""


def make_runner(ctx=None):
    ctx = ctx or FakeContext()
    return DialogueRunner(parse_yarn(SCRIPT, "test.yarn"), ctx), ctx


def texts(events):
    return [event.text for event in events if isinstance(event, Line)]


def test_start_line_then_menu_with_hidden_option():
    runner, _ = make_runner()
    runner.start()
    events = run_until_input(runner)
    assert texts(events) == ["Hello, stranger."]
    assert events[0].speaker == "Sue"
    assert isinstance(events[-1], Options)
    assert events[-1].choices == ["Ask about work", "Leave"]
    assert not runner.can_exit


def test_gated_option_appears_and_sets_flag():
    ctx = FakeContext()
    ctx.vars["trusted"] = True
    runner, _ = make_runner(ctx)
    runner.start()
    options = run_until_input(runner)[-1]
    assert options.choices == ["Ask about work", "Secret", "Leave"]
    runner.select(1)
    events = run_until_input(runner)
    assert texts(events) == ["Between us...", "Anything else?"]
    assert ctx.vars["told"] is True


def test_option_body_falls_through_then_jumps_back():
    runner, _ = make_runner()
    runner.start()
    run_until_input(runner)
    runner.select(0)
    events = run_until_input(runner)
    assert texts(events) == ["I dig.", "Anything else?"]
    assert isinstance(events[-1], Options)


def test_stop_ends_and_marks_visited():
    runner, ctx = make_runner()
    runner.start()
    run_until_input(runner)
    runner.select(1)
    assert isinstance(runner.advance(), End)
    assert runner.finished
    assert ctx.visits == {"Start": 1, "Menu": 1}

    runner.start()
    events = run_until_input(runner)
    assert texts(events) == ["Back again?"]


def test_commands_reach_context():
    runner, ctx = make_runner()
    runner.start("Gift")
    assert texts(run_until_input(runner)) == ["Take these."]
    assert ctx.commands == [("give", ["Rations", 2])]
    assert runner.can_exit


def test_misuse_and_script_errors():
    runner, _ = make_runner()
    runner.start()
    run_until_input(runner)
    with pytest.raises(DialogueError):
        runner.advance()
    with pytest.raises(DialogueError):
        runner.select(9)

    program = parse_yarn("title: Start\n---\n{nope()}\n===\n", "broken.yarn")
    broken = DialogueRunner(program, FakeContext())
    broken.start()
    with pytest.raises(DialogueError, match="broken.yarn:3"):
        broken.advance()
    with pytest.raises(DialogueError, match="No node"):
        broken.start("Missing")


def test_all_options_hidden_skips_group():
    program = parse_yarn("title: Start\n---\n-> A <<if false>>\nAfter.\n===\n")
    runner = DialogueRunner(program, FakeContext())
    runner.start()
    events = run_until_input(runner)
    assert texts(events) == ["After."]
    assert isinstance(events[-1], End)
