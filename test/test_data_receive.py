from datetime import datetime as dt
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from PyQt5.QtWidgets import QApplication

from kiwoom_api_handler.api import Kiwoom, DataFeeder


def testDataReceive():

    app = QApplication(sys.argv)

    # API 로그인
    broker = Kiwoom()
    broker.commConnect()

    feeder = DataFeeder(broker)

    accNo = feeder.getAccNo()
    today = dt.now().strftime("%Y%m%d")
    code = "005930"

    # TRs
    print(feeder.getOPT10004(code))
    print(feeder.getOPT10005(code))
    print(feeder.getOPT10059(today, code))
    print(feeder.getOPT10074(accNo, "20200101", today))
    print(feeder.getOPT10075(accNo))
    print(feeder.getOPT10080(code, "30", "0"))
    print(feeder.getOPTKWFID(["005930", "000660"]))
    print(feeder.getOPW00001(accNo))
    print(feeder.getOPW00004(accNo))
    print(feeder.getOPW00007(today, accNo))

    # support methods
    print(feeder.getDeposit(accNo))
    print(feeder.getUnExOrderDict(accNo))
    print(feeder.getAccountDict(accNo))
    print(feeder.getInventoryDict(accNo))
    print(feeder.getInventoryCodes(accNo))


if __name__ == "__main__":

    testDataReceive()
