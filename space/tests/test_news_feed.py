from entities.player import Player
from util.economy.news_feed import FRESH_TICKS, MAX_STORIES, NewsFeed
from world.save import load_game, save_game
from world.world_state import WorldState


def goods(**prices):
    return {name: {"basePrice": base, "currentPrice": current} for name, (base, current) in prices.items()}


def boom():
    return [{"good": "Steel", "price": 405, "change": "+50%"}]


def fresh_feed():
    return NewsFeed(WorldState())


def test_story_stays_hidden_until_its_market_is_checked_after_it_fired():
    feed = fresh_feed()
    feed.advance()
    feed.observe("Etheora", goods(Steel=(270, 270)))
    feed.record("Etheora", "Boom", boom())
    assert feed.known_stories() == []

    feed.observe("Etheora", goods(Steel=(270, 405)))
    assert [story["event"] for story in feed.known_stories()] == ["Boom"]


def test_stale_markets_hide_their_stories():
    feed = fresh_feed()
    feed.advance()
    feed.record("Etheora", "Boom", boom())
    feed.observe("Etheora", goods(Steel=(270, 405)))
    for _ in range(FRESH_TICKS + 1):
        feed.advance()
    assert not feed.is_fresh("Etheora")
    assert feed.known_stories() == []
    assert feed.stories == []


def test_known_stories_are_newest_first_and_capped():
    feed = fresh_feed()
    for index in range(MAX_STORIES + 5):
        feed.record("Etheora", f"Event {index}", boom())
    feed.observe("Etheora", goods(Steel=(270, 405)))
    known = feed.known_stories()
    assert len(feed.stories) == MAX_STORIES
    assert known[0]["event"] == f"Event {MAX_STORIES + 4}"


def test_observe_snapshots_prices_and_skips_empty_markets():
    feed = fresh_feed()
    feed.advance()
    feed.observe("Etheora", goods(Steel=(270, 300.4)))
    feed.observe("Moon", {})
    assert feed.intel["Etheora"]["tick"] == 1
    assert feed.intel["Etheora"]["goods"] == {"Steel": {"price": 300, "base": 270}}
    assert "Moon" not in feed.intel
    assert feed.market_status(["Terramonta"]) == [("Terramonta", None), ("Etheora", 0)]


def test_feed_survives_a_save_and_reload(tmp_path):
    path = str(tmp_path / "save.yaml")
    world = WorldState()
    feed = NewsFeed(world)
    feed.advance()
    feed.record("Etheora", "Boom", boom())
    feed.observe("Etheora", goods(Steel=(270, 405)))
    save_game(Player(), world, path)

    reloaded = NewsFeed(load_game(path)[1])
    assert reloaded.tick == 1
    assert [story["event"] for story in reloaded.known_stories()] == ["Boom"]
