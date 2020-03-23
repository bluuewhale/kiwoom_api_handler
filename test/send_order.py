from PyQt5.QtWidgets import QApplication
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

<<<<<<< HEAD:test/send_order.py
from kiwoom_api_handler.api import Kiwoom, DataFeeder, Executor
=======
from PyQt5.QtWidgets import QApplication

from kiwoom_api.api import Kiwoom, DataFeeder, Executor
>>>>>>> 23fae0b04e39ea3193123baac24b6bab82410959:test/test_send_order.py


class OrderTest(unittest.TestCase):
    def testSendOrderSuccess(self):

        app = QApplication(sys.argv)

        # API 로그인
        kiwoom = Kiwoom()
        kiwoom.commConnect()

        feeder = DataFeeder(kiwoom)
        executor = Executor(kiwoom)

        accNo = feeder.getAccNo()
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
        orderResponse = executor.sendOrder(**orderSpecDict)

        print(orderResponse)

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
