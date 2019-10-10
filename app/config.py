import json

import util


def save():
    with open('config.json', 'w') as output:
        json.dump(CONFIG, output)


def load():
    '''
    .. versionchanged:: 0.8.1
        Check if config file exists before trying to open it.
    '''
    CONFIG.clear()
    if util.exists('config.json'):
        with open( 'r') as input_:
            CONFIG.update(json.load(input_))

    return CONFIG


CONFIG = {}

load()
