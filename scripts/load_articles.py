import sys
import random
import json
from pandas_ods_reader import read_ods

ods_path = sys.argv[1]
sheet_names = [
    "S Factual",
    "S Cats",
    "S Socks",
    "S Skub",
    "S High fives",
    "S Houseboats",
    "S Anti-Red",
    "S Anti-Blue",
    "S Anti-Yellow",
    "S Conflated"
]
class Indexes():
    HEADLINE = 0
    TYPE = 1
    CONTENT = 2
    AUTHOR = 3
    FAKE_TYPE = 4
    FAKE_CONTENT = 5
    FAKE_AUTHOR = 6

def get_iloc(row, idx):
    try:
        return row.iloc[idx]
    except IndexError:
        return ""

articles = []
for sheet_name in sheet_names:
    df = read_ods(ods_path, sheet_name)
    for idx in df.index[1:]:
        row = df.loc[idx]

        article = {
            "title": get_iloc(row, Indexes.HEADLINE),
            "content": get_iloc(row, Indexes.CONTENT),
            "type_": get_iloc(row, Indexes.TYPE),
            "author": get_iloc(row, Indexes.AUTHOR),
            "fake_content": get_iloc(row, Indexes.FAKE_CONTENT),
            "fake_type_": get_iloc(row, Indexes.FAKE_TYPE),
            "fake_author": get_iloc(row, Indexes.FAKE_AUTHOR),
            "is_fake": random.choice((True, False)),  # Add weight
        }
        articles.append(article)


print(json.dumps(articles))
