"""Converts a given XL sheet into a JSON file and downloads the images in the XL sheet, alongwith assigning them UUIDs

The JSON objects can then be used to import data into the Database
"""

import copy
import sys
import json
from pandas_ods_reader import read_ods
from numpy import isnan
import gdown
import openpyxl
import uuid

wb = openpyxl.load_workbook('Viral Spiral v2.xlsx')
ws = wb['Cards Master']


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


def is_valid_cell(text):
    return text and text.strip() and text.strip() != "null"

def image_token_creator(r, c, sheet):
    # print("(" + str(r) + "," + str(c) + ")")
    try: 
        url = sheet.cell(row=r, column=c).hyperlink.target
        # url = url.replace("open", "uc")
        # print(url)
        file_id = url.split('=')[1]
        file_id = file_id[:-4]
        prefix = 'https://drive.google.com/uc?/export=download&confirm=pbef&id='
        image_id = uuid.uuid4()
        output = str(image_id) + '.jpg'
        image_folder_path = 'images/'
        gdown.download(prefix+file_id, image_folder_path+output, quiet=True)
        return str(image_id)
    except AttributeError:
        # print("No download!")
        return ""



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

    description_true = row.iloc[use_iloc()]
    description_fake = row.iloc[use_iloc()]
    image_url = image_token_creator(idx+2, use_iloc()+1, ws)
    factual_card = {
        "title": "",
        "description": description_true,
        "fakes": [
            {
                "title": "",
                "description": description_fake,
                "fake": True,
                "image": image_url,
                "tgb": tgb,
            }
        ],
        "tgb": tgb,
        "image": image_url,
    }
    if not is_valid_cell(factual_card["fakes"][0]["description"]):
        factual_card["fakes"] = []
    cards.append(factual_card)

    # Bias cards
    for color in (Color.RED, Color.BLUE, Color.YELLOW):
        bias_card = {
            "title": "",
            "description": row.iloc[use_iloc()],
            "bias_against": color,
            "fakes": [],
            "fake": True, 
            "tgb": tgb,
            "image": image_token_creator(idx+2, use_iloc()+1, ws),
        }
        # if not is_valid_cell(bias_card["fakes"][0]["description"]):
        #     bias_card["fakes"] = []
        cards.append(bias_card)

    # Topic cards
    for topic in (
        Topic.CATS,
        Topic.SOCKS,
        Topic.SKUB,
        Topic.HIGH_FIVES,
        Topic.HOUSEBOATS,
    ):
        
        # pro card
        description_true = row.iloc[use_iloc()]
        description_fake = row.iloc[use_iloc()]
        image_url = image_token_creator(idx+2, use_iloc()+1, ws)


        pro_card = {
            "title": "",
            "description": description_true,
            "affinity_towards": topic,
            "affinity_count": 1,
            "fakes": [
                {
                    "title": "",
                    "description": description_fake,
                    "affinity_towards": topic,
                    "affinity_count": 1,
                    "fake": True,
                    "image": image_url,
                    "tgb": tgb,
                }
            ],
            "tgb": tgb,
            "image": image_url,
        }

        # against card
        description_true = row.iloc[use_iloc()]
        description_fake = row.iloc[use_iloc()]
        image_url = image_token_creator(idx+2, use_iloc()+1, ws)


        against_card = {
            "title": "",
            "description": description_true,
            "affinity_towards": topic,
            "affinity_count": -1,
            "fakes": [
                {
                    "title": "",
                    "description": description_fake,
                    "affinity_towards": topic,
                    "affinity_count": -1,
                    "fake": True,
                    "image": image_url,
                    "tgb": tgb,
                }
            ],
            "tgb": tgb,
            "image": image_url,
        }
        if not is_valid_cell(pro_card["fakes"][0]["description"]):
            pro_card["fakes"] = []
        if not is_valid_cell(against_card["fakes"][0]["description"]):
            against_card["fakes"] = []
        cards.append(pro_card)
        cards.append(against_card)

print(json.dumps(cards))

json_string = json.dumps(cards)

with open('cards.json', 'w') as outfile:
    outfile.write(json_string)  
