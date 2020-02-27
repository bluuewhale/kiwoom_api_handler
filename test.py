import sys

import pandas as pd
from PyQt5.QtWidgets import QApplication

from executor import Executor
from feeder import Feeder
from broker import *



if __name__ == '__main__':
    pd.options.mode.chained_assignment = None

    # 접속
    app = QApplication(sys.argv)

    # API 로그인
    stratID = 'A011010001'

    broker = Kiwoom(stratID)
    broker.commConnect()

    feeder = Feeder(broker)

    accntNum = feeder.getAccountNum()
    date = datetime.now().strftime("%Y%m%d")
    code = "005930"

    #print(feeder.getOpt10059(date, code))
    print(feeder.getOpw00001(accntNum))
