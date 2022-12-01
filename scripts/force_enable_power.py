import os
import sys


from models.powers import VIRAL_SPIRAL, CANCEL, FAKE_NEWS
from models import Player, PlayerPower, Game


def set_power(game_id, player_name, power_name, active: bool):
    game = Game.select().where(Game.id_ == game_id).first()
    player = game.player_set.where(Player.name == player_name).first()
    PlayerPower.update(name=power_name, player=player, active=active)
    print("Done")


if __name__ == "__main__":
    game_id = os.getenv("game_id")
    player_name = os.getenv("player_name")
    power_name = os.getenv("power_name")
    active = os.getenv("active", "no") == "yes"

    args = [game_id, player_name, power_name, active]
    if None in args:
        print("Invalid env vars")
        print("Usage:")
        print(
            "game_id=<gameid> player_name=foo power_name=viral_spiral active=yes python"
            " scripts/force_enable_power.py"
        )
        sys.exit(1)

    set_power(*args)
