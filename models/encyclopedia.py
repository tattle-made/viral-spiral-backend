import json

import peewee

from .base import InGameModel


class Article(InGameModel):
    title = peewee.TextField()
    content = peewee.TextField()
    type_ = peewee.CharField()
    author = peewee.CharField()
    fake_content = peewee.TextField()
    fake_type_ = peewee.CharField()
    fake_author = peewee.CharField()
    is_fake = peewee.BooleanField()

    @classmethod
    def import_from_json(cls, json_dict=None, json_path=None, defaults=None):
        """First creates the original cards, then the fakes"""
        from .card import Card

        if not json_dict:
            with open(json_path) as infile:
                json_dict = json.load(infile)

        game_id = defaults["game_id"]
        new_ = []
        for idx in range(len(json_dict)):
            dict_ = json_dict[idx]
            title = dict_["title"]
            card = (
                Card.select()
                .where(Card.game_id == game_id)
                .where(Card.title.iregexp(f".*{title.strip()}.*"))
                .first()
            )
            if not card:
                continue
            dict_["card_id"] = card.id_
            new_.append(dict)

        super().import_from_json(json_dict=new_, defaults=defaults)

    def render(self):
        """Returns either the true or fake article"""
        if self.is_fake and self.fake_content and self.fake_type_ and self.fake_author:
            return {
                "title": self.title,
                "content": self.fake_content,
                "type": self.fake_type_,
                "author": self.fake_author,
            }

        return {
            "title": self.title,
            "content": self.content,
            "type": self.type_,
            "author": self.author,
        }
