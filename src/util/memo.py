import os
import json
import yaml
from src.config.config import read_config
import codecs
import string
import random


sites = {}
pages = {}
edits = []
tepapalinks = {}

editors = {}

comments = []


def load_memo():
    global pages, edits, editors, comments
    memo_data = load_file("memo.json")

    if memo_data:
        pages = memo_data.get("pages")
        edits = memo_data.get("edits")
        editors = memo_data.get("editors")
        comments = memo_data.get("comments")


def save_memo():
    memo_data = {"pages": pages,
                 "edits": edits,
                 "editors": editors,
                 "comments": comments}
    save_file("memo.json", memo_data)


def load_users():
    usernames = read_config("usernames")

    for u in usernames:
        editors.update({u: {"username": u, "active": False, "new_pages": []}})

    return usernames


def obscure_username(username):
    letters = string.ascii_lowercase
    prefix = "".join(random.choices(letters, k=10))
    suffix = "".join(random.choices(letters, k=10))
    o_username = prefix + codecs.encode(username, "rot_13") + suffix
    return o_username


def match_username(username, o_username):
    o_username = o_username[10:-10]
    if codecs.encode(o_username, "rot_13") == username:
        return True


def update_url_dump(filepath, data):
    saved_data = load_file(filepath)
    if not saved_data:
        saved_data = {}
    for page_key in data.keys():
        if page_key not in saved_data.keys():
            page_data = data[page_key]
            pageid = page_data["pageid"]
            site_id = page_data["site"]
            title = page_data["title"]
            page_type = page_data["page_type"]
            saved_data.update({page_key: {"pageid": pageid,
                                          "site": site_id,
                                          "title": title,
                                          "page_type": page_type}})
    save_file(filepath, saved_data)


def load_file(filepath, plaintext=False):
    if os.path.isfile(filepath):
        data = None
        if filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                if plaintext:
                    data = f.read()
                else:
                    data = [line.strip() for line in f.readlines()]
        elif filepath.endswith(".json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = None
        elif filepath.endswith(".yaml"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except yaml.YAMLError:
                data = None

        return data

    else:
        print("File at {} not found. Will be created on write.".format(filepath))
        return None


def load_summary(platform_name):
    filepath = "src/resources/summaries/{}.txt".format(platform_name)
    return load_file(filepath, plaintext=True)


def save_file(filepath, data):
    with open(filepath, "w+", encoding="utf-8") as f:
        try:
            json.dump(data, f, indent=4)
        except json.JSONDecodeError:
            print("Failed to write data to {}.".format(filepath))
