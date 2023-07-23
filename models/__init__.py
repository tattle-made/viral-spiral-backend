"""Easy imports for models"""
from .base import Game, Round, FullRound, db
from .card import Card, CardInstance
from .player import Player, PlayerInitialBias, PlayerInitialAffinity, Score
from .counters import AffinityTopic, Color
from .powers import PlayerPower, CancelStatus, CancelVote
from .card_queue import PlayerCardQueue
from .encyclopedia import Article
from .playerhand import PlayerHand

ALL_MODELS = [
    # This is the order in which the tables will be created
    Game,
    Round,
    FullRound,
    AffinityTopic,
    Color,
    PlayerInitialBias,
    PlayerInitialAffinity,
    Player,
    Score,
    PlayerPower,
    CancelStatus,
    CancelVote,
    Card,
    CardInstance,
    PlayerCardQueue,
    PlayerHand,
]
