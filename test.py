from datetime import datetime as dt
import sys

import pandas as pd
from PyQt5.QtWidgets import QApplication

from executor import Executor
from feeder import Feeder
from api import *


if __name__ == "__main__":
    pd.options.mode.chained_assignment = None

    # 접속
    app = QApplication(sys.argv)

    # API 로그인
    stratID = "A011010001"

    broker = Kiwoom(stratID)
    broker.commConnect()

    feeder = Feeder(broker)

    accntNum = feeder.getAccountNum()
    today = dt.now().strftime("%Y%m%d")
    code = "005930"

    # print(feeder.getOpt10004(code))
    # print(feeder.getOpt10005(code))
    print(feeder.getOpt10059(today, code))
    # print(feeder.getOpw00001(accntNum))
