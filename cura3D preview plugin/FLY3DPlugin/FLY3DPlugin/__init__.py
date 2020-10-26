# Copyright (c) 2017 Looming
# Cura is released under the terms of the LGPLv3 or higher.

from . import FLY3DStore


def getMetaData():
    return {}


def register(app):
    return {
        "output_device": FLY3DStore.FLY3DStorePlugin(),
        }
