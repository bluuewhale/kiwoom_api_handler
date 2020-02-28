from collections import defaultdict
from datetime import datetime

import pandas as pd

from ._errors import *


class DataFeeder:
    def __init__(self, broker):

        self.broker = broker
        self.accNo = self.getAccNo()

        # 각 시장에 상장된 종목 코드
        self.kspCodeList = self.broker.getCodeListByMarket("0")
        self.kdqCodeList = self.broker.getCodeListByMarket("10")
        self.etfCodeList = self.broker.getCodeListByMarket("8")

    ###############################################################
    ############## TR,주문 및 잔고 관련 헬퍼 메서드   ###############
    ###############################################################

    def __OPT10004(self, code):

        if not isinstance(code, str):
            raise ParameterTypeError()

        self.broker.setInputValue("종목코드", code)
        self.broker.commRqData("주식호가요청", "OPT10004", 0, "2000")

    def getOPT10004(self, code):
        """ 주식호가요청 : OPT10004
        지정한 종목의 매도, 매수 호가 및 잔량을 반환합니다.

        params
        ===========================
        code: str, 종목코드

        return
        ============================
        OPT10004: dict
        """

        self.__OPT10004(code)

        OPT10004 = self.broker.OPT10004
        return OPT10004

    def __OPT10005(self, code):

        if not isinstance(code, str):
            raise ParameterTypeError()

        self.broker.setInputValue("종목코드", code)
        self.broker.commRqData("주식일주월시분요청", "OPT10005", 0, "2000")

    def getOPT10005(self, code):
        """ 주식일주월시분요청 : OPT10005
        지정한 일별 OHLCV, 투자주체별 순매수 대금 등을 반환합니다.

        params
        =========================
        code: str, 종목코드
        idx: int or list OPTional, default=None
            반환받을 행을 선택, none일 경우, 전체를 반환

        return
        =========================
        OPT10005: pandas.DataFrame
        """

        self.__OPT10005(code)
        OPT10005 = self.broker.OPT10005
        return OPT10005

    def __OPT10059(self, date, code, gumaekGubun=1, maemaeGubun=0, danwiGubun=1):

        # type check
        if not (
            isinstance(date, str),
            isinstance(code, str),
            isinstance(gumaekGubun, str),
            isinstance(maemaeGubun, str),
            isinstance(danwiGubun, str),
        ):
            raise ParameterTypeError()

        # value check
        if not (len(date) == 8):
            raise ParameterValueError()

        self.broker.setInputValue("일자", date)
        self.broker.setInputValue("종목코드", code)
        self.broker.setInputValue("금액수량구분", gumaekGubun)
        self.broker.setInputValue("매매구분", maemaeGubun)
        self.broker.setInputValue("단위구분", danwiGubun)
        self.broker.commRqData("종목별투자자기관별요청", "OPT10059", 0, "2000")

    def getOPT10059(
        self, date, code, idx=None, gumaekGubun="1", maemaeGubun="0", danwiGubun="1"
    ):
        """ 종목별투자자기관별요청 : 10059
        지정된 종목에 대한 투자주체별 거래량/거래대금

        params
        ======================================================
        date: str, "YYYYMMDD"
        code: str, ex) "005930"
        idx: int, 조회할 이전 영업일 수, defalut=None 전체조회;
        gumaekGubun: str, 금액수량구분, 1:금액 ; 2:수량
        maemaeGubun: str, 매매구분, 0:순매수, 1: 매수, 2:매도
        danwiGubun: str, 단위구분, 1:주, 1000:천주

        return
        ==================================================
        OPT10059: pandas.DataFrame
        """

        self.__OPT10059(date, code, gumaekGubun, maemaeGubun, danwiGubun)
        OPT10059 = self.broker.OPT10059

        if idx is not None:
            OPT10059 = OPT10059.loc[idx]

        return OPT10059

    def __OPT10074(self, accNo, sdate, edate):

        # type check
        if not (isinstance(accNo, str), isinstance(sdate, str), isinstance(edate, str)):
            raise ParameterTypeError()

        # value check
        if not ((len(sdate) == 8), (len(edate) == 8)):
            raise ParameterValueError()

        isNext = 0  # 최초에는 0으로 지정

        while True:

            self.broker.setInputValue("계좌번호", accNo)
            self.broker.setInputValue("시작일자", sdate)
            self.broker.setInputValue("종료일자", edate)
            self.broker.commRqData("일자별실현손익요청", "OPT10074", isNext, "1074")

            isNext = self.broker.isNext
            if not isNext:
                break

    def getOPT10074(self, accNo, sdate, edate=""):
        """ 일자별실현손익요청

        params
        =======================================================
        accNo: str
        sdate: str - start date, YYYYMMDD
        edate: str - end date, YYYYMMDD
        """

        if not edate:
            edate = sdate

        self.__OPT10074(accNo, sdate, edate)
        return self.broker.OPT10074

    def __OPT10075(self, accNo, inquiry, inquiry2):

        # type check
        if not (
            isinstance(accNo, str),
            isinstance(inquiry, str),
            isinstance(inquiry2, str),
        ):
            raise ParameterTypeError()

        # value check
        if not ((inquiry in ["0", "1", "2"]), (inquiry2 in ["0", "1", "2"])):
            raise ParameterValueError()

        isNext = 0  # 최초에는 0으로 지정

        while True:

            self.broker.setInputValue("계좌번호", accNo)
            self.broker.setInputValue("체결구분", inquiry)
            self.broker.setInputValue("매매구분", inquiry2)
            self.broker.commRqData("실시간미체결요청", "OPT10075", isNext, "1075")

            isNext = self.broker.isNext
            if not isNext:
                break

    def getOPT10075(self, accNo, inquiry="1", inquiry2="0"):
        """
        실시간미체결요청

        params
        =======================================================
        accNo: str
        inquiry: str - 0:체결+미체결, 1:미체결, 2:체결
        inquiry2: str - 0:전체, 1:매도, 2:매수
        """

        self.__OPT10075(accNo, inquiry, inquiry2)
        return self.broker.OPT10075

    def __OPTKWFID(self, codes):

        if not isinstance(codes, str):
            raise ParameterTypeError()

        codesCnt = len(codes.split(";"))
        self.broker.commKwRqData(codes, 0, codesCnt, "관심종목정보요청", "1111", typeFlag=0)

    def getOPTKWFID(self, codeList):
        """  관심종목정보요청

        한번에 100 종목 이상까지 조회가능하도록 수정한 헬퍼 매서드입니다.
        요청한 데이터는 self.broker.OPTKWFIDData에 저장됩니다.

        params
        =====================================
        codeList: list, 종목코드가 담긴 list

        return
        ======================================
        data: pandas.DataFrame - row(개별 종목), columns(기준가, 시가 등 63개의 열)
        """

        if not isinstance(codeList, list):
            raise ParameterTypeError

        if not len(codeList):
            raise ParameterValueError

        data = pd.DataFrame()

        cnt = len(codeList)
        step = 100

        for s, e in zip(range(0, cnt, step), range(step, cnt + step, step)):  # 100개씩

            tmpCodeList = codeList[s:e]
            tmpCodes = ";".join(tmpCodeList)

            self.__OPTKWFID(tmpCodes)  # TR 전송
            OPTKWFID = self.broker.OPTKWFID

            data = pd.concat((data, OPTKWFID), axis=0, copy=False)

        data.reset_index(drop=True, inplace=True)
        return data

    def __OPW00001(self, accNo, pswd, inquiry):

        if not (
            isinstance(accNo, str),
            isinstance(pswd, str),
            isinstance(inquiry, str),
        ):
            raise ParameterTypeError()

        self.broker.setInputValue("계좌번호", accNo)
        self.broker.setInputValue("비밀번호", pswd)
        self.broker.setInputValue("조회구분", inquiry)
        self.broker.commRqData("예수금상세현황요청", "OPW00001", 0, "2001")

    def getOPW00001(self, accNo, pswd="", inquiry="2"):
        """예수금상세현황요청(주문가능금액)
        주문가능금액을 반환합니다.

        params
        ===========================================================
        accNo: str
        pswd: str
        inquiry: str - 조회구분 = 1:추정조회, 2:일반조회

        return
        ===========================================================
        OPW00001: dict
        """

        self.__OPW00001(accNo, pswd, inquiry)
        OPW00001 = self.broker.OPW00001

        return OPW00001

    def __OPW00004(self, accNo, pswd):

        if not (isinstance(accNo, str), isinstance(pswd, str)):
            raise ParameterTypeError()

        isNext = 0  # 최초에는 0으로 지정

        while True:

            self.broker.setInputValue("계좌번호", accNo)
            self.broker.setInputValue("비밀번호", pswd)
            self.broker.commRqData("계좌평가현황요청", "OPW00004", isNext, "2004")

            isNext = self.broker.isNext
            if not isNext:
                break

    def getOPW00004(self, accNo, pswd=""):
        """ 계좌평가잔고내역요청
        계좌정보 및 보유종목 정보를 반환합니다.

        params
        =========================================================
        accNo: str
        pswd: str

        return
        =========================================================
        OPW00018 :  Dict, {
            'account' : 싱글데이터
            'stocks' : 멀티데이터
        }
        """

        self.__OPW00004(accNo, pswd)
        OPW00004 = self.broker.OPW00004

        # 종목코드에서 A제거
        for dict in OPW00004["stocks"]:

            dict["종목코드"] = dict["종목코드"].replace("A", "")

        return OPW00004

    def __OPW00007(self, date, accNo, inquiry):

        if not (
            isinstance(date, str),
            isinstance(accNo, str),
            isinstance(inquiry, str),
        ):
            raise ParameterTypeError()

        if not (len(date) == 8):
            raise ParameterValueError()

        isNext = 0  # 최초에는 0으로 지정

        while True:

            self.broker.setInputValue("주문일자", date)  # YYYYMMDD
            self.broker.setInputValue("계좌번호", accNo)
            self.broker.setInputValue("조회구분", inquiry)
            self.broker.commRqData("계좌별주문체결내역상세요청", "OPW00007", isNext, "2007")

            isNext = self.broker.isNext
            if not isNext:
                break

    def getOPW00007(self, date, accNo, inquiry="1"):
        """
        계좌별주문체결내역상세요청

        주문 정보
        params
        ===================================
        date: str - YYYYMMDD
        accNo: str
        inquiry: str - 1:주문순, 2:역순, 3:미체결, 4:체결내역만
        """

        self.__OPW00007(date, accNo, inquiry)
        return self.broker.OPW00007

    ##########################################
    ########## 계좌 조회 관련 메서드 ##########
    ##########################################

    def getAccNo(self):
        return self.broker.getLoginInfo("ACCNO").rstrip(";")

    def getDeposit(self, accNo):
        #  계좌 정보
        OPW00004Data = self.getOPW00004(accNo)

        deposit = int(OPW00004Data["account"]["D+2추정예수금"].replace(",", ""))
        return deposit

    def getUnexOrderDictList(self, accNo):
        inquiry = "1"  # 미체결
        inquiry2 = "0"  # 매수+매도

        unexOrderDictList = self.getOPT10075(accNo, inquiry, inquiry2)
        return unexOrderDictList

    def getAccountDict(self, accNo):
        OPW00004Data = self.getOPW00004(accNo)

        accountDict = OPW00004Data["account"]
        return accountDict

    def getInventoryDictList(self, accNo):
        # 개별 종목 정보
        OPW00004Data = self.getOPW00004(accNo)

        inventoryDictList = OPW00004Data["stocks"]
        return inventoryDictList

    def getInventoryCodeList(self, accNo):
        inventoryDictList = self.getInventoryDictList(accNo)

        codeList = [dict["종목코드"] for dict in inventoryDictList]
        return codeList

    ##########################################
    ############# utility 메서드 #############
    ##########################################

    def getMarketByCode(self, code):
        """
        해당 종목이 상장된 시장정보 반환
        """

        if code in self.kspCodeList:
            return "ksp"

        elif code in self.kdqCodeList:
            return "kdq"

        elif code in self.etfCodeList:
            return "ETF"

        return None

    def dropIssueStock(self, codeList):
        """
        관리종목, 거래정지 종목을 제거합니다.

        return
        =======================
        cleanList
        """

        cleanList = []

        for code in codeList:
            stateList = self.broker.getMasterStockState(code)

            if "관리종목" in stateList or "거래정지" in stateList:
                continue

            cleanList.append(code)

        return cleanList

    def getCodesFromKRX(self, market="all"):
        """ 상장기업 목록 (한국거래소) """

        kspURL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType=stockMkt&searchType=13"
        ksdURL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType=kdqMkt&searchType=13"

        if market == "all":
            kspCodeList = list(
                pd.read_html(kspURL, header=0)[0]["종목코드"].map("{:06d}".format)
            )
            kdqCodeList = list(
                pd.read_html(kdqURL, header=0)[0]["종목코드"].map("{:06d}".format)
            )

            codeList = kspCodeList + kdqCodeList

        if market == "ksp":
            codeList = list(
                pd.read_html(kspURL, header=0)[0]["종목코드"].map("{:06d}".format)
            )

        if market == "kdq":
            codeList = list(
                pd.read_html(kdqURL, header=0)[0]["종목코드"].map("{:06d}".format)
            )

        codeList = [c for c in codeList if not "스팩" in c]  # 스팩 제거
        return codeList

    ### logging 관련 매서드
    def showTradingSummary(self, date):

        # logging할 데이터
        traSummaryDict = self.getOPT10074(self.accNo, date)

        date = "-".join((date[:4], date[4:6], date[6:]))  # YYYY-MM-DD 꼴로 수정

        totalBuy = int(traSummaryDict["총매수금액"])
        totalSell = int(traSummaryDict["총매도금액"])
        netProfit = int(traSummaryDict["실현손익"])
        accoundDict = self.getOPW00004(self.accNo)
        balanceEnd = int(accoundDict["account"]["추정예탁자산"].replace(",", ""))  # 마감 잔고
        balanceStart = balanceEnd - netProfit
        stratRt = balanceEnd / balanceStart - 1

        summaryDict = {
            "TABLE": "trading_summary",
            "BASC_DT": date,
            "STRAT_BUY": totalBuy,
            "STRAT_SELL": totalSell,
            "STRAT_NET_PROFIT": netProfit,
            "BALANCE_START": balanceStart,
            "BALANCE_END": balanceEnd,
            "STRAT_RET_PCT": stratRt,
        }

        self.broker.logger.debug("=" * 70)
        self.broker.logger.debug("{")

        for key, val in loggingDict.items():

            self.broker.logger.debug('"{}" : "{}" ,'.format(key, val))

        self.broker.logger.debug("}")
        self.broker.logger.debug("=" * 70)

        return summaryDict
