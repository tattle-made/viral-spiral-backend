import peewee
from constants import (
    VIRAL_SPIRAL_AFFINITY_COUNT,
    VIRAL_SPIRAL_BIAS_COUNT,
    CANCELLING_AFFINITY_COUNT,
    FAKE_NEWS_BIAS_COUNT,
    SOCKET_EVENT_ENC_SEARCH_RESULT,
)
from .utils import model_to_dict
from .base import InGameModel, Round, Game
from .counters import AffinityTopic, Color
from exceptions import NotAllowed, NotFound
from functools import lru_cache
from enum import Enum


class ScoreType(Enum):
    CLOUT = "clout"
    AFFINITY = "affinity"
    BIAS = "bias"


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

    def bias(self, against: Color) -> int:
        """Returns the bias of this player against a given color"""
        return Score.bias(self.score_set, against)

    def affinity(self, towards: AffinityTopic) -> int:
        """Returns the bias of this player against a given color"""
        return Score.affinity(self.score_set, towards)

    def affinity_matches(self, with_, towards: AffinityTopic) -> bool:
        """Returns True if self's affinity matches with `with_`'s affinity
        As an example, if player affinities for cats are as follows :
            P1 = +3, P2 = +1, P3 = -1, P4 = 0
            P1's affinity matches with P2 but not with P3 and P4
        and if the player affinities for cats are as follows :
            P1 = -4, P2 = -1, P3 = +1, P4 = 0
            P1's affinity matches with P2 but not P3 and P4
        """
        return self.affinity(towards=towards) * with_.affinity(towards=towards) >= 1

    def bias_matches(self, with_, against: Color) -> bool:
        """Returns True if self's bias matches with `with_`'s bias"""
        return self.bias(against=against) * with_.bias(against=against) >= 1

    def all_affinities(self):
        return Score.all_affinities(self.score_set)

    def all_biases(self):
        return Score.all_biases(self.score_set)

    def card_instances_in_hand(self):
        """Retuns all card instances which the player is holding"""
        # TODO optimise this
        return [ci for ci in self.card_instances if ci.status == ci.STATUS_HOLDING]

    def event_receive_card(self, card_instance):
        """queue the card instance the UI prompts user to do something"""
        from .card import CardInstance
        from .card_queue import PlayerCardQueue

        PlayerCardQueue.queue(card_instance)

    def clout(self):
        return Score.clout(self.score_set)

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
            original_player = Player.select().where(Player.id_ == self.id_).first()
            Score.inc_clout(original_player, -1)

        affinity_towards = card_instance.card.affinity_towards
        affinity_count = card_instance.card.affinity_count
        if (
            affinity_towards
            and affinity_count in (-1, 1)
            and self.affinity(towards=affinity_towards) * affinity_count >= 1
        ):
            original_player = Player.select().where(Player.id_ == self.id_).first()
            Score.inc_clout(original_player, -1)

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
        original_player = (
            Player.select()
            .where(Player.id_ == card_instance.card.original_player_id)
            .first()
        )
        Score.inc_clout(original_player, 1)

        # If this is a biased card, decrease the score of all players of the
        # community against which this card is biased
        # This happens only for the first pass of this card
        if card_instance.card.bias_against is not None and card_instance.from_ is None:
            for player in self.game.player_set:
                if player.color == card_instance.card.bias_against and player != self:
                    Score.inc_clout(player, -1)

        card_bias = card_instance.card.bias_against
        if card_bias is not None:
            Score.inc_bias(self, card_bias, 1)

        card_affinity = card_instance.card.affinity_towards
        card_affinity_count = card_instance.card.affinity_count
        if card_affinity is not None:
            Score.inc_affinity(self, card_affinity, card_affinity_count)

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
        from .powers import CancelVote, CancelStatus

        CancelVote.update(vote=vote).where(CancelVote.voter == self).where(
            CancelVote.cancel_status_id == cancel_status_id
        ).execute()

        CancelStatus.set_final_status(cancel_status_id)

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
            player = (
                Player.select()
                .where(Player.id_ == card_instance.from_.player.id_)
                .first()
            )
            if player:
                Score.inc_clout(player, -1)
            else:
                pass 
                
        else: 
            # Deduct point of the player who marked the card fake incorrectly
            player = (
                Player.select()
                .where(Player.id_ == card_instance.player_id)
                .first()
            )
            if player:
                Score.inc_clout(player, -1)
        

        # Discard all instanes of this (fake) card going around WITHOUT affecting the SCORE
        from .card_queue import PlayerCardQueue
        from .card import CardInstance

        card_instance = self.card_instances.where(
            CardInstance.id_ == card_instance_id
        ).first()

        card_instance.discarded = True
        card_instance.save()

        PlayerCardQueue.dequeue(card_instance)
        PlayerCardQueue.mark_as_fake(card_instance.card)
        card_instance.card.discarded = True
        card_instance.card.save()
        return model_to_dict(card_instance)

    def action_encyclopedia_search(self, card_id):
        """Returns this card's encyclopedia article"""
        from .card import Card
        from .encyclopedia import Article

        card = Card.select().where(Card.id_ == card_id, Card.game == self.game).first()
        if not card:
            raise Exception("Encyclopedia Search : Card Not Found")
        if card.fake:
            if card.original:
                article = card.original.encyclopedia_article.first()
            else:
                article = card.encyclopedia_article.first()
        else:
            article = card.encyclopedia_article.first()
        if article:
            return article.render(fake=card.fake)
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
        ) and CANCELLING_AFFINITY_COUNT:
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


"""
Keeps all game related scores in one table.
includes player's affinities, biases and clout.

Each row represents a type of score for a player in a game -
the player's clout, or their affinity towards a topic or their bias against a color

The table's schema was chosen keeping in mind that the affinity and bias count 
might change, so we've adopted this instead of a table with large but fixed columns.

"""


class Score(InGameModel):
    player = peewee.ForeignKeyField(Player, null=True)

    # Tells you which type of score this is. The subsequent fields `target` and `value`
    # need to be treated accordingly. Possible values are clout, affinity or bias.
    # I would have preferred to use an enum but peewee implementation for Enum seemed non trivial
    type = peewee.FixedCharField(max_length=10)
    target = peewee.CharField(max_length=32, null=True)
    value = peewee.IntegerField()

    @classmethod
    def initialize(cls, game: Game, player: Player):
        Score.create(game=game, player=player, type=ScoreType.CLOUT.value)
        for affinity in game.affinitytopic_set:
            Score.create(
                game=game,
                player=player,
                type=ScoreType.AFFINITY.value,
                target=affinity.id_,
            )
        for bias in game.color_set:
            if bias != player.color:
                Score.create(
                    game=game, player=player, type=ScoreType.BIAS.value, target=bias.id_
                )

    @classmethod
    def inc_bias(cls, player: Player, color: Color, inc: int):
        (
            Score.update({Score.value: Score.value + inc})
            .where(Score.game == player.game)
            .where(Score.player == player)
            .where(Score.target == color.id_)
            .where(Score.type == ScoreType.BIAS.value)
            .execute()
        )

    @classmethod
    def inc_affinity(cls, player: Player, affinity: AffinityTopic, inc: int):
        (
            Score.update({Score.value: Score.value + inc})
            .where(Score.game == player.game)
            .where(Score.player == player)
            .where(Score.target == affinity.id_)
            .where(Score.type == ScoreType.AFFINITY.value)
            .execute()
        )

    @classmethod
    def inc_clout(cls, player: Player, inc: int):
        clout = Score.clout(player.score_set)
        new_clout = 0 if clout + inc < 0 else clout + inc
        (
            Score.update({Score.value: new_clout})
            .where(Score.game == player.game)
            .where(Score.player == player)
            .where(Score.type == ScoreType.CLOUT.value)
            .execute()
        )

    """
        A helper method to format scores in a way thats backwards compatible
        with what the client expects 
    """

    @classmethod
    def all_scores_for_client(cls, scores: peewee.ModelSelect):
        all_scores = {"score": 0, "biases": {}, "affinities": {}}
        for score in scores:
            if score.type == ScoreType.CLOUT.value:
                all_scores["score"] = score.value
            elif score.type == ScoreType.BIAS.value:
                all_scores["biases"][score.target] = score.value
            elif score.type == ScoreType.AFFINITY.value:
                all_scores["affinities"][score.target] = score.value
        return all_scores

    @classmethod
    def all_biases(cls, scores: peewee.ModelSelect):
        all_biases = {}
        for score in scores:
            if score.type == ScoreType.BIAS.value:
                all_biases[score.target] = score.value
        return all_biases

    @classmethod
    def all_affinities(cls, scores: peewee.ModelSelect):
        all_affinities = {}
        for score in scores:
            if score.type == ScoreType.AFFINITY.value:
                all_affinities[score.target] = score.value
        return all_affinities

    @classmethod
    def bias(cls, scores: peewee.ModelSelect, color: Color):
        for score in scores:
            if score.type == ScoreType.BIAS.value and score.target == color.id_:
                return score.value
        return 0

    @classmethod
    def affinity(cls, scores: peewee.ModelSelect, affinity: AffinityTopic):
        for score in scores:
            if score.type == ScoreType.AFFINITY.value and score.target == affinity.id_:
                return score.value
        return 0

    @classmethod
    def clout(cls, scores: peewee.ModelSelect):
        for score in scores:
            if score.type == ScoreType.CLOUT.value:
                return score.value
        return 0
