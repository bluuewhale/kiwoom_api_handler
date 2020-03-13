from datetime import datetime as dt
from functools import wraps
import os
import sys

sys.path.append(r"C:\Users\koko8\Documents\git-project\kiwoom_api")
import unittest

from PyQt5.QtWidgets import QApplication

from kiwoom_api.api import Kiwoom, DataFeeder


def initQt(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        app = QApplication(sys.argv)
        self.broker = Kiwoom()
        self.feeder = DataFeeder(self.broker)
        self.broker.commConnect()

        func(self, *args, **kwargs)

    return inner


class TestKiwoom(unittest.TestCase):
    def Setup(self):
        pass

    # @initQt
    def testSingleTone(self):
        app = QApplication(sys.argv)

        a = Kiwoom.instance()
        b = Kiwoom.instance()

        a.commConnect()

        print(a)
        print(b)
        print(a.connectState)
        print(b.connectState)


if __name__ == "__main__":
    unittest.main()
