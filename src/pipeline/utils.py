import os


def raw_dir(file):
    return os.path.join("../../data/raw", file)


def clean_dir(file):
    return os.path.join("../../data/clean", file)
