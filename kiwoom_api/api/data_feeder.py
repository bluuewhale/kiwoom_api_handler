from collections import defaultdict
from datetime import datetime
import os

import pandas as pd

from .errors import KiwoomConnectError, ParameterTypeError, ParameterValueError
from .return_codes import TRName


class DataFeeder:
    """ Data 수신과 관련된 class 입니다. Kiwoom 인스턴스(instance)를 생성자의 매개변수로 받습니다.

    TR과 관련된 자세한 사항은 [키움증권 공식 API 개발
    문서](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) 혹은 KOA StudioSA를 참조하시길 바랍니다.
    """

    def __init__(self, kiwoom, **kwargs):
        self.kiwoom = kiwoom
        for k, v in kwargs:
            setattr(self, k, v)

    def request(self, trCode, **kwargs):
        trCode = trCode.upper()

        if trCode == "OPTKWFID":
            return self.__requestOPTKWFID(**kwargs)

        for k, v in kwargs.items():
            self.kiwoom.setInputValue(k, v)

        trName = getattr(TRName, trCode)
        self.kiwoom.commRqData(trName, trCode, 0, "0000")
        return getattr(self.kiwoom, trCode)

    def __requestOPTKWFID(
        self, arrCode, next, codeCount, rqName="OPTKWFID", scrNo="0000", typeFlag=0
    ):
        """ 복수종목조회 메서드(관심종목조회 메서드라고도 함).

        이 메서드는 setInputValue() 메서드를 이용하여, 사전에 필요한 값을 지정하지 않는다.
        단지, 메서드의 매개변수에서 직접 종목코드를 지정하여 호출한다.

        데이터 수신은 receiveTrData() 이벤트에서 아래 명시한 항목들을 1회 수신하며,
        이후 receiveRealData() 이벤트를 통해 실시간 데이터를 얻을 수 있다.
        복수종목조회 TR 코드는 OPTKWFID 이며, 요청 성공시 아래 항목들의 정보를 얻을 수 있다.

        [종목코드, 종목명, 현재가, 기준가, 전일대비, 전일대비기호, 등락율, 거래량, 거래대금,
        체결량, 체결강도, 전일거래량대비, 매도호가, 매수호가, 매도1~5차호가, 매수1~5차호가,
        상한가, 하한가, 시가, 고가, 저가, 종가, 체결시간, 예상체결가, 예상체결량, 자본금,
        액면가, 시가총액, 주식수, 호가시간, 일자, 우선매도잔량, 우선매수잔량,우선매도건수,
        우선매수건수, 총매도잔량, 총매수잔량, 총매도건수, 총매수건수, 패리티, 기어링, 손익분기,
        잔본지지, ELW행사가, 전환비율, ELW만기일, 미결제약정, 미결제전일대비, 이론가,
        내재변동성, 델타, 감마, 쎄타, 베가, 로]

        1초에 5회 제한

        Parameters
        ----------
        arrCode: str
            종목코드, 세미콜론(;)으로 구분, 한번에 100종목까지 조회가능
        next: int 
            (0: 조회, 1: 남은 데이터 이어서 조회)
            기존 API 문서는 boolean type
        codeCount: int 
            codes에 지정한 종목의 갯수.
        rqName: str
        scrNo: str
        typeFlag: int
          주식과 선물옵션 구분(0: 주식, 3: 선물옵션),
          기존 API 문서에서는 가운데 위치하지만, 맨 뒤로 이동시켰음

        return
        ----------
        str 
            0(정상), -200(시세과부하), -201(조회전문작성 에러)
        """

        self.kiwoom.commKwRqData(arrCode, next, codeCount, rqName, scrNo, typeFlag)
        return getattr(self.kiwoom, "OPTKWFID")

    #############################
    ###### utility methods ######
    #############################

    @property
    def accNo(self):
        return self.kiwoom.accNo

    def getDeposit(self, accNo):
        """ D+2 추정예수금 반환 
        
        Returns
        ----------
        int
        """

        OPW00004 = self.request("OPW00004", **{"계좌번호": accNo})
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

        return self.request("OPT10075", **params)

    def getAccountDict(self, accNo):
        """ 계좌 정보 """

        OPW00004 = self.request("OPW00004", **{"계좌번호": accNo})
        return OPW00004.get("싱글데이터")

    def getInventoryDict(self, accNo):
        """ 현재 보유중인 개별 종목 정보 """

        OPW00004 = self.request("OPW00004", **{"계좌번호": accNo})
        return OPW00004.get("멀티데이터")

    def getInventoryCodes(self, accNo):
        """ 현재 보유중인 종목코드 반환 """

        inventoryDict = self.getInventoryDict(accNo)
        return [d.get("종목코드") for d in inventoryDict]

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

        if not self.kiwoom.connectState:
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

        if not self.kiwoom.connectState:
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
        traSummaryDict = self.request("OPT10074", **params)

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

