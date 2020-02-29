from collections import deque, defaultdict
from datetime import datetime as dt
import os
import sys
import time

import pandas as pd
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop
from PyQt5.QtWidgets import QApplication

from ._utility import *
from ._errors import *
from ._logger import *


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

        # 전략코드
        self.stratID = ""

        # Loop 변수
        # 비동기 방식으로 동작되는 이벤트를 동기화(순서대로 동작) 시킬 때
        self.loginLoop = None
        self.requestLoop = None
        self.orderLoop = None
        self.conditionLoop = None

        # 서버구분
        self.serverStatus = None

        # 연속조회구분
        self.isNext = 0

        # logging 클래스
        self.__initLogger()

        # API 요청 제한 관리 Queue (1초 5회, 1시간 1,000회)
        self.requestDelayCheck = APIDelayCheck(logger=self.logger)
        self.orderDelayCheck = APIDelayCheck(logger=self.logger)

        # 서버에서 받은 메시지
        self.msg = ""

        # Event 처리
        self.OnEventConnect.connect(self.eventConnect)
        self.OnReceiveTrData.connect(self.eventReceiveTrData)
        self.OnReceiveChejanData.connect(self.eventReceiveChejanData)
        self.OnReceiveMsg.connect(self.eventReceiveMsg)

    def __initLogger(self):
        """ logger 객체 생성 """

        try:
            os.mkdir("log")
        except FileExistsError:
            pass

        today = dt.now().strftime("%Y%m%d")
        try:
            os.mkdir("log/{}".format(today))
        except FileExistsError:
            pass

        filePath = "log/{}/kiwoom_log.txt".format(today)
        self.logger = Logger(name="Kiwoom", filePath=filePath, streamHandler=True)

    ###############################################################
    ################### 이벤트 발생 시 메서드   #####################
    ###############################################################

    def eventConnect(self, returnCode):
        """ 통신 연결 상태 변경시 이벤트
        returnCode가 0이면 로그인 성공
        그 외에는 ReturnCode 클래스 참조.

        params
        =======================================
        returnCode: int - 0이면 로그인 성공, 이외에는 로그인 실패
        """

        t = dt.now()

        if returnCode == ReturnCode.OP_ERR_NONE:

            msg = "{} EVENT: Successfully Login".format(t)

            self.logger.debug("=" * 70)
            self.logger.debug(msg)
            self.logger.debug("=" * 70)

        else:

            errorName = ReturnCode.CAUSE[returnCode]
            msg = "{} EVENT: Connection failed => {}".format(t, errorName)

            self.logger.debug("=" * 70)
            self.logger.debug(msg)
            self.logger.debug("=" * 70)

        # commConnect() 메서드에 의해 생성된 루프를 종료시킨다.
        # 로그인 후, 통신이 끊길 경우를 대비해서 예외처리함.
        try:
            self.loginLoop.exit()
        except AttributeError:
            pass

    def eventReceiveMsg(self, scrNo, rqName, trCode, msg):
        """ 수신 메시지 이벤트
        서버로 어떤 요청을 했을 때(로그인, 주문, 조회 등),
        그 요청에 대한 처리내용을 전달해준다.

        params
        ===========================================
        scrNo: str,
          화면번호(4자리, 사용자 정의,
          서버에 조회나 주문을 요청할 때 이 요청을 구별하기 위한 키값)
        rqName: str, TR 요청명(사용자 정의)
        trCode: str
        msg: str, 서버로 부터의 메시지
        """

        self.logger.debug(msg)

    def eventReceiveTrData(
        self,
        scrNo,
        rqName,
        trCode,
        recordName,
        inquiry,
        deprecated1,
        deprecated2,
        deprecated3,
        deprecated4,
    ):
        """
        TR 수신 이벤트시 실행되는 매서드

        조회요청 응답을 받거나 조회데이터를 수신했을 때 호출됩니다.
        rqName과 trCode는 getCommData() 메소드의 매개변수와 매핑되는 값 입니다.

        요청한 TR에 대해 수신된 데이터는 self.{trCode}Data에 저장됩니다.
        수신된 데이터는 모두 str 타입으로 사용자가 원하는 형태로 2차 가공이 필요합니다.

        trCode 및 rqName과 관련된 자세한 내용은 OPEN API+ 개발가이드 및
        KOA StudioSA를 참고하시기 바랍니다.


        params
        ===================================================================
        scrNo: str - 화면번호(4자리)
        rqName: str - TR 요청명(commRqData() 메소드 호출시 사용된 rqName)
        trCode: str
        recordName: str
        inquiry: str - 조회("0" or "": 남은 데이터 없음, '2': 남은 데이터 있음)
        """

        self.isNext = 0 if ((inquiry == "0") or (inquiry == "")) else 2  # 추가조회 여부

        # logging
        orderNo = self.getCommData(trCode, "", 0, "주문번호")

        self.logger.debug("=" * 70)
        self.logger.debug("{")
        self.logger.debug('"TIME" : "{}",'.format(dt.now()))
        self.logger.debug('"BASC_DT" : "{}",'.format(dt.now().strftime("%Y%m%d")))
        self.logger.debug('"EVENT": "eventReceiveTrData",')
        self.logger.debug('"REQUEST_NAME": "{}",'.format(rqName))
        self.logger.debug('"TR_CODE": "{}",'.format(trCode))
        self.logger.debug('"ORDER_NO": "{}",'.format(orderNo))
        self.logger.debug("}")
        self.logger.debug("=" * 70)

        # 주문 이벤트인 경우, loop에서 나옴
        try:
            self.orderLoop.exit()
        except AttributeError:
            pass

        try:

            # OPT10004 : 주식호가요청
            if trCode == "OPT10004":

                self.OPT10004 = {}
                keyList = TrKeyList.OPT10004["멀티데이터"]

                for key in keyList:

                    value = self.getCommData(trCode, "주식호가요청", 0, key)
                    self.OPT10004[key] = value

            # OPT10005 : 주식일주월시분요청
            elif trCode == "OPT10005":

                OPT10005 = defaultdict(lambda: [])

                n = self.getRepeatCnt(trCode, rqName)
                keyList = TrKeyList.OPT10005["멀티데이터"]

                for i in range(n):
                    for key in keyList:

                        value = self.getCommData(trCode, "주식일주월시분요청", i, key)
                        OPT10005[key].append(value)

                self.OPT10005 = pd.DataFrame(OPT10005, columns=keyList, dtype=object)

            # OPT10059 : 종목별투자자기관별요청
            elif trCode == "OPT10059":

                OPT10059 = defaultdict(lambda: [])

                n = self.getRepeatCnt(trCode, rqName)
                keyList = TrKeyList.OPT10059["멀티데이터"]

                for i in range(n):
                    for key in keyList:

                        value = self.getCommData(
                            trCode, "종목별투자자기관별요청", i, key
                        )  # 중첩 리스트

                        OPT10059[key].append(value)

                self.OPT10059 = pd.DataFrame(OPT10059, columns=keyList, dtype=object)

            # OPT10074 : 일자별실현손익요청
            elif trCode == "OPT10074":

                self.OPT10074 = {"acc": {}, "stocks": {}}

                # 싱글데이터 : 계좌 총합
                keyList = TrKeyList.OPT10074["싱글데이터"]

                for key in keyList:

                    value = self.getCommData(trCode, rqName, 0, key)
                    self.OPT10074["acc"][key] = value

                # 멀티데이터: 개별 종목
                cnt = self.getRepeatCnt(trCode, rqName)
                keyList = TrKeyList.OPT10074["멀티데이터"]

                for i in range(cnt):
                    for key in keyList:

                        value = self.getCommData(trCode, rqName, i, key)
                        self.OPT10074["stocks"][key] = value

            # OPT10075 : 실시간미체결요청
            elif trCode == "OPT10075":

                self.OPT10075 = []

                cnt = self.getRepeatCnt(trCode, rqName)
                keyList = TrKeyList.OPT10075["멀티데이터"]

                for i in range(cnt):

                    tmpDict = {}

                    for key in keyList:

                        value = self.getCommData(trCode, rqName, i, key)
                        tmpDict[key] = value

                    self.OPT10075.append(tmpDict)

            # OPTKWFID : 관심종목정보요청
            if trCode == "OPTKWFID":

                keyList = TrKeyList.OPTKWFID["멀티데이터"]

                self.OPTKWFID = self.getCommDataEx(trCode, "관심종목정보")
                self.OPTKWFID = pd.DataFrame(
                    self.OPTKWFID, columns=keyList, dtype=object
                )

            # OPW00001 : 예수금상세현황요청
            elif trCode == "OPW00001":

                self.OPW00001 = {}
                keyList = TrKeyList.OPW00001["싱글데이터"]

                for key in keyList:

                    value = self.getCommData(trCode, rqName, 0, key)
                    self.OPW00001[key] = value

            # OPW00004 : 계좌평가현황요청
            elif trCode == "OPW00004":

                self.OPW00004 = {"acc": {}, "stocks": []}  # 보유종목 정보

                # 계좌평가현황 (싱글 데이터)
                keyList = TrKeyList.OPW00004["싱글데이터"]

                for key in keyList:

                    value = self.getCommData(trCode, rqName, 0, key)
                    self.OPW00004["acc"][key] = value

                # 보유 종목 정보 (멀티 데이터)
                cnt = self.getRepeatCnt(trCode, rqName)
                keyList = TrKeyList.OPW00004["멀티데이터"]

                for i in range(cnt):
                    stockInfoDict = {}

                    for key in keyList:

                        value = self.getCommData(trCode, rqName, i, key)
                        stockInfoDict[key] = value

                    self.OPW00004["stocks"].append(stockInfoDict)

            # OPW00007 : 계좌별주문체결내역상세요청
            elif trCode == "OPW00007":

                self.OPW00007 = []

                cnt = self.getRepeatCnt(trCode, rqName)
                keyList = TrKeyList.OPW00007["멀티데이터"]

                for i in range(cnt):
                    tmpDict = {}

                    for key in keyList:

                        value = self.getCommData(trCode, rqName, i, key)
                        tmpDict[key] = value

                    self.OPW00007.append(tmpDict)

        # error 발생시 logging
        except Exception as e:
            self.logger.error(
                "{} eventReceiveTrData() {}: {}, {} ".format(
                    dt.now(), e, rqName, trCode
                )
            )

        finally:
            try:
                self.requestLoop.exit()
            except AttributeError:
                pass

    def eventReceiveChejanData(self, gubun, itemCnt, fidList):
        """
        주문 접수/확인 수신시 이벤트
        주문요청후 주문접수, 체결통보, 잔고통보를 수신할 때 마다 호출됩니다.

        params
        =================================================================
        gubun: str - 체결구분('0': 주문접수/주문체결, '1': 잔고통보, '3': 특이신호)
        itemCnt: int - fid의 갯수
        fidList: str - fidList 구분은 ;(세미콜론) 이다.
        """

        # Logging
        fids = fidList.split(";")

        # logging
        self.logger.debug("=" * 70)
        self.logger.debug("{")

        self.logger.debug('"TIME" : "{}",'.format(dt.now()))
        self.logger.debug('"EVENT": "eventReceiveChejanData",')
        self.logger.debug('"GUBUN" : "{}", '.format(gubun))  # '0': 주문접수/주문체결 '1':잔고통보
        self.logger.debug('"BASC_DT" : "{}", '.format(dt.now().strftime("%Y%m%d")))
        self.logger.debug('"STRAT_ID": "{}",'.format(self.stratID))

        for fid in fids:
            try:
                fidName = FidList.CHEJAN[fid]

            except KeyError:
                fidName = fid

            data = self.getChejanData(fid)

            if fid == "302":  # 종목명은 앞뒤 공백이 존재함
                data = data.strip()

            self.logger.debug('"{}": "{}",'.format(fidName, data))

        self.logger.debug("}")
        self.logger.debug("=" * 70)

    ###############################################################
    #################### 로그인 관련 메서드   ######################
    ###############################################################

    def commConnect(self):
        """
        로그인 시도
        """

        self.dynamicCall("CommConnect()")

        self.loginLoop = QEventLoop()  # QEventLoop를 생성해서 비동기로 작업이 처리되는 것을 방지
        self.loginLoop.exec_()  # eventConnect에서 loop를 종료시킨다.

    def getConnectState(self):
        """
        현재 접속상태를 반환합니다.

        return
        =============================
        state: int - 0(미연결), 1(연결)
        """

        state = self.dynamicCall("GetConnectState()")
        return state

    def getLoginInfo(self, tag, isConnectState=False):
        """
        사용자의 tag에 해당하는 정보를 반환한다.

        tag에 올 수 있는 값은 아래와 같다.
        ACCOUNT_CNT, ACCNO, USER_ID, USER_NAME, GetServerGubun

        params
        =================================================
        tag: string
        isConnectState: bool - 접속상태을 확인할 필요가 없는 경우 True로 설정.

        return
        =================================================
        info : string - 입력한 tag에 대응하는 정보
        """

        if not isConnectState:
            if not self.getConnectState():  # 1: 연결, 0: 미연결
                raise KiwoomConnectError()

        if not isinstance(tag, str):
            raise ParameterTypeError()

        if tag not in [
            "ACCOUNT_CNT",
            "ACCNO",
            "USER_ID",
            "USER_NAME",
            "GetServerGubun",
        ]:
            raise ParameterValueError()

        if tag == "GetServerGubun":
            info = self.getServerGubun()
        else:
            info = self.dynamicCall('GetLoginInfo("{}")'.format(tag))
        return info

    def getServerGubun(self):
        """
        서버구분 정보를 반환한다.

        return
        =====================================
        server_status: string ("1": 모의투자서버, else: 실서버)
        """

        serverStatus = self.dynamicCall(
            "KOA_Functions(QString, QString)", "GetServerGubun", ""
        )
        return serverStatus

    ###############################################################
    ################### TR(조회) 관련 메서드   #####################
    ## 시세조회, 관심종목 조회, 조건검색 등 합산 조회수 1초 5회 제한 ##
    ###############################################################

    # 점검방법은 CommRqData()함수와 CommKwRqData()함수를 이용한 조회횟수를
    # 합산하는 것으로 연속조회 역시 CommRqData()를 이용므로 합산됩니다.

    def setInputValue(self, key, value):
        """
        TR 전송에 필요한 값을 설정한다.

        params
        =======================================
        key: str - TR에 명시된 input 이름, ex) 계좌번호, 종목코드
        value: str - key에 해당하는 값, ex) 88231524, 005930
        """

        if not (isinstance(key, str) and isinstance(value, str)):
            raise ParameterTypeError()

        self.dynamicCall("SetInputValue(QString, QString)", key, value)

    def commRqData(self, rqName, trCode, inquiry, scrNo):
        """
        키움서버에 TR 요청을 한다.
        요청한 데이터는 데이터 수신 이벤트 발생 시 eventReceiveTrData 매서드에서 처리

        1초에 5회 제한

        params
        ============================================================
        rqName: string - TR 요청명(사용자 정의)
        trCode: string
        inquiry: int - 조회(0: 조회, 2: 남은 데이터 이어서 요청)
        scrNo: string - 화면번호(4자리)

        return
        ============================================================
        returnCode: str - 0(정상), -200(시세과부하), -201(조회전문작성 에러)
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not (
            isinstance(rqName, str)
            and isinstance(trCode, str)
            and isinstance(inquiry, int)
            and isinstance(scrNo, str)
        ):
            raise ParameterTypeError()

        # API 제한 확인
        self.requestDelayCheck.checkDelay()

        returnCode = self.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            rqName,
            trCode,
            inquiry,
            scrNo,
        )

        if returnCode != ReturnCode.OP_ERR_NONE:  # 0이외엔 실패
            self.logger.error(
                "{} commRqData {} Request Failed!, ERROR CODE: {}".format(
                    dt.now(), rqName, returnCode
                )
            )
            raise KiwoomProcessingError(
                "commRqData(): {}".format(ReturnCode.CAUSE[returnCode])
            )

        # logging
        self.logger.debug("{}  commRqData {}".format(dt.now(), rqName))

        # 루프 생성: eventReceiveTrData() 메서드에서 루프를 종료시킨다.
        self.requestLoop = QEventLoop()
        self.requestLoop.exec_()

    def getRepeatCnt(self, trCode, rqName):
        """
        서버로 부터 전달받은 데이터의 갯수를 리턴합니다.(멀티데이터의 갯수)
        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.

        키움 OpenApi+에서는 데이터를 싱글데이터와 멀티데이터로 구분합니다.
        싱글데이터란, 서버로 부터 전달받은 데이터 내에서, 중복되는 키(항목이름)가
        하나도 없을 경우. 예를들면, 데이터가 '종목코드', '종목명', '상장일',
        '상장주식수' 처럼 키(항목이름)가 중복되지 않는 경우를 말합니다.

        반면 멀티데이터란, 서버로 부터 전달받은 데이터 내에서, 일정 간격으로
        키(항목이름)가 반복될 경우를 말합니다. 예를들면, 10일간의 일봉데이터를
        요청할 경우 '종목코드', '일자', '시가', '고가', '저가' 이러한 항목이
        10번 반복되는 경우입니다. 이러한 멀티데이터의 경우 반복 횟수(=데이터의 갯수)
        만큼, 루프를 돌면서 처리하기 위해 이 메서드를 이용하여 멀티데이터의 갯수를
        얻을 수 있습니다.

        차트조회는 한번에 최대 900개 데이터를 수신할 수 있습니다.

        params
        ============================================================
        trCode: str
        rqName: str

        return
        ============================================================
        cnt : int, 서버에서 전달받은 데이터 갯수
        """

        if not (isinstance(trCode, str) and isinstance(rqName, str)):
            raise ParameterTypeError()

        cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trCode, rqName)
        return cnt

    def getCommData(self, trCode, rqName, index, key):
        """

        데이터 획득 메서드
        evnetReceiveTrData() 이벤트 메서드가 호출될 때, 그 안에서
        조회데이터를 얻어오는 메서드입니다. 이 함수는 반드시 OnReceiveTRData()
        이벤트가 호출될때 그 안에서 사용해야 합니다.

        싱글데이터는 index=0
        멀티데이터는 getRepeatCnt 매서드로 데이터 수를 확인한 후,
        loop문으로 index를 1씩 늘리며 접근

        params
        ========================================================
        trCode: string
        rqName: string - TR 요청명(commRqData() 메소드 호출시 사용된 rqName)
        index: int
        key: string - 수신 데이터에서 얻고자 하는 값의 키(출력항목이름)

        return
        =========================================================
        data: string
        """

        if not (
            isinstance(trCode, str)
            and isinstance(rqName, str)
            and isinstance(index, int)
            and isinstance(key, str)
        ):
            raise ParameterTypeError()

        data = self.dynamicCall(
            "GetCommData(QString, QString, int, QString)", trCode, rqName, index, key
        )

        return data.strip()

    def getCommDataEx(self, trCode, multiDataName):
        """
        멀티 데이터 획득

        조회 수신데이터 크기가 큰 차트데이터를 한번에 가져올 목적으로 만든 전용함수입니다.
        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.

        params
        ==================================================================
        trCode: string
        multiDataName: string,  KOA에 명시된 멀티데이터명

        return
        ==================================================================
        data: list,  중첩리스트
        """

        if not (isinstance(trCode, str) and isinstance(multiDataName, str)):
            raise ParameterTypeError()

        data = self.dynamicCall(
            "GetCommDataEx(QString, QString)", trCode, multiDataName
        )
        return data

    def commKwRqData(self, arrCode, next, codeCount, rqName, scrNo, typeFlag=0):
        """
        복수종목조회 메서드(관심종목조회 메서드라고도 함).

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

        params
        ==================================================================================
        arrCode: string - 한번에 100종목까지 조회가능, 세미콜론(;)으로 구분.
        next: int (0: 조회, 1: 남은 데이터 이어서 조회)
          - 기존 API 문서는 boolean type
        codeCount: int - codes에 지정한 종목의 갯수.
        rqName: string
        scrNo: string
        typeFlag: int
          주식과 선물옵션 구분(0: 주식, 3: 선물옵션),
          기존 API 문서에서는 가운데 위치하지만, 맨 뒤로 이동시켰음

        return
        ===================================================================================
        returnCode: str - 0(정상), -200(시세과부하), -201(조회전문작성 에러)
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not (
            isinstance(arrCode, str)
            and isinstance(next, int)
            and isinstance(codeCount, int)
            and isinstance(rqName, str)
            and isinstance(scrNo, str)
            and isinstance(typeFlag, int)
        ):

            raise ParameterTypeError()

        # API 제한 확인
        self.requestDelayCheck.checkDelay()

        returnCode = self.dynamicCall(
            "CommKwRqData(QString, QBoolean, int, int, QString, QString)",
            arrCode,
            next,
            codeCount,
            typeFlag,
            rqName,
            scrNo,
        )

        if returnCode != ReturnCode.OP_ERR_NONE:
            self.logger.error(
                "{} commKwRqData {} Request Failed!".format(dt.now(), rqName)
            )
            raise KiwoomProcessingError(
                " {} commKwRqData(): {} ".format(dt.now(), ReturnCode.CAUSE[returnCode])
            )

        # logging
        self.logger.debug("{}  commKwRqData {}".format(dt.now(), rqName))

        # 루프 생성: receiveTrData() 메서드에서 루프를 종료시킨다.
        self.requestLoop = QEventLoop()
        self.requestLoop.exec_()

    ###############################################################
    ################### 주문과 잔고처리 관련 메서드 #################
    ########################## 1초 5회 제한 ########################
    ###############################################################

    def sendOrder(
        self,
        rqName,
        scrNo,
        accNo,
        orderType,
        code,
        qty,
        price,
        hogaType,
        originOrderNo,
    ):

        """
        주식 주문 메서드

        sendOrder() 메소드 실행시,
        OnReceiveMsg, OnReceiveTrData, OnReceiveChejanData 이벤트가 발생한다.
        이 중, 주문에 대한 결과 데이터를 얻기 위해서는 OnReceiveChejanData 이벤트를 통해서 처리한다.

        OnReceiveTrData 이벤트를 통해서는 주문번호를 얻을 수 있는데,
        주문후 OnReceiveTrData에서 주문번호가 ''공백으로 전달되면 주문접수 실패를 의미한다.

        params
        =======================================================================
        rqName: string - 주문 요청명(사용자 정의)
        scrNo: string - 화면번호(4자리)
        accNo: string - 계좌번호(10자리)
        orderType: int
            주문유형(1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도정정)
        code: string - 종목코드
        qty: int - 주문수량
        price: int - 주문단가
        hogaType: string
            거래구분(00: 지정가, 03: 시장가, 05: 조건부지정가, 06: 최유리지정가, 그외에는 api 문서참조)
        originOrderNo: string
            원주문번호(신규주문에는 공백, 정정및 취소주문시 원주문번호를 입력합니다.)

        ※  시장가, 최유리지정가, 최우선지정가, 시장가IOC, 최유리IOC,시장가FOK,
            최유리FOK, 장전시간외, 장후시간외 주문시 주문가격을 입력하지 않습니다.
        """

        # server connection check
        if not self.getConnectState():
            raise KiwoomConnectError()

        # API 제한 확인
        self.orderDelayCheck.checkDelay()

        # parameter type check
        if not (
            isinstance(rqName, str)
            and isinstance(scrNo, str)
            and isinstance(accNo, str)
            and isinstance(orderType, int)
            and isinstance(code, str)
            and isinstance(qty, int)
            and isinstance(price, int)
            and isinstance(hogaType, str)
            and isinstance(originOrderNo, str)
        ):
            raise ParameterTypeError()

        # parameter value check
        try:
            orderType = OrderType.TYPE[orderType]
        except KeyError:
            errMsg = "orderType must be in [1, 2, 3, 4, 5, 6], but got {}".format(
                orderType
            )
            raise ParameterValueError(errMsg)

        returnCode = self.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            [
                rqName,
                scrNo,
                accNo,
                orderType,
                code,
                qty,
                price,
                hogaType,
                originOrderNo,
            ],
        )

        # returnCode check
        try:
            returnMsg = ReturnCode.CAUSE[returnCode]
        except KeyError:
            errMsg = "received an unexpected return code: {}".format(returnMsg)
            raise KiwoomProcessingError(errMsg)

        if returnCode != ReturnCode.OP_ERR_NONE:
            raise KiwoomProcessingError(
                "received error msg from server: {}".format(returnMsg)
            )

        self.logger.info(
            "{} sendOrder() : Code:{}, Price:{}, Qty:{}, orderType={}".format(
                dt.now(), code, price, qty, orderType
            )
        )

        # receiveTrData() 에서 루프종료
        self.orderLoop = QEventLoop()
        self.orderLoop.exec_()

    def getChejanData(self, fid):
        """ 주문접수, 주문체결, 잔고정보를 얻어오는 메서드
        이 메서드는 receiveChejanData() 이벤트 메서드가 호출될 때
        그 안에서 사용해야 합니다.

        params
        ===========================
        fid: str

        return
        ===========================
        data: str
        """

        if not isinstance(fid, str):
            raise ParameterTypeError()

        data = self.dynamicCall('GetChejanData("{}")'.format(fid))
        return data


class APIDelayCheck:
    def __init__(self, logger=None):
        """
        Kiwoom API 요청 제한을 피하기 위해 요청을 지연하는 클래스입니다.

        params
        =================================
        logger: Kiwoom Class의 logger - defalut=None
        """
        # 1초에 5회, 1시간에 1,000회 제한
        self.rqHistory = deque(maxlen=1000)

        if logger:
            self.logger = logger

    def checkDelay(self):
        """
        TR 1초 5회 제한을 피하기 위해, 조회 요청을 지연합니다.
        """
        time.sleep(0.1)  # 기본적으로 요청 간에는 0.1초 delay

        if len(self.rqHistory) < 5:
            pass
        else:
            # 1초 delay (5회)
            oneSecRqTime = self.rqHistory[-4]

            # 1초 이내에 5번 요청하면 delay
            while True:
                RqInterval = time.time() - oneSecRqTime
                if RqInterval > 1:
                    break

        # 1hour delay (1000회)
        if len(self.rqHistory) == 1000:
            oneHourRqTime = self.rqHistory[0]
            oneHourRqInterval = time.time() - oneHourRqTime

            if oneHourRqInterval < 3610:
                delay = 3610 - oneHourRqInterval

                if self.logger:
                    self.logger.warning(
                        "{} checkRequestDelay: Request delayed by {} seconds".format(
                            dt.now(), delay
                        )
                    )

                    time.sleep(delay)

        # 새로운 request 시간 기록
        self.rqHistory.append(time.time())


class OrderType(object):
    """키움 OPEN API+ sendOrder의 orderType에 대응되는 주문"""

    TYPE = {
        1: "신규매수",
        2: "신규매도",
        3: "매수취소",
        4: "매도취소",
        5: "매수정정",
        6: "매도정정",
    }


class ReturnCode(object):
    """ 키움 OpenApi+ 함수들이 반환하는 값 """

    OP_ERR_NONE = 0  # 정상처리
    OP_ERR_FAIL = -10  # 실패
    OP_ERR_LOGIN = -100  # 사용자정보교환실패
    OP_ERR_CONNECT = -101  # 서버접속실패
    OP_ERR_VERSION = -102  # 버전처리실패
    OP_ERR_FIREWALL = -103  # 개인방화벽실패
    OP_ERR_MEMORY = -104  # 메모리보호실패
    OP_ERR_INPUT = -105  # 함수입력값오류
    OP_ERR_SOCKET_CLOSED = -106  # 통신연결종료
    OP_ERR_SISE_OVERFLOW = -200  # 시세조회과부하
    OP_ERR_RQ_STRUCT_FAIL = -201  # 전문작성초기화실패
    OP_ERR_RQ_STRING_FAIL = -202  # 전문작성입력값오류
    OP_ERR_NO_DATA = -203  # 데이터없음
    OP_ERR_OVER_MAX_DATA = -204  # 조회가능한종목수초과
    OP_ERR_DATA_RCV_FAIL = -205  # 데이터수신실패
    OP_ERR_OVER_MAX_FID = -206  # 조회가능한FID수초과
    OP_ERR_REAL_CANCEL = -207  # 실시간해제오류
    OP_ERR_ORD_WRONG_INPUT = -300  # 입력값오류
    OP_ERR_ORD_WRONG_ACCTNO = -301  # 계좌비밀번호없음
    OP_ERR_OTHER_ACC_USE = -302  # 타인계좌사용오류
    OP_ERR_MIS_2BILL_EXC = -303  # 주문가격이20억원을초과
    OP_ERR_MIS_5BILL_EXC = -304  # 주문가격이50억원을초과
    OP_ERR_MIS_1PER_EXC = -305  # 주문수량이총발행주수의1%초과오류
    OP_ERR_MIS_3PER_EXC = -306  # 주문수량이총발행주수의3%초과오류
    OP_ERR_SEND_FAIL = -307  # 주문전송실패
    OP_ERR_ORD_OVERFLOW = -308  # 주문전송과부하
    OP_ERR_MIS_300CNT_EXC = -309  # 주문수량300계약초과
    OP_ERR_MIS_500CNT_EXC = -310  # 주문수량500계약초과
    OP_ERR_ORD_WRONG_ACCTINFO = -340  # 계좌정보없음
    OP_ERR_ORD_SYMCODE_EMPTY = -500  # 종목코드없음

    CAUSE = {
        0: "정상처리",
        -10: "실패",
        -100: "사용자정보교환실패",
        -102: "버전처리실패",
        -103: "개인방화벽실패",
        -104: "메모리보호실패",
        -105: "함수입력값오류",
        -106: "통신연결종료",
        -200: "시세조회과부하",
        -201: "전문작성초기화실패",
        -202: "전문작성입력값오류",
        -203: "데이터없음",
        -204: "조회가능한종목수초과",
        -205: "데이터수신실패",
        -206: "조회가능한FID수초과",
        -207: "실시간해제오류",
        -300: "입력값오류",
        -301: "계좌비밀번호없음",
        -302: "타인계좌사용오류",
        -303: "주문가격이20억원을초과",
        -304: "주문가격이50억원을초과",
        -305: "주문수량이총발행주수의1%초과오류",
        -306: "주문수량이총발행주수의3%초과오류",
        -307: "주문전송실패",
        -308: "주문전송과부하",
        -309: "주문수량300계약초과",
        -310: "주문수량500계약초과",
        -340: "계좌정보없음",
        -500: "종목코드없음",
    }


class TrKeyList(object):

    OPTKWFID = {
        "멀티데이터": [
            "종목코드",
            "종목명",
            "현재가",
            "기준가",
            "전일대비",  # 5
            "전일대비기호",
            "등락율",
            "거래량",
            "거래대금",
            "체결량",  # 10
            "체결강도",
            "전일거래량대비",
            "매도호가",
            "매수호가",
            "매도1차호가",  # 15
            "매도2차호가",
            "매도3차호가",
            "매도4차호가",
            "매도5차호가",
            "매수1차호가",  # 20
            "매수2차호가",
            "매수3차호가",
            "매수4차호가",
            "매수5차호가",
            "상한가",  # 25
            "하한가",
            "시가",
            "고가",
            "저가",
            "종가",  # 30
            "체결시간",
            "예상체결가",
            "예상체결량",
            "자본금",
            "액면가",  # 35
            "시가총액",
            "주식수",
            "호가시간",
            "일자",
            "우선매도잔량",  # 40
            "우선매수잔량",
            "우선매도건수",
            "우선매수건수",
            "총매도잔량",
            "총매수잔량",  # 45
            "총매도건수",
            "총매수건수",
            "패리티",
            "기어링",
            "손익분기",  # 50
            "잔본지지",
            "ELW행사가",
            "전환비율",
            "ELW만기일",
            "미결제약정",  # 55
            "미결제전일대비",
            "이론가",
            "내재변동성",
            "델타",
            "감마",  # 60
            "쎄타",
            "베가",
            "로",  # 63
        ]
    }

    OPT10004 = {
        "멀티데이터": [
            # 매도호가 관련
            "매도최우선호가",
            "매도2차선호가",
            "매도3차선호가",
            "매도4차선호가",
            "매도5차선호가",
            "매도6차선호가",
            "매도7차선호가",
            "매도8차선호가",
            "매도9차선호가",
            "매도10차선호가",
            "매도최우선잔량",
            "매도2차선잔량",
            "매도3차선잔량",
            "매도4차선잔량",
            "매도5차선잔량",
            "매도6차선잔량",
            "매도7차선잔량",
            "매도8차선잔량",
            "매도9차선잔량",
            "매도10차선잔량",
            "매도1차선잔량대비",
            "매도2차선잔량대비",
            "매도3차선잔량대비",
            "매도4차선잔량대비",
            "매도5차선잔량대비",
            "매도6차선잔량대비",
            "매도7차선잔량대비",
            "매도8차선잔량대비",
            "매도9차선잔량대비",
            "매도10차선잔량대비",
            # 매수호가 관련
            "매수최우선호가",
            "매수2차선호가",
            "매수3차선호가",
            "매수4차선호가",
            "매수5차선호가",
            "매수6차선호가",
            "매수7차선호가",
            "매수8차선호가",
            "매수9차선호가",
            "매수10차선호가",
            "매수최우선잔량",
            "매수2차선잔량",
            "매수3차선잔량",
            "매수4차선잔량",
            "매수5차선잔량",
            "매수6차선잔량",
            "매수7차선잔량",
            "매수8차선잔량",
            "매수9차선잔량",
            "매수10차선잔량",
            "매수1차선잔량대비",
            "매수2차선잔량대비",
            "매수3차선잔량대비",
            "매수4차선잔량대비",
            "매수5차선잔량대비",
            "매수6차선잔량대비",
            "매수7차선잔량대비",
            "매수8차선잔량대비",
            "매수9차선잔량대비",
            "매수10차선잔량대비",
            # 총잔량
            "총매도잔량",
            "총매수잔량",
            "총매도잔량직전대비",
            "총매수잔량직전대비",
            # 시간외
            "시간외매도잔량",
            "시간외매수잔량",
            "시간외매도잔량대비",
            "시간외매수잔량대비",
        ]
    }

    OPT10005 = {
        "멀티데이터": [
            "날짜",
            "시가",
            "고가",
            "저가",
            "종가",
            "대비",
            "등락률",
            "거래량",
            "거래대금",
            "체결강도",
            "외인보유",
            "외인비중",
            "외인순매수",
            "기관순매수",
            "개인순매수",
            "외국계",
            "신용잔고율",
            "프로그램",
        ]
    }

    OPT10059 = {
        "멀티데이터": [
            "일자",
            "현재가",
            "대비기호",
            "전일대비",
            "등락율",
            "누적거래량",
            "누적거래대금",
            "개인투자자",
            "기관계",
            "외국인투자자",
            "금융투자",
            "보험",
            "투신",
            "기타금융",
            "은행",
            "연기금등",
            "사모펀드",
            "국가",
            "기타법인",
            "내외국인",
        ]
    }
    OPT10074 = {
        "싱글데이터": ["총매수금액", "총매도금액", "실현손익", "매매수수료", "매매세금"],
        "멀티데이터": ["일자", "매수금액", "매도금액", "당일매도손익", "당일매매수수료", "당일매매세금"],
    }
    OPT10075 = {
        "멀티데이터": [
            "계좌번호",
            "주문번호",
            "관리사번",
            "종목코드",
            "업무구분",
            "주문상태",
            "종목명",
            "주문수량",
            "주문가격",
            "미체결수량",
            "체결누계금액",
            "원구문번호",
            "주문구분",
            "매매구분",
            "시간",
            "체결번호",
            "체결가",
            "체결량",
            "현재가",
            "매도호가",
            "매수호가",
            "단위체결가",
            "단위체결량",
            "당일매매수수료",
            "당일매매세금",
            "개인투자자",
        ]
    }
    OPW00001 = {
        "싱글데이터": [
            "예수금",
            "주식증거금현금",
            "수익증권증거금현금",
            "익일수익증권매도정산대금",
            "해외주식원화대용설정금",
            "신용보증금현금",
            "신용담보금현금",
            "추가담보금현금" "기타증거금",
            "미수확보금",
            "공매도대금",
            "신용설정평가금",
            "수표입금액",
            "기타수표입금액",
            "신용담보재사용",
            "코넥스기본예탁금",
            "ELW예탁평가금",
            "신용대주권리예정금액",
            "생계형가입금액",
            "생계형입금가능금액",
            "대용금평가금액(합계)",
            "잔고대용평가금액",
            "위탁대용잔고평가금액",
            "수익증권대용평가금액",
            "위탁증거금대용",
            "신용보증금대용",
            "신용담보금대용",
            "추가담보금대용",
            "권리대용금",
            "출금가능금액",
            "랩출금가능금액",
            "주문가능금액",
            "수익증권매수가능금액",
            "20%종목주문가능금액",
            "30%종목주문가능금액",
            "40%종목주문가능금액",
            "100%종목주문가능금액",
            "현금미수금",
            "현금미수연체료",
            "신용이자미납",
            "신용이자미납연체료",
            "신용이자미납합계",
            "기타대여금",
            "기타대여금연체료",
            "기타대여금합계",
            "미상환융자금",
            "융자금합계",
            "대주금합계",
            "신용담보비율",
            "중도이용료",
            "최소주문가능금액",
            "대출총평가금액",
            "예탁담보대출잔고",
            "매도담보대출잔고",
            "d+1추정예수금",
            "d+1매도매수정산금",
            "d+1매수정산금",
            "d+1미수변제소요금",
            "d+1매도정산금",
            "d+1출금가능금액",
            "d+2추정예수금",
            "d+2매도매수정산금",
            "d+2미수변제소요금",
            "d+2매도정산금",
            "d+2출금가능금액",
            "출력건수",
        ]
    }

    OPW00004 = {
        "싱글데이터": [
            "계좌명",
            "지점명",
            "예수금",
            "D+2추정예수금",
            "유가잔고평가액",
            "예탁자산평가액",
            "총매입금액",
            "추정예탁자산",
            "매도담보대출금",
            "당일투자원금",
            "당월투자원금",
            "누적투자원금",
            "당일투자손익",
            "당월투자손익",
            "누적투자손익",
            "당일손익율",
            "당월손익율",
            "누적손익율",
            "출력건수",
        ],
        "멀티데이터": [
            "종목코드",
            "종목명",
            "보유수량",
            "평균단가",
            "현재가",
            "평가금액",
            "손익금액",
            "손익율",
            "대출일",
            "매입금액",
            "결제잔고",
            "전일매수수량",
            "전일매도수량",
            "금일매수수량",
            "금일매도수량",
        ],
    }

    OPW00007 = {
        "싱글데이터": ["출력건수"],
        "멀티데이터": [
            "주문번호",
            "종목번호",
            "매매구분",
            "신용구분",
            "주문수량",
            "주문단가",
            "확인수량",
            "접수구분",
            "반대여부",
            "주문시간",
            "원주문",
            "종목명",
            "주문구분",
            "대출일",
            "체결수량",
            "체결단가",
            "주문잔량",
            "통신구분",
            "정정취소",
            "확인시간",
        ],
    }


class FidList(object):
    """ receiveChejanData() 이벤트 메서드로 전달되는 FID 목록 """

    # DB에 저장할 column은 key를 영어로 작성
    CHEJAN = {
        "9201": "ACCOUNT_NO",  # 계좌번호
        "9203": "ORDER_NO",  # 주문번호
        "9205": "관리자사번",
        "9001": "TICKER",  # 종목코드
        "912": "주문업무분류",
        "913": "ORDER_STATUS",  # 주문상태: "접수", "체결"
        "302": "NAME",  # 종목명
        "900": "ORDER_QTY",  # 주문수량
        "901": "ORDER_PRICE",  # 주문가격
        "902": "UNEX_QTY",  # 미체결수량
        "903": "체결누계금액",
        "904": "ORIGINAL_ORDER_NO",
        "905": "ORDER_GUBUN",  # 주문구분: "+매수", "-매도", "매수취소" ..
        "906": "HOGA_TYPE",  # 매매구분: "보통", "시장가"..
        "907": "SELL_BUY_GUBUN",  # 매도수구분 : (1:매도, 2:매수, 주문상태; 접수인 경우)
        "908": "ORDER_TRAN_TIME",  # 주문/체결시간
        "909": "TRAN_NO",  # 체결번호
        "910": "체결가",
        "911": "체결량",
        "10": "현재가",
        "27": "(최우선)매도호가",
        "28": "(최우선)매수호가",
        "914": "TRAN_PRICE",  # 단위체결가
        "915": "TRAN_QTY",  # 단위체결량
        "938": "당일매매수수료",
        "939": "당일매매세금",
        "919": "거부사유",
        "920": "화면번호",
        "921": "터미널신호",
        "922": "신용구분",
        "923": "대출일",
        "949": "949",
        "10010": "10010",
        "917": "신용구분",
        "916": "대출일",
        "930": "보유수량",
        "931": "매입단가",
        "932": "총매입가",
        "933": "주문가능수량",
        "945": "당일순매수수량",
        "946": "BUY_SELL_GUBUN",  # 매도/매수구분 (주문상태: 체결인 경우)
        "950": "당일총매도손익",
        "951": "예수금",
        "307": "기준가",
        "8019": "손익율",
        "957": "신용금액",
        "958": "신용이자",
        "959": "담보대출수량",
        "924": "924",
        "918": "만기일",
        "990": "당일실현손익(유가)",
        "991": "당일신현손익률(유가)",
        "992": "당일실현손익(신용)",
        "993": "당일실현손익률(신용)",
        "397": "파생상품거래단위",
        "305": "상한가",
        "306": "하한가",
    }
