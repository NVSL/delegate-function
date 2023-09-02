from contextlib import contextmanager
import copy
import os

@contextmanager
def env(**kwargs):
    try:
        old = copy.deepcopy(os.environ)
        os.environ.update(kwargs)
        yield
    finally:
        os.environ.update(old)