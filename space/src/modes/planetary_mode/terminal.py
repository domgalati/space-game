"""Terminals ashore: the docking terminal and the market terminal, run against planetary mode's
player, market and planet. The command line itself is ui.terminal.Terminal.
"""
from ui.terminal import Terminal
from util.economy import trade
from world.items import item_name


class ShoreTerminal(Terminal):
    """A terminal ashore. Every one trades on the local market."""

    HELP = ("help", "info", *trade.TRADE_USAGE, "exit")

    def __init__(self, mode):
        super().__init__()
        self.mode = mode  # the PlanetaryMode this terminal stands in

    def deactivate(self):
        super().deactivate()
        self.mode.deactivate_terminal()

    def argument_candidates(self, verb):
        economy = getattr(self.mode, "economy", None)
        if verb not in ("buy", "sell") or economy is None:
            return []
        return [item_name(good) for good in economy.goods()]

    def trade(self, verb, argument):
        mode = self.mode
        return trade.handle(verb, argument, mode.player, mode.economy, mode.planet.planet_guild)

    def cmd_prices(self, argument):
        return self.trade("prices", argument)

    def cmd_buy(self, argument):
        return self.trade("buy", argument)

    def cmd_sell(self, argument):
        return self.trade("sell", argument)

    def cmd_cargo(self, argument):
        return self.trade("cargo", argument)

    def cmd_news(self, argument):
        return self.trade("news", argument)


class DockingTerminal(ShoreTerminal):
    terminal_type = "docking"
    HELP = ("help", "info", *trade.TRADE_USAGE, "refuel", "repair", "depart", "exit")

    def cmd_info(self, argument):
        return "Docking Terminal v1.0. Use this terminal for managing docking operations."

    def cmd_refuel(self, argument):
        return trade.refuel(self.mode.player, self.mode.economy)

    def cmd_repair(self, argument):
        return trade.repair(self.mode.player)

    def cmd_depart(self, argument):
        self.mode.return_to_star_system_mode()


class MarketTerminal(ShoreTerminal):
    terminal_type = "market"

    def cmd_info(self, argument):
        return f"{self.mode.planet.name} Exchange. Current prices for registered haulers."


TERMINALS = {terminal.terminal_type: terminal for terminal in (DockingTerminal, MarketTerminal)}
