from datetime import datetime as dt
from functools import wraps
import os
import sys

sys.path.append(r"C:\Users\koko8\Documents\git-project\kiwoom_api")
import unittest

from PyQt5.QtWidgets import QApplication

from kiwoom_api.api import Kiwoom, DataLoader


def initQt(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        app = QApplication(sys.argv)
        self.broker = Kiwoom()
        self.loader = DataLoader(self.broker)
        self.broker.commConnect()

        func(self, *args, **kwargs)

    return inner


class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = None
        self.date = "20200312"
        self.code = "005930"

    #! TODO: 유닛테스트 코드 작성

    def printData(self, data):
        if data.get("싱글데이터", False):
            print(data.get("싱글데이터"))

        if data.get("멀티데이터", False):
            print(data.get("멀티데이터")[0])

    @initQt
    def testOPT10004(self, *args, **kwargs):
        self.assertTrue(hasattr(self.loader, "load"))

        params = {"종목코드": self.code}
        data = self.loader.load(trCode="OPT10004", **params)

        print(data)

    @initQt
    def test_OPT10005(self):
        self.assertTrue(hasattr(self.loader, "load"))

        params = {"종목코드": self.code}
        data = self.loader.load(trCode="OPT10005", **params)

        print(data)

    @initQt
    def test_OPT10059(self):
        self.assertTrue(hasattr(self.loader, "load"))

        params = {
            "일자": self.date,
            "종목코드": self.code,
            "금액수량구분": "1",  # 1:금액, 2:수량
            "매매구분": "0",  # 0:순매수, 1:매수, 2:매도
            "단위구분": "1",  # 1:단주, 1000:천주
        }
        data = self.loader.load(trCode="OPT10059", **params)

        print(data)

    @initQt
    def test_OPT10074(self):
        self.assertTrue(hasattr(self.loader, "load"))

        params = {
            "계좌번호": self.loader.getAccNo(),
            "시작일자": self.date,
            "종료일자": self.date,
        }
        data = self.loader.load(trCode="OPT10074", **params)

        print(data)

    @initQt
    def test_OPT10075(self):
        self.assertTrue(hasattr(self.loader, "load"))

        params = {
            "계좌번호": self.loader.getAccNo(),
            "전체종목구분": "0",
            "매매구분": "0",
            "종목코드": self.code,
            "체결구분": "0",
        }
        data = self.loader.load(trCode="OPT10075", **params)

        print(data)

        """
        # TRs
        print(feeder.getOPT10004(code))
        print(feeder.getOPT10005(code))
        print(feeder.getOPT10059(today, code))
        print(feeder.getOPT10074(accNo, "20200101", today))
        print(feeder.getOPT10075(accNo))
        print(feeder.getOPT10080(code, "30", "0"))
        print(feeder.getOPTKWFID([self.code, "000660"]))
        print(feeder.getOPW00001(accNo))
        print(feeder.getOPW00004(accNo))
        print(feeder.getOPW00007(today, accNo))

        # support methods
        print(feeder.getDeposit(accNo))
        print(feeder.getUnExOrderDict(accNo))
        print(feeder.getAccountDict(accNo))
        print(feeder.getInventoryDict(accNo))
        print(feeder.getInventoryCodes(accNo))
        """


if __name__ == "__main__":

    unittest.main()
