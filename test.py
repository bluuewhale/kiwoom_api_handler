from datetime import datetime as dt
import sys

import pandas as pd
from PyQt5.QtWidgets import QApplication

from api import *


if __name__ == "__main__":
    pd.options.mode.chained_assignment = None

    # 접속
    app = QApplication(sys.argv)

    # API 로그인
    stratID = "A011010001"

    broker = Kiwoom(stratID)
    broker.commConnect()

    feeder = DataFeeder(broker)
    executor = Executor(broker)

    accNo = feeder.getAccNo()
    today = dt.now().strftime("%Y%m%d")
    code = "005930"

    print(feeder.getOPT10004(code))
    print(feeder.getOPT10005(code))
    print(feeder.getOPT10059(today, code))
    print(feeder.getOPT10074(accNo, "20200101", today))
    print(feeder.getOPT10075(accNo))
    print(feeder.getOPTKWFID(["005930", "006630"]))
    print(feeder.getOPW00001(accNo))
    print(feeder.getOPW00004(accNo))
    print(feeder.getOPW00007(today, accNo))

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

    # executor.sendOrder(orderSpecDict)
