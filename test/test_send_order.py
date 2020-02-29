import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from PyQt5.QtWidgets import QApplication

from kiwoom_api_handler.api import Kiwoom, DataFeeder, Executor


def testSendOrder():

    app = QApplication(sys.argv)

    # API 로그인
    broker = Kiwoom()
    broker.commConnect()

    feeder = DataFeeder(broker)
    executor = Executor(broker)

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

    executor.sendOrder(orderSpecDict)


if __name__ == "__main__":

    testSendOrder()
