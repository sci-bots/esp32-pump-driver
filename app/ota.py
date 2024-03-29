import gc
import os

import util

from wifimgr import get_connection
from github import Repo


USERNAME = 'sci-bots'
REPO_URL = 'https://github.com/sci-bots/esp32-pump-driver'


def latest_version(API_TOKEN):
    repo = Repo(REPO_URL, api_token=API_TOKEN, username=USERNAME)
    return repo.latest_version()


def fetch_update(API_TOKEN, tag=None, output_dir='/ota-next', cache=False,
                 verbose=True):
    # Try to connect to wifi
    wlan = get_connection()
    if wlan is None:
        raise RuntimeError('No network connection.')

    if not util.exists(output_dir):
        os.mkdir(output_dir)

    repo = Repo(REPO_URL, api_token=API_TOKEN, username=USERNAME)

    if tag is None:
        tag = repo.latest_version()

    downloaded = []
    for path in ('/app', '/lib'):
        contents = repo.tag_contents(tag, path=path)
        try:
            downloaded += repo.download(contents, root=output_dir + path,
                                        cache=cache, verbose=verbose)
        except Exception as exception:
            print('error fetching update: `%s`' % contents)
            raise
    with open(output_dir + '/VERSION', 'w') as output:
        output.write(tag + '\n')
    gc.collect()
    return downloaded


def swap(previous, current, next_):
    try:
        if util.exists(previous):
            util.rmtree(previous)
        os.mkdir(previous)

        for path in ('/app', '/lib', '/VERSION'):
            if util.exists(current + path):
                os.rename(current + path, previous + path)
            if util.exists(next_ + path):
                os.rename(next_ + path, current + path)
                print('updated: `%s`' % (current + path))
            gc.collect()
    finally:
        if util.exists(next_):
            util.rmtree(next_)
