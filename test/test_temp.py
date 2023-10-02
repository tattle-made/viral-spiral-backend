from models import Game, Player, Card
import pprint
from deck_generators import first
pp = pprint.PrettyPrinter(indent=4)

game = Game.select().where(Game.id_=="376744ef254d473c92924da141dea26c").first()
yellow = [color for color in game.color_set if color.name=='yellow'][0]
adhiraj = Player.select().where(Player.id_=="5004a06159c74309bce76cf49a8340e9").first()

def test(tgb):
    pp.pprint(first.stat_deck(adhiraj, yellow, tgb))
    pp.pprint(first.distribution(first.stat_deck(adhiraj, yellow, tgb)))