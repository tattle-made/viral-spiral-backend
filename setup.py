"""Sets up the DB etc"""

import sys
import peeweedbevolve
from models import db, ALL_MODELS


def init_db():
    # Create models
    db.evolve(ALL_MODELS)


if __name__ == "__main__":
    init_db()
