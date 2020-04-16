from PyQt5.QtWidgets import QApplication
import os
from pprint import pprint
import sys
import unittest
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from PyQt5.QtWidgets import QApplication

from kiwoom_api.api import Kiwoom, DataFeeder, Executor


class OrderTest(unittest.TestCase):
    def testSendOrderSuccess(self):

        app = QApplication(sys.argv)

        # API 로그인
        kiwoom = Kiwoom.instance()
        kiwoom.commConnect()

        feeder = DataFeeder(kiwoom)
        executor = Executor(kiwoom)

        accNo = feeder.accNo
        code = "005930"

        orderSpecDict = executor.createOrderSpec(
            rqName="test",
            scrNo="0000",
            accNo=accNo,
            orderType=1,  # 신규매수
            code=code,
            qty=1,
            price=0,
            hogaType="03",
            originOrderNo="",
        )

        for _ in range(2):
            orderResponse = executor.sendOrder(**orderSpecDict)
            #pprint(orderResponse)

            #print(kiwoom.getServerGubun())
            

            #time.sleep(5)
            #print(len(kiwoom.codes))
            #time.sleep(5)

    """ 
    def testSendOrderFail(self):

        app = QApplication(sys.argv)

        # API 로그인
        kiwoom = Kiwoom()
        kiwoom.commConnect()

        feeder = DataFeeder(kiwoom)
        executor = Executor(kiwoom)

        accNo = feeder.getAccNo()
        code = 123144

        orderSpecDict = executor.createOrderSpec(
            rqName="test",
            scrNo="0000",
            accNo=accNo,
            orderType=1,  # 신규매수
            code=code,
            qty=1,
            price=0,
            hogaType="03",
            originOrderNo="",
        )
        executor.sendOrder(**orderSpecDict)
    """


if __name__ == "__main__":

    unittest.main()
