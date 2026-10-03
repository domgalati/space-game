import random
import re
from pathlib import Path

import pygame.freetype
import pytest

from util.economy import trade
from util.economy.economy import Economy
from util.economy.news import MAX_LINES, NO_WIRE, QUIET_WIRE, render_news
from util.economy.news_feed import FRESH_TICKS, NewsFeed
from util.terminal_text import Transient, plain, to_lines
from world.world_state import WorldState

TELESYS = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "TeleSys.ttf"
PLACES = ["Terramonta", "Etheora", "Nexum Astra"]


def goods(**prices):
    return {name: {"basePrice": base, "currentPrice": current} for name, (base, current) in prices.items()}


def feed_with_news(tmp_path):
    feed = NewsFeed(WorldState(str(tmp_path / "w.yaml")))
    feed.advance()
    feed.record("Terramonta", "Mining Accident", [
        {"good": "Raw Minerals", "price": 120, "change": "+20%"},
        {"good": "Steel", "price": 180, "change": "-10%"},
    ])
    feed.record("Etheora", "Boom", [{"good": "Steel", "price": 405, "change": "+50%"}])
    feed.record("Nexum Astra", "Customs Crackdown", [{"good": "Luxury Goods", "price": 1260, "change": "+40%"}])
    feed.observe("Terramonta", goods(**{"Raw Minerals": (100, 120), "Steel": (200, 180)}))
    feed.observe("Etheora", goods(Steel=(270, 405)))
    return feed


def edition(feed, seed=1):
    return render_news(feed, PLACES, rng=random.Random(seed))


def page(feed, seed=1, width=80):
    report = edition(feed, seed)
    return [plain(line) for line in to_lines(report.renderable, width)]


def intro(feed, seed=1, width=80):
    report = edition(feed, seed)
    assert report.intro is not None
    return [plain(line) for line in to_lines(report.intro, width)]


def row_with(lines, *parts):
    return any(all(part in line for part in parts) for line in lines)


def test_front_page_shows_only_checked_markets(tmp_path):
    feed = feed_with_news(tmp_path)
    lines = page(feed)
    text = "\n".join(lines)
    assert "THE NEXUS WIRE" in text and "LANDING 1" in text
    assert "MINING ACCIDENT" in text and "BOOM" in text
    assert "CUSTOMS CRACKDOWN" not in text
    assert "POLLING ACTIVE WIRES" not in text
    assert row_with(lines, "Raw Minerals", "$120", "+20%")
    assert row_with(lines, "Steel", "$180", "-10%")
    assert row_with(lines, "Steel", "$405", "+50%")
    boot = intro(feed)
    assert row_with(boot, "Nexum Astra", "no contact")
    assert row_with(boot, "Etheora", "live")


def test_movers_use_the_price_seen_at_the_last_check(tmp_path):
    lines = page(feed_with_news(tmp_path))
    assert row_with(lines, "Steel", "Etheora", "$405", "+50%")
    assert row_with(lines, "Raw Minerals", "Terramonta", "$120", "+20%")


def test_stale_markets_are_flagged_in_the_intro_and_their_stories_dropped(tmp_path):
    feed = feed_with_news(tmp_path)
    for _ in range(FRESH_TICKS + 1):
        feed.advance()
    lines = page(feed)
    text = "\n".join(lines)
    assert row_with(intro(feed), "Etheora", "stale")
    assert "BOOM" not in text
    assert NO_WIRE in text


def test_quiet_wire_when_fresh_but_nothing_happened(tmp_path):
    feed = NewsFeed(WorldState(str(tmp_path / "w.yaml")))
    feed.advance()
    feed.observe("Etheora", goods(Steel=(270, 270)))
    assert QUIET_WIRE in "\n".join(page(feed))


@pytest.mark.parametrize("width", [80, 52])
def test_page_is_capped_and_fits_the_terminal(tmp_path, width):
    feed = NewsFeed(WorldState(str(tmp_path / "w.yaml")))
    feed.advance()
    for index in range(12):
        feed.record("Etheora", f"Event Number {index}", [
            {"good": "Steel", "price": 405, "change": "+50%"},
            {"good": "Rations", "price": 72, "change": "-20%"},
        ])
    feed.observe("Etheora", goods(Steel=(270, 405), Rations=(90, 72)))
    lines = page(feed, width=width)
    text = "\n".join(lines)
    assert len(lines) <= MAX_LINES
    assert all(len(line) <= width for line in lines)
    assert "EVENT NUMBER 11" in text
    # Without the wire-status block more cards fit; the footer appears only when some are held.
    if "older stories held" not in text:
        assert "EVENT NUMBER 0" in text


def test_wording_changes_numbers_do_not(tmp_path):
    feed = feed_with_news(tmp_path)
    first, second = page(feed, seed=1), page(feed, seed=2)
    assert first != second

    def numbers(lines):
        return sorted(re.findall(r"\$\d+|[+-]\d+%", "\n".join(lines)))

    assert numbers(first) == numbers(second)


def test_only_glyphs_telesys_has(tmp_path):
    pygame.init()
    pygame.freetype.init()
    font = pygame.freetype.Font(str(TELESYS), 16)
    feed = feed_with_news(tmp_path)
    used = set("".join(page(feed) + page(feed, width=52) + intro(feed) + intro(feed, width=52))) - {" "}
    assert not {ch for ch in used if font.get_metrics(ch)[0] is None}


def test_trade_news_reads_the_economy_feed(tmp_path):
    feed = feed_with_news(tmp_path)
    report = trade.handle("news", "", None, Economy("Terramonta", {"Terramonta": {}}, feed=feed))
    assert isinstance(report, Transient) and report.intro is not None
    assert "BOOM" in "\n".join(plain(line) for line in to_lines(report.renderable, 80))
    assert "POLLING ACTIVE WIRES" in "\n".join(plain(line) for line in to_lines(report.intro, 80))


def test_no_feed_means_no_wire():
    report = render_news(None)
    text = "\n".join(plain(line) for line in to_lines(report.renderable, 80))
    assert NO_WIRE in text
    assert report.intro is None
