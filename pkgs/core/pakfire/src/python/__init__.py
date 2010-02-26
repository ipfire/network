#!/usr/bin/python

from repo import Repositories
from transactionset import Transactionset

class Pakfire(object):
    repos = Repositories()
    ts = Transactionset()

    def __init__(self):
        pass
