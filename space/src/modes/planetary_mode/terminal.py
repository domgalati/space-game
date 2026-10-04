import pygame
from util.config import resolve_game_path
from util.terminal_text import PALETTE, Transient, to_lines
from .terminals import docking_terminal, market_terminal

COMMANDS = {
    "docking": ["help", "info", "prices", "buy", "sell", "cargo", "news", "refuel", "repair", "depart", "exit"],
    "market": ["help", "info", "prices", "buy", "sell", "cargo", "news", "exit"],
    "scan": ["help", "scan", "dock", "hail", "ping", "shield", "salvage", "news", "exit"],
}
QUANTITIES = ("all", "max")
# Bezel art per terminal. Every variant keeps the original screen opening, so text layout is unchanged.
_BEZELS = "space/assets/img/_style_samples/terminal_variants"
BEZELS = {
    "docking": f"{_BEZELS}/docking/terminal_screen.png",
    "market": f"{_BEZELS}/market/terminal_screen.png",
    "scan": f"{_BEZELS}/ship/terminal_screen.png",
}
DEFAULT_BEZEL = "space/assets/img/objects/terminal_screen.png"


def bezel_path(terminal_type):
    return resolve_game_path(BEZELS.get(terminal_type, DEFAULT_BEZEL))


def _common_prefix(words):
    if not words:
        return ""
    prefix = words[0]
    for word in words[1:]:
        while not word.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix


def complete_prefix(prefix, options):
    """Return (replacement, matches). matches is set when the line is already at the shared prefix."""
    folded = prefix.lower()
    matches = [option for option in options if option.lower().startswith(folded)]
    if not matches:
        return prefix, []
    if len(matches) == 1:
        completed = matches[0]
        if not completed.endswith(" "):
            completed += " "
        return completed, []
    common = _common_prefix([match.lower() for match in matches])
    if len(common) > len(prefix):
        return matches[0][:len(common)], []
    return prefix, matches


def _is_quantity(token):
    return token.isdigit() or token.lower() in QUANTITIES


def split_argument(rest):
    """Return (name_prefix, quantity_or_None). A quantity counts once a space follows it."""
    words = rest.split()
    if words and _is_quantity(words[0]) and (len(words) > 1 or rest.endswith(" ")):
        quantity = words[0]
        remainder = rest[len(quantity):].lstrip().rstrip()
        return remainder, quantity
    return rest.rstrip(), None


ROW_REVEAL_SECONDS = 0.08  # scan-style reveal for wire-check intros
INTRO_HOLD_SECONDS = 0.45  # pause after the last row before the page opens


class Pager:
    """A less-style view over lines too tall for the terminal window."""

    def __init__(self, lines, height, keep=True):
        self.lines = lines
        self.height = height
        self.keep = keep  # copy into scrollback on close
        self.top = 0

    @property
    def max_top(self):
        return max(0, len(self.lines) - self.height)

    def scroll(self, rows):
        self.top = max(0, min(self.max_top, self.top + rows))

    def page(self, pages):
        self.scroll(pages * self.height)

    def visible(self):
        return self.lines[self.top:self.top + self.height]

    def status(self):
        last = min(self.top + self.height, len(self.lines))
        return f" {self.top + 1}-{last}/{len(self.lines)}  SPC next  B back  g/G top/end  Q close "


class BootSequence:
    """Row-reveal intro (like the planet scan) that then opens a pager."""

    def __init__(self, lines, pending, keep=False):
        self.lines = lines
        self.pending = pending
        self.keep = keep
        self.time = 0.0

    def rows_shown(self):
        return min(len(self.lines), int(self.time / ROW_REVEAL_SECONDS))

    def finished(self):
        return self.time >= len(self.lines) * ROW_REVEAL_SECONDS + INTRO_HOLD_SECONDS


class Terminal:
    columns = 80

    def __init__(self, terminal_type, planetary_mode, planet_name):
        self.terminal_type = terminal_type
        self.planetary_mode = planetary_mode
        self.planet_name = planet_name  # Store the planet name
        self.input_buffer = ""
        self.output_buffer = []
        self.history = []
        self.history_index = 0
        self.history_draft = ""
        self.active = False
        self.cursor_visible = True
        self.blink_timer = 0
        self.blink_interval = 50  # milliseconds
        self.max_lines = 13  # Adjust as needed for your map_surface size
        self.scroll_position = 0
        self.pager = None
        self.boot = None
        self._transient_output = False
        self._font = None

    def activate(self):
        self.active = True
        # Clear buffers or set up terminal-specific data

    def deactivate(self):
        self.active = False
        ## Call deactivate_terminal() from PlanetaryMode
        if self.planetary_mode:
            self.planetary_mode.deactivate_terminal()

    def depart(self):
        if self.planetary_mode:
            self.planetary_mode.return_to_star_system_mode()

    def process_input(self, event):
        if not self.active or event.type != pygame.KEYDOWN:
            return
        if self.boot:
            # Any key skips the wire-check animation and opens the page.
            self.finish_boot()
            return
        if self.pager:
            self._pager_key(event)
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self.input_buffer = self.input_buffer[:-1]
        elif event.key == pygame.K_UP:
            self._recall(-1)
        elif event.key == pygame.K_DOWN:
            self._recall(1)
        elif event.key == pygame.K_TAB:
            self.complete()
        elif event.unicode and event.unicode.isprintable():
            self.input_buffer += event.unicode

    def _submit(self):
        line = self.input_buffer.strip()
        self.scroll_position = 0
        before = len(self.output_buffer)
        self._transient_output = False
        self.boot = None
        self.execute_command(self.input_buffer)
        # The first new line is the "> command" echo; page only what the command printed.
        printed = self.flatten(self.output_buffer[before + 1:])
        if self.boot:
            del self.output_buffer[before + 1:]
        elif printed and (self._transient_output or len(printed) > self.max_lines):
            del self.output_buffer[before + 1:]
            self.pager = Pager(printed, self.max_lines, keep=not self._transient_output)
        self.input_buffer = ""
        if line and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self.history_index = len(self.history)
        self.history_draft = ""

    def finish_boot(self):
        """End the intro animation and open the pending pager content."""
        boot, self.boot = self.boot, None
        if boot is None:
            return
        self.pager = Pager(boot.pending, self.max_lines, keep=boot.keep)

    def _recall(self, direction):
        if direction < 0:
            if self.history_index == 0:
                return
            if self.history_index == len(self.history):
                self.history_draft = self.input_buffer
            self.history_index -= 1
            self.input_buffer = self.history[self.history_index]
            return
        if self.history_index >= len(self.history):
            return
        self.history_index += 1
        if self.history_index == len(self.history):
            self.input_buffer = self.history_draft
        else:
            self.input_buffer = self.history[self.history_index]

    def _pager_key(self, event):
        key, character = event.key, event.unicode
        if key == pygame.K_ESCAPE or character in ("q", "Q"):
            self.close_pager()
        elif key in (pygame.K_SPACE, pygame.K_PAGEDOWN) or character == " ":
            self.pager.page(1)
        elif key == pygame.K_PAGEUP or character in ("b", "B"):
            self.pager.page(-1)
        elif key == pygame.K_DOWN or character == "j":
            self.pager.scroll(1)
        elif key == pygame.K_UP or character == "k":
            self.pager.scroll(-1)
        elif key == pygame.K_END or character == "G":
            self.pager.top = self.pager.max_top
        elif key == pygame.K_HOME or character == "g":
            self.pager.top = 0

    def close_pager(self):
        """Like less -X: everything lands in scrollback, with the page you were reading on screen.

        Transient output (the news) is dropped instead, so stale editions never pile up.
        """
        pager, self.pager = self.pager, None
        if not pager.keep:
            self.scroll_position = 0
            return
        self.output_buffer.extend(pager.lines)
        total = len(self.flatten_output_buffer())
        first_viewed = total - len(pager.lines) + pager.top
        self.scroll_position = max(0, total - self.max_lines - first_viewed)

    def commands(self):
        return list(COMMANDS.get(self.terminal_type, []))

    def argument_candidates(self, verb):
        if verb not in ("buy", "sell") or self.planetary_mode is None:
            return []
        economy = getattr(self.planetary_mode, "economy", None)
        if economy is None:
            return []
        return list(economy.goods())

    def show_matches(self, matches):
        self.output_buffer.extend(self.wrap_text("  " + "  ".join(matches), self.columns))

    def show(self, result):
        """Append a command result: plain text is wrapped, Rich renderables are laid out to fit."""
        if isinstance(result, Transient):
            self._transient_output = True
            body = to_lines(result.renderable, self.columns)
            if result.intro is not None:
                self.boot = BootSequence(to_lines(result.intro, self.columns), body, keep=False)
                return
            self.output_buffer.extend(body)
            return
        if isinstance(result, str):
            for line in result.split("\n"):
                self.output_buffer.extend(self.wrap_text(line, self.columns))
        else:
            self.output_buffer.extend(to_lines(result, self.columns))

    def complete(self):
        line = self.input_buffer
        leading = line[:len(line) - len(line.lstrip())]
        body = line[len(leading):]
        if not body.strip():
            self.show_matches(self.commands())
            return
        if " " not in body:
            replacement, matches = complete_prefix(body, self.commands())
            if matches:
                self.show_matches(matches)
            elif replacement != body:
                self.input_buffer = leading + replacement
            return

        verb, _, rest = body.partition(" ")
        candidates = self.argument_candidates(verb.lower())
        if not candidates:
            return
        prefix, quantity = split_argument(rest)
        canonical = next((command for command in self.commands() if command.lower() == verb.lower()), verb)
        if quantity is None:
            lead = f"{leading}{canonical} "
        else:
            lead = f"{leading}{canonical} {quantity} "
        replacement, matches = complete_prefix(prefix, candidates)
        if matches:
            self.show_matches(matches)
        elif replacement != prefix:
            self.input_buffer = lead + replacement

    def wrap_text(self, text, max_length):
        wrapped_lines = []
        while len(text) > max_length:
            # Find the nearest space before the max_length
            if text.find('\n') > 0: #if text contains \n
                split_index = text.rfind('\n', 0, max_length)
            else:
                split_index = text.rfind(' ', 0, max_length)
            if split_index == -1:  # No spaces found, force split
                split_index = max_length

            # Split the line and add to the list
            wrapped_lines.append(text[:split_index])
            text = text[split_index:].lstrip()  # Remove leading spaces from the rest

        wrapped_lines.append(text)  # Add the last part of the text
        return wrapped_lines

    def execute_command(self, command):
        self.output_buffer.append(f"> {command}")
        # Process the command based on terminal type
        if self.terminal_type == "docking":
            result = docking_terminal.handle_command(command, self.planetary_mode)
        elif self.terminal_type == "market":
            result = market_terminal.handle_command(command, self.planetary_mode)
        else:
            # Default or other terminal types
            result = "Command not recognized in this terminal."

        verb = command.strip().lower()
        if verb == "exit":
            self.deactivate()
       
        if verb == "depart" and self.terminal_type == "docking":
            self.depart()

        self.show(result)


    def update(self, dt):
        if not self.active:
            return
        if self.boot:
            self.boot.time += dt
            if self.boot.finished():
                self.finish_boot()
            return
        self.blink_timer += dt
        if self.blink_timer * 200 >= self.blink_interval:
            self.blink_timer = 0
            self.cursor_visible = not self.cursor_visible

    @staticmethod
    def flatten(lines):
        """Split plain strings on newlines; span lines are already one row each."""
        flattened = []
        for line in lines:
            if isinstance(line, str):
                flattened.extend(line.split('\n'))
            else:
                flattened.append(line)
        return flattened

    def flatten_output_buffer(self):
        return self.flatten(self.output_buffer)

    def _draw_line(self, surface, font, line, x, y):
        if isinstance(line, str):
            line = ((line, PALETTE["body"], None),)
        cell = font.size(" ")[0]
        column = 0
        for text, fg, bg in line:
            left = x + column * cell
            if bg is not None:
                surface.fill(bg, (left, y - 2, len(text) * cell, font.get_height() + 4))
            surface.blit(font.render(text, True, fg), (left, y))
            column += len(text)

    def display(self, surface):
        if not self.active:
            return
        if self._font is None:
            self._font = pygame.font.Font(resolve_game_path("space/assets/fonts/TeleSys.ttf"), 16)
        font = self._font
        x, y_position = 100, 100
        step = font.get_height() + 5
        cell = font.size(" ")[0]

        if self.boot:
            shown = self.boot.rows_shown()
            for line in self.boot.lines[:shown]:
                self._draw_line(surface, font, line, x, y_position)
                y_position += step
            if shown < len(self.boot.lines):
                bar_width = min(self.columns, max(8, self.columns - 4)) * cell
                pygame.draw.line(surface, PALETTE["bright"], (x, y_position), (x + bar_width, y_position), 2)
            status = " SYNCING WIRES  SPC skip ".ljust(self.columns)[:self.columns]
            self._draw_line(
                surface, font,
                ((status, PALETTE["background"], PALETTE["body"]),),
                x, 100 + self.max_lines * step,
            )
            return

        if self.pager:
            rows = self.pager.visible()
        else:
            flattened_output = self.flatten_output_buffer()
            total_line_count = len(flattened_output)
            start_line = max(0, total_line_count - self.max_lines - self.scroll_position)
            end_line = min(start_line + self.max_lines, total_line_count)
            rows = flattened_output[start_line:end_line]

        for line in rows:
            self._draw_line(surface, font, line, x, y_position)
            y_position += step

        if self.pager:
            y_position = 100 + self.max_lines * step
            status = self.pager.status()[:self.columns].ljust(self.columns)
            self._draw_line(surface, font, ((status, PALETTE["background"], PALETTE["body"]),), x, y_position)
            return

        # Combine the input buffer text with the cursor for rendering
        input_text = f"> {self.input_buffer}"
        if self.cursor_visible:
            input_text += "_"  # Append the cursor symbol

        input_surface = font.render(input_text, True, PALETTE["input"])
        surface.blit(input_surface, (x, y_position))

    def scroll_up(self):
        if self.boot:
            return
        if self.pager:
            self.pager.scroll(-1)
            return
        self.scroll_position = min(self.scroll_position + 1, max(0, len(self.flatten_output_buffer()) - self.max_lines))

    def scroll_down(self):
        if self.boot:
            return
        if self.pager:
            self.pager.scroll(1)
            return
        self.scroll_position = max(self.scroll_position - 1, 0)
