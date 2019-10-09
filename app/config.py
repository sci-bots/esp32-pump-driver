import json


def save():
    with open('config.json', 'w') as output:
        json.dump(CONFIG, output)


def load():
    CONFIG.clear()
    with open('config.json', 'r') as input_:
        CONFIG.update(json.load(input_))
    return CONFIG


CONFIG = {}

load()
