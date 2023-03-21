import peewee
from constants import (
    VIRAL_SPIRAL_AFFINITY_COUNT,
    VIRAL_SPIRAL_BIAS_COUNT,
    CANCELLING_AFFINITY_COUNT,
    FAKE_NEWS_BIAS_COUNT,
    SOCKET_EVENT_ENC_SEARCH_RESULT,
)
from .utils import model_to_dict
from .base import InGameModel, Round
from .encyclopedia import Article
from .counters import AffinityTopic, Color
from exceptions import NotAllowed, NotFound
from functools import lru_cache
from score import Score

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

    name = peewee.CharField(null=True)
    clout = peewee.IntegerField(default=0)
    score = peewee.ForeignKeyField(Score)
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
        indexes = (
            (("sequence", "game"), True),
            (("name", "game"), True),
        )

    @lru_cache
    def bias_cached(self, card_instances_count, against: Color):
        count = 0
        for card_instance in self.card_instances:
            # TODO use query
            if card_instance.card.bias_against == against:
                if card_instance.status == card_instance.STATUS_PASSED:
                    count += 1
        return count


    def bias(self, against: Color) -> int:
        """Returns the bias of this player against a given color"""
        return self.bias_cached(self.card_instances.count(), against)
    
    @lru_cache
    def affinity_cached(self, card_instances, towards: AffinityTopic):
        print(card_instances,towards)
        count = 0
        for card_instance in card_instances:
            # TODO use query
            if card_instance.card.affinity_towards == towards:
                if card_instance.status == card_instance.STATUS_PASSED:
                    count += card_instance.card.affinity_count
        return count

    def affinity(self, towards: AffinityTopic) -> int:
        """Returns the bias of this player against a given color"""
        return self.affinity_cached(card_instances=self.card_instances, towards=towards)

    def affinity_matches(self, with_, towards: AffinityTopic) -> bool:
        """Returns True if self's affinity matches with `with_`'s affinity"""
        return self.affinity(towards=towards) * with_.affinity(towards=towards) >= 1

    def bias_matches(self, with_, against: Color) -> bool:
        """Returns True if self's bias matches with `with_`'s bias"""
        return self.bias(against=against) * with_.bias(against=against) >= 1

    def all_affinities(self):
        return dict(
            [(topic.id_, self.affinity(topic)) for topic in self.game.affinitytopic_set]
        )

    def all_biases(self):
        return dict([(color.id_, self.bias(color)) for color in self.game.color_set])

    def card_instances_in_hand(self):
        """Retuns all card instances which the player is holding"""
        # TODO optimise this
        return [ci for ci in self.card_instances if ci.status == ci.STATUS_HOLDING]

    def event_receive_card(self, card_instance):
        """queue the card instance the UI prompts user to do something"""
        from .card import CardInstance
        from .card_queue import PlayerCardQueue

        PlayerCardQueue.queue(card_instance)

    def action_keep_card(self, card_instance_id: str, discard=False):
        """Remove this card from the queue"""
        from .card_queue import PlayerCardQueue
        from .card import CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()

        if discard:
            card_instance.discarded = True
            card_instance.save()

        PlayerCardQueue.dequeue(card_instance)

        # If this card's bias / affinity aligns with the player's bias / affinity,
        # deduct points
        bias_against = card_instance.card.bias_against
        if bias_against and self.bias(against=bias_against) >= 1:
            Player.update(clout=Player.clout - 1).where(
                Player.id_ == self.id_
            ).execute()

        affinity_towards = card_instance.card.affinity_towards
        affinity_count = card_instance.card.affinity_count
        if (
            affinity_towards
            and affinity_count in (-1, 1)
            and self.affinity(towards=affinity_towards) * affinity_count >= 1
        ):
            Player.update(clout=Player.clout - 1).where(
                Player.id_ == self.id_
            ).execute()

        return model_to_dict(card_instance)

    def action_discard_card(self, card_instance_id: str):
        """Remove this card from the queue and discard it"""
        return self.action_keep_card(card_instance_id, discard=True)

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
        Player.update(clout=Player.clout + 1).where(
            Player.id_ == card_instance.card.original_player_id
        ).execute()

        # If this is a biased card, decrease the score of all players of the
        # community against which this card is biased
        # This happens only for the first pass of this card
        if card_instance.card.bias_against is not None and card_instance.from_ is None:
            Player.update(clout=Player.clout - 1).where(
                Player.color == card_instance.card.bias_against
            )

        if card_instance.card.bias_against is not None:
            self.score.update(bias_count = Player.score.bias_count + 1).where(
                Player.score.bias_against == card_instance.card.bias_against
            )
        
        if card_instance.card.affinity_towards is not None:
            self.score.update(affinity_count = Player.score.affinity_count + card_instance.card.affinity_count).where(
                Player.score.affinity_towards == card_instance.card.affinity_towards
            )
            

        return {
            "passed_to": model_to_dict(to_player),
        }

    def action_viral_spiral(
        self,
        pass_card_instance_id: str,
        to: list,
        keep_card_instance_id: str = None,
    ):
        """Pass a card to all the players or a subset of the players.
        Can specify the player IDs in the `to` list"""
        from .powers import VIRAL_SPIRAL, PlayerPower
        from .card import CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == pass_card_instance_id
        ).first()

        if not self.current:
            raise NotAllowed("Can't perform special power if not drawn card")
        if not card_instance:
            raise NotFound("Card instance not found")
        if not PlayerPower.get_latest(name=VIRAL_SPIRAL, player=self).active:
            raise NotAllowed("Viral spiral power missing to pass to all")

        recipients = card_instance.allowed_recipients()
        if to:
            recipients = [rec for rec in recipients if rec.id_ in to]

        for player in recipients:
            self.action_pass_card(
                card_instance=card_instance,
                to_player=player,
                dequeue=False,
            )

        return {"passed_to": [model_to_dict(player) for player in recipients]}

        # Dequeue this card
        from .card_queue import PlayerCardQueue

        PlayerCardQueue.dequeue(card_instance)

        # Keep the other card
        if keep_card_instance_id:
            self.action_keep_card(keep_card_instance_id)

    def action_initiate_cancel(self, against: str, topic_id: str):
        """Initiates a round of voting to cancel a player.
        Provide the name of the player to cancel and the topic to use for casting votes.

        You may select any topic for which your affinity is +-3 or more"""
        from .powers import CancelStatus, CANCEL, PlayerPower

        if not self.current:
            raise NotAllowed("Can't perform special power if not drawn card")
        if not PlayerPower.get_latest(name=CANCEL, player=self).active:
            raise NotAllowed("Cancel power missing")

        if topic_id:
            topic = AffinityTopic.select().where(AffinityTopic.id_ == topic_id).first()
        if not topic:
            raise NotFound("No topic provided")

        if not self.has_initiate_cancel(topic=topic):
            raise NotAllowed("Cannot use this topic for initiating cancel")

        player = self.game.player_set.where(Player.id_ == against).first()
        if not player:
            raise NotFound(f"Player does not exist {against}")
        return model_to_dict(
            CancelStatus.initiate(initiator=self, against=player, topic=topic)
        )

    def action_vote_cancel(self, cancel_status_id, vote: bool = False):
        """Vote True/False to cancel a player"""
        from .powers import CancelVote

        CancelVote.update(vote=vote).where(CancelVote.voter == self).where(
            CancelVote.cancel_status_id == cancel_status_id
        ).execute()

    def action_fake_news(self, card_instance_id: str, fake_card_id: str):
        """Convert a card into fake news"""
        from .card import Card, CardInstance
        from .powers import PlayerPower, FAKE_NEWS

        if not self.current:
            raise NotAllowed("Can't perform special power if not drawn card")
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
        return model_to_dict(card_instance)

    def action_mark_as_fake(self, card_instance_id: str):
        """Mark a card as fake after fact checking"""
        from .card import Card, CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()
        if not card_instance:
            raise NotFound(f"Card instance not found {card_instance_id}")

        if card_instance.card.fake:
            # Deduct points of last player to share this card
            Player.update(score=Player.score - 1).where(
                Player.id_ == card_instance.from_.player.id
            ).execute()
        # Discard all instanes of this (fake) card going around
        from .card_queue import PlayerCardQueue

        self.action_discard_card(card_instance_id)
        PlayerCardQueue.mark_as_fake(card_instance.card)
        card_instance.card.discarded = True
        card_instance.card.save()

    def action_encyclopedia_search(self, card_id):
        """Returns this card's encyclopedia article"""
        from .card import Card

        card = Card.select().where(Card.id_ == card_id, Card.game == self.game).first()
        article = (
            Article.select()
            .where(Article.title == card.description, Article.game == card.game)
            .first()
        )
        # article = card.encyclopedia_article
        if article:
            return article.render()
        return {}

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
        from .powers import VIRAL_SPIRAL, FAKE_NEWS, CANCEL, PlayerPower, CancelVote
        from .card import CardInstance

        allowed_actions = [
            "keep_card",
            "discard_card",
            "mark_as_fake",
            "encyclopedia_search",
        ]

        # Pass card
        if card_instance.allowed_recipients():
            allowed_actions.append("pass_card")

        # Special powers. Allow only if this player is the drawing player
        if self.current:
            # Viral Spiral
            if PlayerPower.get_latest(name=VIRAL_SPIRAL, player=self).active:
                allowed_actions.append("viral_spiral")

            # Initiate Cancel
            if PlayerPower.get_latest(name=CANCEL, player=self).active:
                allowed_actions.append("initiate_cancel")

            # Fake news
            if PlayerPower.get_latest(name=FAKE_NEWS, player=self).active:
                allowed_actions.append("fake_news")

        # Vote cancel
        if (
            CancelVote.pending_votes(round_=self.game.current_round)
            .where(CancelVote.voter == self)
            .exists()
        ):
            allowed_actions.append("vote_cancel")

        return allowed_actions

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

    def valid_topics_for_cancel(self):
        """Returns a list of topics this player can use to initiate cancel"""
        return [
            topic
            for topic in self.game.affinitytopic_set
            if abs(self.affinity(towards=topic)) >= CANCELLING_AFFINITY_COUNT
        ]

    def has_initiate_cancel(self, topic: AffinityTopic = None):
        """Checks whether this player can initate a cancel vote round using members of `topic` to case the vote.
        If topic is not provided, this will check whether this player can use ANY topic to initiate cancel
        """
        if topic:
            return topic in self.valid_topics_for_cancel()
        else:
            return bool(self.valid_topics_for_cancel())

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
        has_cancel = self.has_initiate_cancel()
        PlayerPower.update(name=CANCEL, player=self, active=has_cancel)

        # Fake News
        has_fake_news = False
        for color in self.game.color_set:
            if abs(self.bias(against=color)) >= FAKE_NEWS_BIAS_COUNT:
                has_fake_news = True
                break
        PlayerPower.update(name=FAKE_NEWS, player=self, active=has_fake_news)
