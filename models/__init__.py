"""Easy imports for models"""
from .base import Game, Round, db
from .card import Card, CardInstance
from .player import Player, PlayerInitialBias, PlayerInitialAffinity
from .counters import AffinityTopic, Color
from .powers import PlayerPower, CancelStatus, CancelVote
from .card_queue import PlayerCardQueue
from .encyclopedia import Article

ALL_MODELS = [
    # This is the order in which the tables will be created
    Game,
    Round,
    AffinityTopic,
    Color,
    PlayerInitialBias,
    PlayerInitialAffinity,
    Player,
    PlayerPower,
    CancelStatus,
    CancelVote,
    Card,
    CardInstance,
    PlayerCardQueue,
]
