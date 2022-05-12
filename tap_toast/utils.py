import os


def get_abs_path(path, base=None):
    if base is None:
        base = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(base, path)
