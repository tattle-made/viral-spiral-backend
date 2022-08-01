import peewee

from .base import InGameModel


class Article(InGameModel):
    # TODO Use a list of keywords instead of text search
    content_lower = peewee.TextField()  # For easier querying
    content = peewee.TextField()
    is_fake = peewee.BooleanField()
