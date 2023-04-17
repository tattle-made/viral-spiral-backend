import unittest
from models import (
    Game,
    Player,
    Card,
    CardInstance,
    Score,
    FullRound,
    PlayerPower,
    utils,
    Article,
)


class TestEncyclopedia(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        print("setting up")

        # create_game
        for progress in Game.new(
            player_count=4,
            colors_filepath="config_jsons/example1/colors.json",
            topics_filepath="config_jsons/example1/topics.json",
            password="asdf",
            draw_fn_name="first",
            cards_filepath="config_jsons/example1/cards.json",
            encyclopedia_filepath="config_jsons/example1/articles.json",
        ):
            if progress["type"] == "message":
                print(progress["payload"])
            if progress["type"] == "result":
                cls.game = progress["payload"]

        # join_game
        playernames = ["adhiraj", "aman", "krys", "farah"]
        for name in playernames:
            player = cls.game.get_unclaimed_player(name)
            player.name = name
            Score.initialize(cls.game, player)
            player.save()

        cls.full_round = FullRound.create(game=cls.game)
        players = cls.game.player_set
        players = [player for player in players]
        ordered_players = sorted(players, key=lambda player: player.sequence)

        cls.current_player = ordered_players[0]
        cls.current_player.current = True
        cls.current_player.save()
        cls.game.update_powers()

    def test_search_bias_card(self):
        TGB = 2  # chosen just so we have enough cards to sample from
        game = TestEncyclopedia.game
        current_player = TestEncyclopedia.current_player

        card = (
            Card.select()
            .where(Card.game == game)
            .where(Card.original_player == None)
            .where(Card.bias_against != None)
            .where(Card.bias_against != current_player.color)
            .where(Card.tgb <= TGB)
            .first()
        )

        card_instance = card.draw(self.current_player)
        print(card_instance.card.description)
        article = self.current_player.action_encyclopedia_search(card_instance.card.id_)
        print(article)
        self.assertIn("title", article)
        self.assertIn("content", article)
        self.assertIn("type", article)
        self.assertIn("author", article)
        self.assertEqual(len(article.get("content")) > 0, True)

    def test_search_true_affinity_card(self):
        TGB = 2  # chosen just so we have enough cards to sample from
        game = TestEncyclopedia.game
        current_player = TestEncyclopedia.current_player

        card = (
            Card.select()
            .where(Card.game == game)
            .where(Card.original_player == None)
            .where(Card.affinity_towards != None)
            .where(Card.fake == False)
            .where(Card.tgb <= TGB)
            .first()
        )

        card_instance = card.draw(self.current_player)
        print(card_instance.card.description)
        article = self.current_player.action_encyclopedia_search(card_instance.card.id_)
        print(article)
        self.assertIn("title", article)
        self.assertIn("content", article)
        self.assertIn("type", article)
        self.assertIn("author", article)
        self.assertEqual(len(article.get("content")) > 0, True)

    def test_search_false_affinity_card(self):
        TGB = 2  # chosen just so we have enough cards to sample from
        game = TestEncyclopedia.game
        current_player = TestEncyclopedia.current_player

        card = (
            Card.select()
            .where(Card.game == game)
            .where(Card.original_player == None)
            .where(Card.affinity_towards != None)
            .where(Card.fake == True)
            .where(Card.faked_by == None)
            .where(Card.tgb <= TGB)
            .first()
        )

        card_instance = card.draw(self.current_player)
        print(card_instance.card.description)
        article = self.current_player.action_encyclopedia_search(card_instance.card.id_)
        print(article)
        self.assertIn("title", article)
        self.assertIn("content", article)
        self.assertIn("type", article)
        self.assertIn("author", article)
        self.assertEqual(len(article.get("content")) > 0, True)

    def test_search_true_topical_card(self):
        TGB = 2  # chosen just so we have enough cards to sample from
        game = TestEncyclopedia.game
        current_player = TestEncyclopedia.current_player

        card = (
            Card.select()
            .where(Card.game == game)
            .where(Card.original_player == None)
            .where(Card.affinity_towards == None)
            .where(Card.bias_against == None)
            .where(Card.fake == False)
            .where(Card.tgb <= TGB)
            .first()
        )

        card_instance = card.draw(self.current_player)
        print(card_instance.card.description)
        article = self.current_player.action_encyclopedia_search(card_instance.card.id_)
        print(article)
        self.assertIn("title", article)
        self.assertIn("content", article)
        self.assertIn("type", article)
        self.assertIn("author", article)
        self.assertEqual(len(article.get("content")) > 0, True)

    def test_search_false_topical_card(self):
        TGB = 2  # chosen just so we have enough cards to sample from
        game = TestEncyclopedia.game
        current_player = TestEncyclopedia.current_player

        card = (
            Card.select()
            .where(Card.game == game)
            .where(Card.original_player == None)
            .where(Card.affinity_towards == None)
            .where(Card.bias_against == None)
            .where(Card.fake == True)
            .where(Card.faked_by == None)
            .where(Card.tgb <= TGB)
            .first()
        )

        card_instance = card.draw(self.current_player)
        print(card_instance.card.description)
        article = self.current_player.action_encyclopedia_search(card_instance.card.id_)
        print(article)
        self.assertIn("title", article)
        self.assertIn("content", article)
        self.assertIn("type", article)
        self.assertIn("author", article)
        self.assertEqual(len(article.get("content")) > 0, True)

    @classmethod
    def tearDownClass(self) -> None:
        pass
        # delete_game


# Create Game

# Join Game

# Draw a fake card
# Search

# Draw

if __name__ == "__main__":
    unittest.main()
