"""Sets up the DB etc"""

import sys
from models import db, ALL_MODELS


def init_db():
    # Create models
    db.create_tables(ALL_MODELS)


if __name__ == "__main__":
    init_db()
