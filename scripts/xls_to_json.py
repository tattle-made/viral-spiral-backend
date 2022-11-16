"""Converts a given XL sheet into a JSON file

The JSON objects can then be used to import data into the Database
"""

import copy
import sys
import json
from pandas_ods_reader import read_ods
from numpy import isnan


class Color:
    RED = "red"
    BLUE = "blue"
    YELLOW = "yellow"


class Topic:
    CATS = "cats"
    SOCKS = "socks"
    SKUB = "skub"
    HIGH_FIVES = "high_fives"
    HOUSEBOATS = "houseboats"


ods_path = sys.argv[1]
sheet_name = "Cards Master"
df = read_ods(ods_path, sheet_name)

### Loaded the data. Reading the cards now

cards = []
tgb = None

for idx in df.index[1:]:
    row = df.loc[idx]

    iloc = {"value": 0}

    def use_iloc():
        """Utility function to use and increment the iloc"""
        temp = iloc["value"]
        iloc["value"] += 1
        return temp

    new_tgb = row.iloc[use_iloc()]
    if not isnan(new_tgb):
        tgb = new_tgb

    # Factual card
    factual_card = {
        "title": "",
        "description": row.iloc[use_iloc()],
        "fakes": [
            {
                "title": "",
                "description": row.iloc[use_iloc()],
            }
        ],
        "tgb": tgb,
    }
    cards.append(factual_card)

    # Bias cards
    for color in (Color.RED, Color.BLUE, Color.YELLOW):
        bias_card = {
            "title": "",
            "description": row.iloc[use_iloc()],
            "bias_against": color,
            "fakes": [
                {
                    "title": "",
                    "description": row.iloc[use_iloc()],
                    "bias_against": color,
                }
            ],
            "tgb": tgb,
        }
        cards.append(bias_card)

    # Topic cards
    for topic in (
        Topic.CATS,
        Topic.SOCKS,
        Topic.SKUB,
        Topic.HIGH_FIVES,
        Topic.HOUSEBOATS,
    ):
        pro_card = {
            "title": "",
            "description": row.iloc[use_iloc()],
            "affinity_towards": topic,
            "affinity_count": 1,
            "fakes": [
                {
                    "title": "",
                    "description": row.iloc[use_iloc()],
                    "affinity_towards": topic,
                    "affinity_count": 1,
                }
            ],
            "tgb": tgb,
        }
        against_card = {
            "title": "",
            "description": row.iloc[use_iloc()],
            "affinity_towards": topic,
            "affinity_count": -1,
            "fakes": [
                {
                    "title": "",
                    "description": row.iloc[use_iloc()],
                    "affinity_towards": topic,
                    "affinity_count": -1,
                }
            ],
            "tgb": tgb,
        }
        cards.append(pro_card)
        cards.append(against_card)

print(json.dumps(cards))