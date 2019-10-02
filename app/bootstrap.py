import gc
import upip

from wifimgr import get_connection
from github import Repo


def main():
    wlan = get_connection()
    gc.collect()

    for package in ('urequests', 'shutil', 'uasyncio', 'functools'):
        upip.install(package)
        gc.collect()


def fetch_update(API_TOKEN, output_dir='/ota-next', cache=False):
    USERNAME = 'sci-bots'
    REPO_URL = 'https://github.com/sci-bots/esp32-pump-driver'

    repo = Repo(REPO_URL, api_token=API_TOKEN, username=USERNAME)

    latest_tag = repo.latest_version()

    contents = repo.tag_contents(latest_tag, path='/app')
    try:
        repo.download(contents, root=output_dir, cache=cache)
    except Exception as exception:
        print('error fetching update: `%s`' % contents)

    # try:
        # if exists('/app_'):
            # rmtree('/app_')
        # if exists('/app'):
            # os.rename('/app', '/app_')
        # os.rename('/ota-next', '/app')
        # print('updated: `/app`')
    # finally:
        # if exists('/ota-next'):
            # rmtree('/ota-next')
