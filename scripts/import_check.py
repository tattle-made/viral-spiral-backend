"""To run after an import to verify the data"""

import unittest
import json
from uuid import uuid4
from models import Game, Article, Card
from models.utils import model_to_dict

class SanityCheck(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.game_name = None
        self.player_names = []
        super().__init__(*args, **kwargs)

    def setUp(self):
        """Creates a new game"""
        self.game_name = f"test_{uuid4().hex}"
        self.player_names = [
            "player1",
            "player2",
            "player3",
        ]
        game = Game.new(
            name=self.game_name,
            players=self.player_names,
            colors_filepath="config_jsons/example1/colors.json",
            topics_filepath="config_jsons/example1/topics.json",
            cards_filepath="config_jsons/example1/cards.json",
            encyclopedia_filepath="config_jsons/example1/articles.json",
        )
        self.game_name = game.name

    def test_card_article_link(self):
        """Tests the link between cards and articles"""
        failed = []
        game = Game.select().where(Game.name == self.game_name).first()
        cards = game.card_set.filter(Card.original == None)
        for card in cards:
            article = game.article_set.where(
                Article.title == card.description
            ).first()
            if not article:
                failed.append(model_to_dict(card))

        if failed:
            with open("failed.json", "w") as outfile:
                json.dump(failed, outfile, indent=2)

        self.assertEqual(len(failed), 0)

unittest.main()
