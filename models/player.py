import peewee
from .base import InGameModel
from .counters import AffinityTopic, Color
from exceptions import NotAllowed, NotFound


class PlayerInitialBias(InGameModel):
    """Stores the initial bias of a player"""

    count = peewee.IntegerField(default=0)
    against = peewee.ForeignKeyField(Color)


class PlayerInitialAffinity(InGameModel):
    """Stores the initial affinity of a player"""

    count = peewee.IntegerField()
    towards = peewee.ForeignKeyField(Color)


class Player(InGameModel):
    """A player in the game"""

    name = peewee.CharField()
    score = peewee.IntegerField(default=0)
    color = peewee.ForeignKeyField(Color)
    initial_bias = peewee.ForeignKeyField(
        PlayerInitialBias, backref="player", unique=True, null=True
    )
    initial_affinity = peewee.ForeignKeyField(
        PlayerInitialAffinity, backref="player", unique=True, null=True
    )
    sequence = peewee.IntegerField(null=False, default=1)

    client_id = peewee.CharField(null=True)
    current = peewee.BooleanField(default=False)

    class Meta:
        # Unique together
        indexes = ((("sequence", "game"), True),)

    def bias(self, against: Color) -> int:
        """Returns the bias of this player against a given color"""
        # TODO optimise
        count = 0
        for card_instance in self.card_instances:
            # TODO use query
            if card_instance.card.bias_against == against:
                if card_instance.status == card_instance.STATUS_PASSED:
                    count += 1
        if self.initial_bias and self.initial_bias.against == against:
            count += self.initial_bias.count
        return count

    def affinity(self, towards: AffinityTopic) -> int:
        """Returns the bias of this player against a given color"""
        # TODO optimise
        count = 0
        for card_instance in self.card_instances:
            # TODO use query
            if card_instance.card.affinity_towards == towards:
                if card_instance.status == card_instance.STATUS_PASSED:
                    count += card_instance.card.affinity_count
        if self.initial_affinity and self.initial_affinity.towards == towards:
            count += self.initial_affinity.count
        return count

    def event_receive_card(self, card_instance):
        """queue the card instance the UI prompts user to do something"""
        from .card import CardInstance
        from .card_queue import PlayerCardQueue

        PlayerCardQueue.queue(card_instance)

    def action_keep_card(self, card_instance_id: str):
        """Remove this card from the queue"""
        # TODO check if this action is allowed
        from .card_queue import PlayerCardQueue
        from .card import CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()

        PlayerCardQueue.dequeue(card_instance)

    def action_pass_card(self, card_instance_id: str, to: str):
        """Can either pass the card to a player or to all players

        `to` can be "all" or a player's name"""
        # TODO check if this card can be passed
        from .powers import VIRAL_SPIRAL
        from .card import CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()

        if to == "all":
            if self.powers.where(self.__class__.name == VIRAL_SPIRAL).count() == 1:
                to_players = self.__class__.select()
            else:
                raise NotAllowed("Viral spiral power missing to pass to all")
        else:
            player = self.game.player_set.where(Player.name == to)
            if player.count() > 0:
                player = player.first()
            if not player:
                raise NotFound("Player not found")
            to_players = [player]

        # Increase the original player's score
        Player.update(score=Player.score + 1).where(
            Player.id_ == card_instance.card.original_player_id
        ).execute()

        # Trigger the receive card events
        for player in to_players:
            to_card_instance = CardInstance.create(
                card=card_instance.card,
                from_=card_instance,
                player=player,
                game=self.game,
            )
            player.event_receive_card(to_card_instance)

        # Dequeue this card
        from .card_queue import PlayerCardQueue

        PlayerCardQueue.dequeue(card_instance)

    def all_actions(self):
        """Utility function to return all possible actions"""
        return [
            fn
            for fn in dir(self)
            if callable(getattr(self, fn)) and fn.startswith("action_")
        ]

    def allowed_actions(self, card_instance):
        """Returns list of actions allowed for this user given a card instance
        received by them"""
        # TODO Write this
        return self.all_actions()

    def get_queued_card_instance(self):
        """Returns the oldest card instance queued. Returns None if no cards
        are queued"""
        from .card_queue import PlayerCardQueue

        query = self.card_queue_items.where(PlayerCardQueue.active == True)

        oldest = query.order_by(PlayerCardQueue.idx).first()
        if oldest:
            return oldest.card_instance

    def perform_action(self, action: str, **kwargs):
        """Takes a string `action` which is the name of the function to
        trigger, for example `action_keep_card`

        kwargs is passed onto the action function"""
        assert action.startswith("action")
        return getattr(self, action)(**kwargs)
