from datetime import datetime as dt
from functools import wraps
import os
from pprint import pprint
import sys
import time
import unittest

from PyQt5.QtWidgets import QApplication

from kiwoom_api.api import Kiwoom, DataFeeder


def initQt(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        app = QApplication(sys.argv)
        kiwoom = Kiwoom()
        kiwoom.commConnect()
        self.feeder = DataFeeder(kiwoom)

        func(self, *args, **kwargs)

    return inner


class TestDataFeeder(unittest.TestCase):
    def setUp(self):
        self.feeder = None
        self.date = "20200312"
        self.code = "005930"
        time.sleep(3)
    #! TODO: 유닛테스트 코드 작성

    @initQt
    def testOPT10004(self, *args, **kwargs):

        params = {"종목코드": self.code}
        data = self.feeder.request(trCode="OPT10004", **params)
        pprint(data)

    @initQt
    def testOPT10005(self):

        params = {"종목코드": self.code}
        data = self.feeder.request(trCode="OPT10005", **params)
        pprint(data)

    @initQt
    def testOPT10059(self):

        params = {
            "일자": self.date,
            "종목코드": self.code,
            "금액수량구분": "1",  # 1:금액, 2:수량
            "매매구분": "0",  # 0:순매수, 1:매수, 2:매도
            "단위구분": "1",  # 1:단주, 1000:천주
        }

        data = self.feeder.request(trCode="OPT10059", **params)
        pprint(data)

    @initQt
    def testOPT10074(self):

        params = {
            "계좌번호": self.feeder.accNo,
            "시작일자": self.date,
            "종료일자": self.date,
        }

        data = self.feeder.request(trCode="OPT10074", **params)
        pprint(data)

    @initQt
    def testOPT10075(self):

        params = {
            "계좌번호": self.feeder.accNo,
            "전체종목구분": "0",
            "매매구분": "0",
            "종목코드": self.code,
            "체결구분": "0",
        }

        data = self.feeder.request(trCode="OPT10075", **params)
        pprint(data)

    @initQt
    def testOPT10080(self):

        params = {
            "종목코드": self.code,
            "틱범위": "1",
            "수정주가구분": "0",
        }

        data = self.feeder.request(trCode="OPT10080", **params)
        pprint(data)

    @initQt
    def testOPTKWFID(self):

        params = {
            "arrCode": "005930;023590",
            "next": 0,
            "codeCount": 2,
        }
        data = self.feeder.requestOPTKWFID(**params)
        pprint(data)

    @initQt
    def testOPW00001(self):

        params = {
            "계좌번호": self.feeder.accNo,
            "비밀번호": "",
            "비밀번호입력매체구분": "00",
            "조회구분": "2",
        }
        data = self.feeder.request(trCode="OPW00001", **params)
        pprint(data)

    @initQt
    def testOPW00004(self):

        params = {
            "계좌번호": self.feeder.accNo,
            "비밀번호": "",
            "상장폐지조회구분": "0",
            "비밀번호입력매체구분": "00",
        }
        data = self.feeder.request(trCode="OPW00004", **params)
        pprint(data)

    @initQt
    def testOPW00007(self):

        params = {
            "주문일자": "202003013",
            "계좌번호": self.feeder.accNo,
            "비밀번호": "",
            "비밀번호입력매체구분": "00",
            "조회구분": "1",
        }
        data = self.feeder.request(trCode="OPW00007", **params)
        pprint(data)

    # unility methods
    @initQt
    def testGetDeposit(self):
        accNo = self.feeder.accNo
        data = self.feeder.getDeposit(accNo)
        pprint(data)

    @initQt
    def testGetUnExOrders(self):
        accNo = self.feeder.accNo
        data = self.feeder.getUnExOrders(accNo)
        pprint(data)

    @initQt
    def testGetAccountDict(self):
        accNo = self.feeder.accNo
        data = self.feeder.getAccountDict(accNo)
        pprint(data)

    @initQt
    def testGetInventoryDict(self):
        accNo = self.feeder.accNo
        data = self.feeder.getInventoryDict(accNo)
        pprint(data)

    @initQt
    def testGetInventoryCodes(self):
        accNo = self.feeder.accNo
        data = self.feeder.getInventoryCodes(accNo)
        pprint(data)

    @initQt
    def testGetCodeListByMarket(self):

        market = "0"
        data = self.feeder.getCodeListByMarket(market)
        #pprint(data[:10])

    @initQt
    def testGetMasterCodeName(self):

        data = self.feeder.getMasterCodeName(self.code)
        pprint(data)
        self.assertEqual(data, "삼성전자")

    @initQt
    def testGetMarketByCode(self):

        data = self.feeder.getMarketByCode(self.code)
        pprint(data)
        self.assertEqual(data, "KSP")

    @initQt
    def testGetMasterStockState(self):

        data = self.feeder.getMasterStockState(self.code)
        pprint(data)


if __name__ == "__main__":

    unittest.main()
