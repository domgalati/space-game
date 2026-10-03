"""Alerts and the event log.

Urgent things raise one alert at a time at the top centre, the most severe first, each for
ALERT_MS. Everything, alert or not, also goes into a short event log at the lower left that
fades over LOG_MS. While an enemy ping is on its way, a strip pinned under the banner says
when it lands and how to dodge it, then says whether it missed or caught you.
"""
from collections import namedtuple

import pygame

from util.config import SCREEN_HEIGHT, SCREEN_WIDTH

from .glyphs import draw_text, text_width
from .panel import Panel
from .theme import (
    BLINK_MS, BRIGHT, CELL_H, CELL_W, DANGER, FILL, FLASH_MS, LABEL, VALUE, WARN, blink, shade,
)

NOTE, INFO, WARNING, DANGER_LEVEL = -1, 0, 1, 2  # a note goes in the log without an alert
COLOURS = {NOTE: VALUE, INFO: LABEL, WARNING: WARN, DANGER_LEVEL: DANGER}
NAMES = {INFO: "INFO", WARNING: "WARNING", DANGER_LEVEL: "DANGER"}
ALERT_MS = 2500
FADE_IN_MS = 200  # info alerts fade in
FADE_OUT_MS = 300  # every alert fades out at the end of its time
QUEUE_LIMIT = 4
LOG_SIZE = 5
LOG_MS = 8000
LOG_COLS = 44  # longer log lines are cut
OUTCOME_MS = 2000  # how long the ping strip shows MISSED or CAUGHT
TOP = 8
# Between the two status panels: 1080 - 2 x (8 + 304 + 8).
BAND_WIDTH = SCREEN_WIDTH - 2 * (TOP + 38 * CELL_W + TOP)
BANNER_ROWS_BIG = 4  # border, a 2x line, border
STRIP_TOP = TOP + (BANNER_ROWS_BIG + 1) * CELL_H + 4  # the ping strip stays put under the tallest banner
SEPARATORS = (" - ", ": ")

Event = namedtuple("Event", "text severity at_ms key")
PingWarning = namedtuple("PingWarning", "distance direction turns advice")


class Alert:
    def __init__(self, text, severity, key=None):
        self.text = text
        self.severity = severity
        self.key = key
        self.shown_at = None


class Alerts:
    """The queue behind the banner: most severe first, then oldest first."""

    def __init__(self):
        self.queue = []
        self.current = None

    def post(self, text, severity, now_ms, key=None):
        """Queue an alert. One with the same `key` as a queued or showing alert replaces it, so a
        hazard that repeats every turn refreshes its banner instead of piling up."""
        if key is not None:
            self.queue = [alert for alert in self.queue if alert.key != key]
            if self.current is not None and self.current.key == key:
                self.current.text = text
                self.current.shown_at = now_ms - FADE_IN_MS  # refreshed, without fading in again
                return
        if self.current is not None and severity > self.current.severity:
            self.current = None  # something worse cuts in; the cut alert is still in the log
        self.queue.append(Alert(text, severity, key))
        if len(self.queue) > QUEUE_LIMIT:
            self.queue.remove(min(self.queue, key=lambda alert: alert.severity))

    def update(self, now_ms):
        """The alert on screen this frame, or None."""
        if self.current is not None and now_ms - self.current.shown_at >= ALERT_MS:
            self.current = None
        if self.current is None and self.queue:
            worst = max(alert.severity for alert in self.queue)
            self.current = next(alert for alert in self.queue if alert.severity == worst)
            self.queue.remove(self.current)
            self.current.shown_at = now_ms
        return self.current


class EventLog:
    def __init__(self):
        self.entries = []

    def add(self, text, severity, now_ms, key=None):
        """A keyed event replaces the newest line if that has the same key, as each turn in the heat does."""
        if key is not None and self.entries and self.entries[-1].key == key:
            self.entries.pop()
        self.entries.append(Event(text, severity, now_ms, key))
        del self.entries[:-LOG_SIZE]

    def visible(self, now_ms):
        return [event for event in self.entries if now_ms - event.at_ms < LOG_MS]

    def texts(self):
        return [event.text for event in self.entries]

    def latest(self):
        return self.entries[-1].text if self.entries else None


def split_headline(text):
    """A short headline for the 2x line, and the rest as a detail line under it."""
    for separator in SEPARATORS:
        head, found, rest = text.partition(separator)
        if found and head:
            return head, rest
    return text, ""


def fit(text, width_px, scale=1):
    cells = width_px // (CELL_W * scale)
    return text if len(text) <= cells else text[:cells - 1] + "."


class Banner:
    """Draws the alert queue's current alert: TeleSys at 2x with glow on a glyph-bordered strip."""

    def __init__(self):
        self.alerts = Alerts()
        self._panels = {}

    def panel(self, cols, rows):
        key = (cols, rows)
        if key not in self._panels:
            self._panels[key] = Panel(cols, rows)
            self._panels[key].open(-1_000_000)  # banners fade and flash; they don't wipe
        return self._panels[key]

    def draw(self, screen, now_ms):
        alert = self.alerts.update(now_ms)
        if alert is None:
            return
        colour = COLOURS[alert.severity]
        age = now_ms - alert.shown_at
        room = BAND_WIDTH - 4 * CELL_W
        head, detail = (alert.text, "") if text_width(alert.text, 2) <= room else split_headline(alert.text)
        scale = 2 if text_width(head, 2) <= room else 1
        head, detail = fit(head, room, scale), fit(detail, room)
        width = max(text_width(head, scale), text_width(detail))
        rows = 2 + scale + (1 if detail else 0)
        panel = self.panel(width // CELL_W + 4, rows)
        panel.begin(NAMES[alert.severity], shade(colour, 0.4), colour)
        if alert.severity == WARNING and BLINK_MS <= age < 2 * BLINK_MS:
            head_colour = shade(colour, 0.7)  # blinks once
        else:
            head_colour = colour
        x = (panel.width - text_width(head, scale)) // 2
        draw_text(panel.surface, (x, CELL_H), head, head_colour, scale=scale, glow=head_colour == colour)
        if detail:
            x = (panel.width - text_width(detail)) // 2
            draw_text(panel.surface, (x, (1 + scale) * CELL_H), detail, VALUE)
        if alert.severity == DANGER_LEVEL and age < FLASH_MS:
            panel.flash(now_ms - age, BRIGHT)
        alpha = min(1.0, (ALERT_MS - age) / FADE_OUT_MS)
        if alert.severity == INFO:
            alpha = min(alpha, age / FADE_IN_MS)
        panel.blit(screen, ((SCREEN_WIDTH - panel.width) // 2, TOP), now_ms, alpha=int(255 * max(0.0, alpha)))


class PingStrip:
    """Pinned under the banner while an enemy ping is on its way, then MISSED or CAUGHT."""

    def __init__(self):
        self.outcome = None  # (caught, shown until ms)
        self._panels = {}

    def landed(self, caught, now_ms):
        self.outcome = (caught, now_ms + OUTCOME_MS)

    def panel(self, cols):
        if cols not in self._panels:
            self._panels[cols] = Panel(cols, 4)
            self._panels[cols].open(-1_000_000)
        return self._panels[cols]

    def draw(self, screen, warning, now_ms):
        if warning is not None:
            lines = self.incoming(warning, now_ms)
            title, colour = "INCOMING PING", WARN
        elif self.outcome is not None and now_ms < self.outcome[1]:
            caught = self.outcome[0]
            title, colour = ("CAUGHT", WARN) if caught else ("MISSED", LABEL)
            lines = [[("(( ", colour, True), ("THEY HAVE YOUR POSITION" if caught else "THE PING MISSED YOU",
                                              VALUE, False)]]
        else:
            return
        width = max(sum(text_width(text) for text, _, _ in line) for line in lines)
        panel = self.panel(min(BAND_WIDTH, width + 4 * CELL_W) // CELL_W)
        panel.begin(title, shade(colour, 0.4), colour)
        for row, line in enumerate(lines, start=1):
            x, y = panel.at(2, row)
            for text, tone, glow in line:
                x += draw_text(panel.surface, (x, y), text, tone, glow=glow)
        panel.blit(screen, ((SCREEN_WIDTH - panel.width) // 2, STRIP_TOP), now_ms)

    def incoming(self, warning, now_ms):
        turns = f"{warning.turns} TURN{'S' if warning.turns > 1 else ''}"
        return [
            [("(( ", WARN, True), (f"{warning.distance} {warning.direction}  ", VALUE, False),
             (turns, WARN if blink(now_ms) else shade(WARN, 0.7), blink(now_ms))],
            [(fit(warning.advice, BAND_WIDTH - 4 * CELL_W), LABEL, False)],
        ]


def draw_log(screen, log, now_ms):
    """The last few events, lower left, newest at the bottom, each fading out over LOG_MS."""
    events = log.visible(now_ms)
    bottom = SCREEN_HEIGHT - TOP
    for i, event in enumerate(reversed(events)):
        age = now_ms - event.at_ms
        life = 1 - age / LOG_MS
        y = bottom - (i + 1) * CELL_H
        line = "> " + fit(event.text, LOG_COLS * CELL_W)
        plate = pygame.Surface((text_width(line) + CELL_W, CELL_H), pygame.SRCALPHA)
        plate.fill((*FILL[:3], int(FILL[3] * min(1.0, 2 * life))))
        screen.blit(plate, (TOP, y))
        colour = shade(COLOURS[event.severity], 1 - life)
        draw_text(screen, (TOP + CELL_W // 2, y), line, colour, glow=age < 1000)
