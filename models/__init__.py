"""Easy imports for models"""
from .base import Game, db
from .card import Card, CardInstance
from .player import Player, PlayerInitialBias, PlayerInitialAffinity
from .counters import AffinityTopic, Color
from .powers import PlayerPower
from .card_queue import PlayerCardQueue

ALL_MODELS = [
    Game,
    Card,
    CardInstance,
    Player,
    PlayerInitialBias,
    PlayerInitialAffinity,
    AffinityTopic,
    Color,
    PlayerPower,
    PlayerCardQueue,
]
