import pytest

from dialogue.errors import DialogueError
from dialogue.expressions import parse_expression, to_text
from fakes import FakeContext


def evaluate(text, **variables):
    ctx = FakeContext(functions={"double": lambda n: n * 2, "greet": lambda name: f"hi {name}"})
    ctx.vars.update(variables)
    return parse_expression(text).evaluate(ctx)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1 + 2 * 3", 7),
        ("(1 + 2) * 3", 9),
        ("10 / 4", 2.5),
        ("7 % 3", 1),
        ("-2 + 5", 3),
        ('"a" + "b"', "ab"),
        ('"n" + 3', "n3"),
        ("true and false", False),
        ("true or false", True),
        ("not true", False),
        ("!false", True),
        ("true xor true", False),
        ("3 > 2 && 2 >= 2", True),
        ("1 is 1", True),
        ("1 eq 2", False),
        ("1 neq 2", True),
        ("2 lt 3 and 3 gte 3", True),
        ("1 < 2 == true", True),
    ],
)
def test_operators(text, expected):
    assert evaluate(text) == expected


def test_variables_and_functions():
    assert evaluate("$gold + double(4)", gold=10) == 18
    assert evaluate('greet("Sue")') == "hi Sue"
    assert evaluate("$missing") is False


def test_and_short_circuits():
    ctx = FakeContext(functions={"boom": lambda: 1 / 0})
    assert parse_expression("false and boom()").evaluate(ctx) is False


def test_string_escapes():
    assert evaluate(r'"say \"hi\""') == 'say "hi"'


@pytest.mark.parametrize("text", ["1 +", "(1", "double(1", "1 2", "@"])
def test_bad_expressions(text):
    with pytest.raises(DialogueError):
        parse_expression(text, source="t.yarn", line=4)


def test_error_mentions_location():
    with pytest.raises(DialogueError, match=r"t\.yarn:4"):
        parse_expression("1 +", source="t.yarn", line=4)


def test_to_text():
    assert to_text(5.0) == "5"
    assert to_text(2.5) == "2.5"
    assert to_text(True) == "true"
    assert to_text(None) == ""
