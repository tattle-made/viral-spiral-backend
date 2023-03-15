"""
Keeps all game related scores in one table.
includes player's affinities and biases.
The table's schema was chosen keeping in mind that the affinity and bias count 
might change, so we've adopted this instead of a table with fixed columns.
"""
from .base import InGameModel
from .player import Player
from .counters import Color, AffinityTopic
import peewee

class Score(InGameModel):
    player = peewee.ForeignKeyField(Player, null=True)
    affinity_towards = peewee.ForeignKeyField(AffinityTopic, null=True)
    affinity_count = peewee.IntegerField(default=0)
    bias_against = peewee.ForeignKeyField(Color, null=True)
    bias_count = peewee.IntegerField(default=0)
    clout = peewee.IntegerField(default=0)

    def update_bias(self, color:Color, inc: int):
        (self.update({Score.bias_count: Score.bias_count+inc})
        .where(Score.bias_against==color)
        .execute())


    def update_affinity(self, affinity:AffinityTopic, inc: int):
        (self.update({Score.affinity_count: Score.affinity_count+inc})
        .where(Score.affinity_towards==affinity)
        .execute())