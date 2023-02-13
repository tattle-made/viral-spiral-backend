"""All models related to cards"""
import json
import peewee
from playhouse.shortcuts import model_to_dict as mtd_original
from .base import InGameModel
from .player import Player
from .encyclopedia import Article
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
    fake = peewee.BooleanField(default=False)
    original = peewee.ForeignKeyField("self", backref="fakes", null=True)
    faked_by = peewee.ForeignKeyField(Player, null=True)

    # If this card has been fact checked and (accurately) marked as false, it
    # will be discarded.
    discarded = peewee.BooleanField(default=False)

    # # IntegerField to denote whether this card is the currently active card in
    # # a round or not. If this is 0, it means it is the active card
    # _is_current_int = peewee.IntegerField(unique=True, default=-1)

    # Total game bias. This might be used as a condition for whether this card is
    # to be drawn or not in generator functions
    tgb = peewee.IntegerField(null=True)

    # def is_active(self):
    #     return self._is_current_int == 0

    # @classmethod
    # def get_active_card(cls, cards):
    #     """cards should be a query selector"""
    #     return cards.where(cls._is_current_int == 0).first()

    storyline = peewee.CharField(default="none")
    storyline_index = peewee.IntegerField(default=0)

    encyclopedia_article = peewee.ForeignKeyField(
        Article, null=True, unique=False, backref="cards"
    )

    def to_dict(self, **kwargs):
        """Calls peewee's model_to_dict and passes kwargs to it"""
        dict_ = mtd_original(self, **kwargs)
        fakes = [fake.to_dict() for fake in self.fakes]
        dict_["fakes"] = fakes
        return dict_

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
    def create_from_dict(cls, dict_, defaults=None):
        defaults = defaults or {}
        fakes = dict_.pop("fakes", [])
        affinity_towards = dict_.pop("affinity_towards", None)
        bias_against = dict_.pop("bias_against", None)
        dict_.update(defaults)
        if not dict_.get("description"):
            return
        created = cls.create(**dict_)
        if affinity_towards:
            try:
                topic = AffinityTopic.get(name=affinity_towards, **defaults)
            except AffinityTopic.DoesNotExist:
                # Skip this card
                return
            created.affinity_towards_id = topic.id_
        if bias_against:
            color, _ = Color.get_or_create(name=bias_against, **defaults)
            created.bias_against_id = color.id_
        created.save()
        for fake in fakes:
            fake["original_id"] = created.id_
            cls.create_from_dict(fake, defaults)

    @classmethod
    def import_from_json(cls, json_dict=None, json_path=None, defaults=None):
        """First creates the original cards, then the fakes"""
        if not json_dict:
            with open(json_path) as infile:
                json_dict = json.load(infile)
        for dict_ in json_dict:
            cls.create_from_dict(dict_, defaults=defaults)


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

    def to_dict(self, **kwargs):
        dict_ = mtd_original(self, **kwargs)
        dict_["status"] = self.status
        dict_["card"] = self.card.to_dict()
        return dict_

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

        return self.game.player_set.where(~Player.id_.in_(completed_player_ids))
