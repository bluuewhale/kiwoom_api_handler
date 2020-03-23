from PyQt5.QtWidgets import QApplication
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import numpy as np

from kiwoom_api_handler.api import Kiwoom, DataFeeder, Executor


def dropSign(x):
    """ 부호 및 쉼표 제거

    params
    ----------
    x: str
    """

    return x.replace("+", "").replace("-", "").replace(",", "")

    x.replace()


def getNightWinners(priceDf):
    """
    1. overnight 수익률 > 0 조건으로 groupping
    2. 1번 조건을 만족하는 종목 중 overnight 수익률 상위 20%를 다시 grouping

    params
    ===============
    priceDf: pandas.DataFrame
        OPTKWFID TR요청으로 수신받은 데이터

    return
    ===============
    nightWinnerCodeList: list
        위 조건을 만족하는 종목코드 list
    """

    # 데이터 형변환 (str -> int)
    priceDf["기준가"] = list(map(lambda x: int(dropSign(x)), priceDf["기준가"]))
    priceDf["시가"] = list(map(lambda x: int(dropSign(x)), priceDf["시가"]))

    # overnight 수익률 > 0 조건으로 grouping
    priceDf["overnight"] = priceDf["시가"] / priceDf["기준가"] - 1
    nightPlusDf = priceDf[priceDf["overnight"] > 0]

    # overnight > 0 중에서 수익률 상위 20% grouping
    threshold = np.percentile(nightPlusDf["overnight"], 80)
    nightWinnerDf = nightPlusDf[nightPlusDf["overnight"] > threshold]

    nightWinnerCodeList = list(nightWinnerDf["종목코드"])

    return nightWinnerCodeList


def get30MinuteBong(feeder, code):
    """ 30분봉 데이처를 요청하는 함수

    params
    ----------
    code: str

    return
    df: pandas.DataFrame
    """

    minute = "30"
    df = feeder.getOPT10080(code, minute)

    return df


def test():

    app = QApplication(sys.argv)

    # API 로그인
    broker = Kiwoom()
    broker.commConnect()

    feeder = DataFeeder(broker)

    # 전체 2,976개 종목코드
    kspCodes = feeder.kspCodeList
    kdqCodes = feeder.kdqCodeList
    totalCodes = kspCodes + kdqCodes

    # 기준가(전일 종가, 상장폐지 종목은 상장폐지전 마지막 종가), 시가 등에 대한 정보 요청
    # return data는 모두 string type
    priceDf = feeder.getOPTKWFID(totalCodes)  # (2976, 63)

    # overnight 상위 20% 종목
    nightWinners = getNightWinners(priceDf)
    print(nightWinners)

    # 개별 종목의 30분봉 데이터 요청
    for code in nightWinners:
        bongDf = get30MinuteBong(feeder, code)
        break

    print(bongDf)

    # 데이터 형변환 (str -> int)
    typeChgColumns = ["시가", "고가", "저가", "현재가"]

    for col in typeChgColumns:
        bongDf[col] = list(map(lambda x: int(dropSign(x)), bongDf[col]))


if __name__ == "__main__":

    test()
