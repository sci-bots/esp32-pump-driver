import gc
import upip

from wifimgr import get_connection


def main():
    wlan = get_connection()
    gc.collect()

    for package in ('urequests', 'shutil', 'uasyncio', 'functools'):
        upip.install(package)
        gc.collect()
