from datetime import datetime as dt
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from PyQt5.QtWidgets import QApplication

from kiwoom_api_handler.api import Kiwoom, DataFeeder


def test_all():
    app = QApplication(sys.argv)

    # API 로그인
    broker = Kiwoom.instance()
    broker.commConnect()

    feeder = DataFeeder(broker)

    code = "005930"
    today = dt.now().strftime("%Y%m%d")
    accNo = feeder.getAccNo()

    # TRs
    try:
        feeder.getOPT10001(code)
    except Exception as e:
        print("feeder.getOPT10001() ERROR : {}".format(e))

    try:
        feeder.getOPT10004(code)
    except Exception as e:
        print("feeder.getOPT10004() ERROR : {}".format(e))

    try:
        feeder.getOPT10005(code)
    except Exception as e:
        print("feeder.getOPT10005() ERROR : {}".format(e))

    try:
        feeder.getOPT10059(today, code)
    except Exception as e:
        print("feeder.getOPT10059() ERROR : {}".format(e))

    try:
        feeder.getOPT10074(accNo, "20200101", today)
    except Exception as e:
        print("feeder.getOPT10074() ERROR : {}".format(e))

    try:
        feeder.getOPT10075(accNo)
    except Exception as e:
        print("feeder.getOPT10075() ERROR : {}".format(e))

    try:
        feeder.getOPT10080(code, "30", "0")
    except Exception as e:
        print("feeder.getOPT10080() ERROR : {}".format(e))

    try:
        feeder.getOPTKWFID(["005930", "000660"])
    except Exception as e:
        print("feeder.getOPTKWFID() ERROR : {}".format(e))

    try:
        feeder.getOPW00001(accNo)
    except Exception as e:
        print("feeder.getOPW00001() ERROR : {}".format(e))

    try:
        feeder.getOPW00004(accNo)
    except Exception as e:
        print("feeder.getOPW00004() ERROR : {}".format(e))

    try:
        feeder.getOPW00007(today, accNo)
    except Exception as e:
        print("feeder.getOPW00007() ERROR : {}".format(e))

    # support methods
    try:
        feeder.getDeposit(accNo)
    except Exception as e:
        print("feeder.getAccNo() ERROR : {}".format(e))

    try:
        feeder.getUnExOrderDict(accNo)
    except Exception as e:
        print("feeder.getUnExOrderDict() ERROR : {}".format(e))

    try:
        feeder.getAccountDict(accNo)
    except:
        print("feeder.getAccountDict() ERROR : {}".format(e))

    try:
        feeder.getInventoryDict(accNo)
    except:
        print("feeder.getInventoryDict() ERROR : {}".format(e))

    try:
        feeder.getInventoryCodes(accNo)
    except:
        print("feeder.getInventoryCodes() ERROR : {}".format(e))

    try:
        print(feeder.getWantedTRs("종가"))
    except:
        print("feeder.getWantedTRs() ERROR : {}".format(e))


if __name__ == "__main__":

    test_all()
