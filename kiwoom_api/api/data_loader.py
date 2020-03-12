from collections import defaultdict
from datetime import datetime
import os

import pandas as pd

from kiwoom_api.api._errors import *
from kiwoom_api.api._config import *


class Loader:
    def __init__(self, **kwargs):
        pass

    def load(self):
        raise NotImplementedError


class DataLoader(Loader):
    """ Data 수신과 관련된 class 입니다. Kiwoom 인스턴스(instance)를 생성자의 매개변수로 받습니다.

    TR과 관련된 자세한 사항은 [키움증권 공식 API 개발
    문서](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) 혹은 KOA StudioSA를 참조하시길 바랍니다.
    """

    def __init__(self, kiwoom, **kwargs):
        self.kiwoom = kiwoom

        for k, v in kwargs:
            setattr(self, k, v)

    def load(self, trCode, **kwargs):

        for k, v in kwargs.items():
            self.kiwoom.setInputValue(k, v)

        trName = getattr(TRName, trCode)
        self.kiwoom.commRqData(trName, trCode, 0, "0000")

        data = getattr(self.kiwoom, trCode)
        return data

    #############################
    ###### utility methods ######
    #############################

    def getAccNo(self):
        return self.kiwoom.getLoginInfo("ACCNO").rstrip(";")

    def getDeposit(self, accNo):
        """ D+2 추정예수금 반환 
        
        Returns
        ----------
        int
        """

        OPW00004 = self.load("OPW00004", **{"계좌번호": accNo})
        deposit = int(OPW00004.get("싱글데이터").get("D+2추정예수금").replace(",", ""))
        return deposit

    def getUnExOrders(self, accNo, code=""):
        """ 미체결 정보 반환
        
        Returns
        ----------
        dict
        """

        params = {
            "계좌번호": accNo,
            "전체종목구분": "0",  # 전체
            "매매구분": "0",  # 매수+매도
            "체결구분": "1",  # 미체결
        }

        if code:
            params["전체종목구분"] = "1"  # 종목
            params["종목코드"] = code

        return self.load("OPT10075", **params)

    def getAccountDict(self, accNo):
        """ 계좌 정보 """

        OPW00004 = self.load("OPW00004", **{"계좌번호": accNo})
        return OPW00004.get("싱글데이터")

    def getInventoryDict(self, accNo):
        """ 현재 보유중인 개별 종목 정보 """

        OPW00004 = self.load("OPW00004", **{"계좌번호": accNo})
        return OPW00004.get("멀티데이터")

    def getInventoryCodes(self, accNo):
        """ 현재 보유중인 종목코드 반환 """

        inventoryDict = self.getInventoryDict(accNo)
        return inventoryDict.get("종목코드")

    def getCodeListByMarket(self, market):
        """시장 구분에 따른 종목코드의 목록을 List로 반환한다.

        market에 올 수 있는 값은 아래와 같다.
        {
         '0': 장내,
         '3': ELW,
         '4': 뮤추얼펀드,
         '5': 신주인수권,
         '6': 리츠,
         '8': ETF,
         '9': 하이일드펀드,
         '10': 코스닥,
         '30': 제3시장
        }

        Parameters
        ----------
        market: str

        Returns
        ----------
        codeList: list
            조회한 시장에 소속된 종목 코드를 담은 list
        """

        if not self.kiwoom.getConnectState():
            raise KiwoomConnectError()

        if not isinstance(market, str):
            raise ParameterTypeError()

        if market not in ["0", "3", "4", "5", "6", "8", "9", "10", "30"]:
            raise ParameterValueError()

        codes = self.kiwoom.dynamicCall('GetCodeListByMarket("{}")'.format(market))
        return codes.split(";")

    def getCodeList(self, *markets):
        """ 여러 시장의 종목코드를 List 형태로 반환하는 헬퍼 메서드.

        Parameters
        -----------
        market: array-like or strings - {
         '0': 장내,
         '3': ELW,
         '4': 뮤추얼펀드,
         '5': 신주인수권,
         '6': 리츠,
         '8': ETF,
         '9': 하이일드펀드,
         '10': 코스닥,
         '30': 제3시장
        }

        Returns
        ----------
        list
        """

        codeList = list(map(self.getCodeListByMarket, markets))
        return codeList

    def getMasterCodeName(self, code):
        """ 종목코드의 한글명을 반환한다.

        Parameters
        ----------
        code: str
            종목코드

        Returns
        ----------
        name: str
            종목코드의 한글명
        """

        if not self.kiwoom.getConnectState():
            raise KiwoomConnectError()

        if not isinstance(code, str):
            raise ParameterTypeError()

        name = self.kiwoom.dynamicCall('GetMasterCodeName("{}")'.format(code))
        return name

    def getMarketByCode(self, code):
        """ 해당 종목이 상장된 시장정보 반환 """

        if not hasattr(self, "kspCodeList"):
            setattr(self, "kspCodeList", self.getCodeListByMarket("0"))
            setattr(self, "kdqCodeList", self.getCodeListByMarket("10"))
            setattr(self, "etfCodeList", self.getCodeListByMarket("8"))

        if code in getattr(self, "kspCodeList"):
            return "KSP"

        if code in getattr(self, "kdqCodeList"):
            return "KDQ"

        if code in getattr(self, "etfCodeList"):
            return "ETF"

        return None

    def getMasterStockState(self, code):
        """
        종목코드의 현재 상태를 반환한다.

        Parameters
        ----------
        code: str

        Returns
        ----------
        stateList: list,  증거금비율, 종목상태(관리종목, 거래정지 등..)
        """

        if not isinstance(code, str):
            raise ParameterTypeError()

        states = self.kiwoom.dynamicCall("GetMasterStockState(QString)", code)
        return states.split("|")

    def checkHasIssue(self, code):
        """ 해당 종목이 관리종목 혹은 거래정지에 해당하는지 확인하는 함수

        Returns
        ----------
        isIssue: bool
            True: 관리종목 or 거래정지종목
        """

        stateList = self.kiwoom.getMasterStockState(code)

        if ("관리종목" in stateList) or ("거래정지" in stateList):
            return True

        return False

    """
    ### logging 관련 매서드
    def showTradingSummary(self, date):

        # logging할 데이터
        params = {
            "계좌번호": "accNo",
            "시작일자": date,
            "종료일자": date,
        }
        traSummaryDict = self.load("OPT10074", **params)

        date = "-".join((date[:4], date[4:6], date[6:]))  # YYYY-MM-DD 꼴로 수정

        totalBuy = int(traSummaryDict.get("총매수금액"))
        totalSell = int(traSummaryDict.get("총매도금액"))
        netProfit = int(traSummaryDict.get("실현손익"))
        accoundDict = self.getAccountDict(self.accNo)
        balanceEnd = int(accoundDict["account"]["추정예탁자산"].replace(",", ""))  # 마감 잔고
        balanceStart = balanceEnd - netProfit
        ret = balanceEnd / balanceStart - 1

        summaryDict = {
            "TABLE": "trading_summary",
            "BASC_DT": date,
            "STRAT_BUY": totalBuy,
            "STRAT_SELL": totalSell,
            "STRAT_NET_PROFIT": netProfit,
            "BALANCE_START": balanceStart,
            "BALANCE_END": balanceEnd,
            "STRAT_RET_PCT": ret,
        }

        self.kiwoom.logger.debug("=" * 70)
        self.kiwoom.logger.debug("{")
        for k, v in summaryDict.items():
            self.kiwoom.logger.debug('"{}" : "{}" ,'.format(k, v))
        self.kiwoom.logger.debug("}")
        self.kiwoom.logger.debug("=" * 70)

        return summaryDict
    """

