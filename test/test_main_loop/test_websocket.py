import json
from uuid import uuid4
from main_loop.websocket import create_game, run
from models import Game, Card

data = dict(
    game=uuid4().hex,
    players=["foo", "bar"],
    topics=["cats", "stocks"],
    colors=["red", "blue"],
    draw_fn_name="first",
    cards_filepath="x.json",
)

print(f"Data: {json.dumps(data, indent=2)}")


def test_without_sockets():

    runner = create_game(data)
    print("Created game", runner.game.id_)
    print("Running server")
    run()
    # game = Game.select().where(Game.name==data["game"]).first()
    # Card.import_from_json(json_path="x.json", defaults={"game_id": str(game.id_)})


if __name__ == "__main__":
    test_without_sockets()
    # Game.export_to_file(format="json", output_path="y.json")
