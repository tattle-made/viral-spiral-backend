"""Sets up the DB etc"""

# Create the models
from models import db, ALL_MODELS

db.create_tables(ALL_MODELS)


def add_cards_from_json(filename):
    # TODO implement this
    raise NotImplementedError
