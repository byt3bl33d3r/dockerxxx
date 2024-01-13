import random

def random_name():
    return f'dockerpytest_{random.getrandbits(64):x}'
