"""Easy imports for models"""
from .base import Game, Round, db
from .card import Card, CardInstance
from .player import Player, PlayerInitialBias, PlayerInitialAffinity
from .counters import AffinityTopic, Color
from .powers import PlayerPower, CancelStatus, CancelVote
from .card_queue import PlayerCardQueue

ALL_MODELS = [
    Game,
    Round,
    Card,
    CardInstance,
    Player,
    PlayerInitialBias,
    PlayerInitialAffinity,
    AffinityTopic,
    Color,
    PlayerPower,
    CancelStatus,
    CancelVote,
    PlayerCardQueue,
]
