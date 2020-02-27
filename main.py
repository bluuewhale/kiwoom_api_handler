import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from executor import Executor
from feeder import Feeder
from Kiwoom import *
from orderCreator import OrderCreator
from runner import OvernightReversalRunner

if __name__ == '__main__':
    pd.options.mode.chained_assignment = None

    # 접속
    app = QApplication(sys.argv)

    # 전략코드
    stratID = 'A011010001' # Overnight Reverse

    # API 로그인
    broker = Kiwoom(stratID)
    broker.commConnect()

    feeder = Feeder(broker)
    executor = Executor(broker)
    orderCreator = OrderCreator(feeder)
    accountNum = feeder.getAccountNum()

    # runner 객체 생성
    runner = OvernightReversalRunner(feeder, orderCreator, executor, accountNum)

    # 실행
    runner.run()
