import peewee
from .base import InGameModel


class AffinityTopic(InGameModel):
    """A topic for affinity"""

    name = peewee.CharField(unique=True)


class Color(InGameModel):
    """A color representing a community in the game"""

    name = peewee.CharField(unique=True)
