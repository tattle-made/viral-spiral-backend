"""All models related to cards"""
import json
import peewee
from .base import InGameModel
from .player import Player
from .counters import AffinityTopic, Color


class Card(InGameModel):
    """Represents a card in the game"""

    title = peewee.CharField()
    description = peewee.TextField()
    affinity_towards = peewee.ForeignKeyField(AffinityTopic, null=True)
    affinity_count = peewee.IntegerField(null=True)  # Can be +1 or -1

    bias_against = peewee.ForeignKeyField(Color, null=True)

    bias_history = peewee.ManyToManyField(Color)

    original_player = peewee.ForeignKeyField(Player, null=True)

    # Cards used for fake news will have fake = True. These are basically
    # replicas of the original cards with some fields slightly changed. As of
    # now I am planning to keep an exhaustive copy of all possible fake cards
    # for every single card. Later on, we can move to a card faking function -
    # which can calculate the new bias / affinity based on the chang ein the
    # details
    # By default, these cards are unused and will have faked_by = None.
    # If a player chooses to fake a card, then their player object will come in
    # the faked_by foreign key
    # Each fake news card can have an "original" card - linked in the original
    # field. All fake news cards with the same original card form a pool - and
    # ideally the user can select between any of these.
    fake = peewee.BooleanField()
    original = peewee.ForeignKeyField("self", backref="fakes")
    faked_by = peewee.ForeignKeyField(Player)

    # If this card has been fact checked and (accurately) marked as false, it
    # will be discarded.
    discarded = peewee.BooleanField(default=False)

    # # IntegerField to denote whether this card is the currently active card in
    # # a round or not. If this is 0, it means it is the active card
    # _is_current_int = peewee.IntegerField(unique=True, default=-1)

    # def is_active(self):
    #     return self._is_current_int == 0

    # @classmethod
    # def get_active_card(cls, cards):
    #     """cards should be a query selector"""
    #     return cards.where(cls._is_current_int == 0).first()

    def add_bias(self, against: Color):
        """Adds a bias to this card"""
        if self.bias_against:
            self.bias_history.add(self.bias_against)
        self.bias_against = against
        self.save()

    def draw(self, player: Player):
        """Creates and returns a card instance. Does not affect the player
        score"""
        card_instance = CardInstance.create(
            card=self,
            from_=None,
            player=player,
            game=self.game,
        )
        self.original_player = player
        self.save()
        player.event_receive_card(card_instance)
        return card_instance

    @classmethod
    def import_from_json(cls, json_dict=None, json_path=None, defaults=None):
        """First creates the original cards, then the fakes"""
        if not json_dict:
            with open(json_path) as infile:
                json_dict = json.load(infile)
        fake_map = []
        for obj in json_dict:
            if fakes := obj.pop("fakes"):
                fake_map.append(fakes)
            else:
                fake_map.append(None)
        created_objs = super().import_from_json(json_dict=json_dict, defaults=defaults)
        for i, obj in enumerate(created_objs):
            if fakes := fake_map[i]:
                for fake in fakes:
                    fake["original_id"] = obj.id_
                super().import_from_json(json_dict=fakes, defaults=defaults)


class CardInstance(InGameModel):
    """Stores as instance of a passed / drawn card.

    If the card is drawn, from_ will be null.

    Else, from_ will be a reference to a passed card

    to_ will be the player that this card has gone to
    """

    STATUS_PASSED = "passed"
    STATUS_HOLDING = "holding"

    card = peewee.ForeignKeyField(Card)
    from_ = peewee.ForeignKeyField("self", null=True, unique=False, backref="to_")
    player = peewee.ForeignKeyField(
        Player, null=False, unique=False, backref="card_instances"
    )
    discarded = peewee.BooleanField(default=False)

    class Meta:
        # Unique together
        indexes = ((("card", "player", "game"), True),)

    @property
    def status(self):
        """Status of this card instance - can be "passed" or "holding" """
        if self.to_:
            return self.STATUS_PASSED
        else:
            return self.STATUS_HOLDING

    def create_fake_news(self, fake: Card):
        """Changes the details of the card"""
        assert fake in self.card.fakes
        self.card = fake
        self.card.faked_by = self.player
        self.card.save()
        self.save()

    def allowed_recipients(self):
        """Returns a list of players to whom this card can be passed"""
        # TODO optimise
        # Can select only certain fields
        card_instances = CardInstance.select(CardInstance.player_id).where(
            CardInstance.card == self.card
        )
        completed_player_ids = [ci.player_id for ci in card_instances]
        select_args = []
        return self.game.player_set - Player.select().where(
            Player.id_.in_(completed_player_ids)
        )
