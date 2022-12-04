import peewee

from .base import InGameModel


class Article(InGameModel):
    content_lower = peewee.TextField()  # For easier querying
    content = peewee.TextField()
    headline = peewee.TextField()
    is_fake = peewee.BooleanField()
