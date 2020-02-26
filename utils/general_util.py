import os


def my_mkdir(path, is_file=False):
    if is_file:
        path = os.path.dirname(path)

    if not os.path.exists(path):
        os.makedirs(path)
