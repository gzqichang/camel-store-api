import os

import datetime


def generate_file_name(prefix, file_name=None):
    return "_".join([prefix, str(datetime.datetime.now().timestamp()), file_name])


def encode(name):
    try:
        return name.encode('cp437').decode()
    except UnicodeDecodeError:
        return name.encode('cp437').decode('gbk')