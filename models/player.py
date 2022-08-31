import peewee
from constants import (
    VIRAL_SPIRAL_AFFINITY_COUNT,
    VIRAL_SPIRAL_BIAS_COUNT,
    CANCELLING_AFFINITY_COUNT,
    FAKE_NEWS_BIAS_COUNT,
    SOCKET_EVENT_ENC_SEARCH_RESULT,
)
from .base import InGameModel, Round
from .encyclopedia import Article
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

    def card_instances_in_hand(self):
        """Retuns all card instances which the player is holding"""
        # TODO optimise this
        return [ci for ci in self.card_instances if ci.status == ci.STATUS_HOLDING]

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

    def action_pass_card(
        self,
        # Either pass card instance ID and player name (to)
        card_instance_id: str = None,
        to: str = None,
        # Or pass card instance object and player object
        card_instance=None,
        to_player=None,
        dequeue=True,
    ):
        """Can either pass the card to a player or to all players

        Pass either one of card_instance or card_instance_id
        Pass either one of to_player (type: Player) or
            to (type: Player Name (str))

        If you want to pass this to multiple players, pass `dequeue` = False
        and then dequeue the card manually
        """
        # TODO check if this card can be passed
        from .card import CardInstance

        if not card_instance:
            card_instance = self.card_instances.where(
                CardInstance.id_ == card_instance_id
            ).first()
            if not card_instance:
                raise NotFound("Card instance not found")

        if not to_player:
            to_player = self.game.player_set.where(Player.name == to).first()
            if not to_player:
                raise NotFound("Player not found")

        # Trigger the receive card events
        # Will raise an exception if cannot create
        to_card_instance = CardInstance.create(
            card=card_instance.card,
            from_=card_instance,
            player=to_player,
            game=self.game,
        )
        to_player.event_receive_card(to_card_instance)

        # Dequeue this card
        if dequeue:
            from .card_queue import PlayerCardQueue

            PlayerCardQueue.dequeue(card_instance)

        # Increase the original player's score
        Player.update(score=Player.score + 1).where(
            Player.id_ == card_instance.card.original_player_id
        ).execute()

        # If this is a biased card, decrease the score of all players of the
        # community against which this card is biased
        # This happens only for the first pass of this card
        if card_instance.card.bias_against is not None and card_instance.from_ is None:
            Player.update(score=Player.score - 1).where(
                Player.color == card_instance.card.bias_against
            )

    def action_viral_spiral(
        self, keep_card_instance_id: str, pass_card_instance_id: str
    ):
        """Pass a card to all the players"""
        from .powers import VIRAL_SPIRAL, PlayerPower
        from .card import CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == pass_card_instance_id
        ).first()

        if not card_instance:
            raise NotFound("Card instance not found")
        if not PlayerPower.get_latest(name=VIRAL_SPIRAL, player=self).active:
            raise NotAllowed("Viral spiral power missing to pass to all")

        for player in card_instance.allowed_recipients():
            self.action_pass_card(
                card_instance=card_instance,
                to_player=player,
                dequeue=False,
            )

        # Dequeue this card
        from .card_queue import PlayerCardQueue

        PlayerCardQueue.dequeue(card_instance)

        # Keep the other card
        if keep_card_instance_id:
            self.action_keep_card(keep_card_instance_id)

    def action_initiate_cancel(self, against: str = None):
        """Initiates a round of voting to cancel a player.
        Provide the name of the player to cancel"""
        from .powers import CancelStatus, CANCEL, PlayerPower

        if not PlayerPower.get_latest(name=CANCEL, player=self).active:
            raise NotAllowed("Cancel power missing")

        player = self.game.player_set.where(Player.name == against).first()
        if not player:
            raise NotFound("Player does not exist {against}")
        CancelStatus.initiate(initiator=self, against=player)

    def action_vote_cancel(self, cancel_status_id, vote: bool = False):
        """Vote True/False to cancel a player"""
        from .powers import CancelVote

        CancelVote.select().where(
            CancelVote.cancel_status_id == cancel_status_id
        ).update(vote=vote)

    def action_fake_news(self, card_instance_id: str, fake_card_id: str):
        """Convert a card into fake news"""
        from .card import Card, CardInstance
        from .powers import PlayerPower, FAKE_NEWS

        if not PlayerPower.get_latest(name=FAKE_NEWS, player=self).active:
            raise NotAllowed("Fake news power missing")

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()
        if not card_instance:
            raise NotFound(f"Card instance not found {card_instance_id}")

        fake_card = card_instance.card.fakes.where(Card.id_ == fake_card_id).first()
        if not fake_card:
            raise NotFound(f"Fake card not found {fake_card_id}")

        card_instance.create_fake_news(fake=fake_card)

    def action_mark_as_fake(self, card_instance_id: str):
        """Mark a card as fake after fact checking"""
        from .card import Card, CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()
        if not card_instance:
            raise NotFound(f"Card instance not found {card_instance_id}")

        if card_instance.card.fake:
            # 1. Deduct points of last player to share this card
            Player.update(score=Player.score - 1).where(
                Player.id_ == card_instance.from_.player.id
            ).execute()
            # 2. Discard all instanes of this (fake) card going around
            from .card_queue import PlayerCardQueue

            PlayerCardQueue.discard_card(card_instance.card)
            card_instance.discarded = True
            card_instance.save()
            card_instance.card.discarded = True
            card_instance.card.save()

    def action_encyclopedia_search(self, keyword):
        """Searches for a keyword in the encyclopedia and returns relevant
        articles"""

        articles = Article.select(Article.id_, Article.content).where(
            Article.content_lower.contains(keyword.lower())
        )
        self.game.runner.send_to_player(
            player=self,
            data={
                "keyword": keyword,
                "articles": articles.dicts(),
            },
            event=SOCKET_EVENT_ENC_SEARCH_RESULT,
        )

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

    def get_pending_cancel_vote(self):
        """Returns the oldest pending vote (for cancellation) for this player"""
        from .powers import CancelVote

        return (
            CancelVote.pending_votes(round_=self.game.current_round)
            .where(CancelVote.voter == self)
            .first()
        )

    def perform_action(self, action: str, **kwargs):
        """Takes a string `action` which is the name of the function to
        trigger, for example `action_keep_card`

        kwargs is passed onto the action function"""
        assert action.startswith("action")
        return getattr(self, action)(**kwargs)

    def update_powers(self):
        """Updates the powers of this player"""
        from .powers import VIRAL_SPIRAL, CANCEL, FAKE_NEWS, PlayerPower

        # TODO Optimise this to reuse the computations across powers

        # Viral Spiral
        viral_spiral_affinity_check = False
        viral_spiral_bias_check = False
        for topic in self.game.affinitytopic_set:
            if abs(self.affinity(towards=topic)) >= VIRAL_SPIRAL_AFFINITY_COUNT:
                viral_spiral_affinity_check = True
                break
        for color in self.game.color_set:
            if abs(self.bias(against=color)) >= VIRAL_SPIRAL_BIAS_COUNT:
                viral_spiral_bias_check = True
                break
        has_viral_spiral = viral_spiral_affinity_check and viral_spiral_bias_check
        PlayerPower.update(name=VIRAL_SPIRAL, player=self, active=has_viral_spiral)

        # Cancel
        has_cancel = False
        for topic in self.game.affinitytopic_set:
            if abs(self.affinity(towards=topic)) >= CANCELLING_AFFINITY_COUNT:
                has_cancel = True
                break
        PlayerPower.update(name=CANCEL, player=self, active=has_cancel)

        # Fake News
        has_fake_news = False
        for color in self.game.color_set:
            if abs(self.bias(against=color)) >= FAKE_NEWS_BIAS_COUNT:
                has_fake_news = True
                break
        PlayerPower.update(name=FAKE_NEWS, player=self, active=has_fake_news)
