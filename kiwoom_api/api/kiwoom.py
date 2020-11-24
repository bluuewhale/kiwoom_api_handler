from collections import deque, defaultdict
from datetime import datetime as dt
import functools
import os
import time
import signal

import pandas as pd
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer

from ..utility.utility import dictListToListDict, removeSign, writeJson
from ._logger import Logger
from .errors import (KiwoomConnectError, KiwoomProcessingError,
                     ParameterTypeError, ParameterValueError)
from .return_codes import FidList, ReturnCode, TRKeys


class Kiwoom(QAxWidget):
    """ 싱글톤 패턴 적용 """

    __instance = None
    
    @classmethod
    def __getInstance(cls):
        return cls.__instance

    @classmethod
    def instance(cls, *args, **kwargs):
        cls.__instance = cls(*args, **kwargs)
        cls.instance = cls.__getInstance
        return cls.__instance

    def __init__(self):

        super().__init__()
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

        # old process kill
        # self.__killOldProcess()

        # Loop 변수: 비동기 방식으로 동작되는 이벤트를 동기화
        self.logingLoop = None
        self.requestLoop = None
        self.orderLoop = None
        self.conditionLoop = None

        # 서버구분
        self.serverStatus = None

        # 연속조회구분
        self.isNext = 0

        # logging 클래스
        self.homepath = os.environ.get('userprofile')
        self.logger = Logger(path=self.log_path, name="Kiwoom")

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

    @property
    def log_path(self):
        path = os.path.join(self.homepath, '.kiwoom_log')
        if not os.path.exists(path):
            os.mkdir(path)
        return path
    
    @property
    def order_log_path(self):
        path = os.path.join(self.homepath, '.kiwoom_order_log')
        if not os.path.exists(path):
            os.mkdir(path)
        return path
        
    ###############################################################
    ################### 이벤트 발생 시 메서드   #####################
    ###############################################################

    def eventConnect(self, returnCode):
        """ 통신 연결 상태 변경시 이벤트
        returnCode가 0이면 로그인 성공
        그 외에는 ReturnCode 클래스 참조.

        Parameters
        ----------
        returnCode: int 
            0이면 로그인 성공, 이외에는 로그인 실패
        """

        if returnCode == 0:
            msg = "{} Connection Successful".format(dt.now())
        else:
            errorName = getattr(ReturnCode, "CAUSE").get(returnCode)
            msg = "{} Connection Failed : {}".format(dt.now(), errorName)

        self.logger.debug(msg)

        try:
            self.loginLoop.exit()
        except AttributeError:
            pass

    def eventReceiveMsg(self, scrNo, rqName, trCode, msg):
        """ 수신 메시지 이벤트
        서버로 어떤 요청을 했을 때(로그인, 주문, 조회 등),
        그 요청에 대한 처리내용을 전달해준다.

        Parameters
        ----------
        scrNo: str
            화면번호(4자리, 사용자 정의,
            서버에 조회나 주문을 요청할 때 이 요청을 구별하기 위한 키값)
        rqName: str 
            TR 요청명(사용자 정의)
        trCode: str
        msg: str 
            서버로 부터의 메시지
        """
        if hasattr(self, "orderResponse"):
            self.orderResponse.update({"msg": msg})

        self.logger.debug(msg)

    def eventReceiveTrData(self, scrNo, rqName, trCode, recordName, inquiry, **kwargs):
        """
        TR 수신 이벤트시 실행되는 매서드

        조회요청 응답을 받거나 조회데이터를 수신했을 때 호출됩니다.
        rqName과 trCode는 getCommData() 메소드의 매개변수와 매핑되는 값 입니다.

        요청한 TR에 대해 수신된 데이터는 self.{trCode}에 저장됩니다.
        수신된 데이터는 모두 str 타입으로 사용자가 원하는 형태로 2차 가공이 필요합니다.

        trCode 및 rqName과 관련된 자세한 내용은 OPEN API+ 개발가이드 및
        KOA StudioSA를 참고하시기 바랍니다.

        Parameters
        ----------
        scrNo: str
            화면번호(4자리)
        rqName: str
            TR 요청명(commRqData() 메소드 호출시 사용된 rqName)
        trCode: str
        recordName: str
        inquiry: str 
            조회("0" or "": 남은 데이터 없음, '2': 남은 데이터 있음)
        """

        # 주문 이벤트인 경우
        if "ORD" in trCode:
            # 주문번호 획득, 주문번호가 존재하면 주문 성공
            orderNo = self.getCommData(trCode, "", 0, "주문번호")
            self.orderResponse.update({"orderNo": orderNo})
            try:
                self.orderLoop.exit()
            except AttributeError:
                pass
            return

        # TR 이벤트인 경우, orderResponse를 삭제
        if hasattr(self, "orderResponse"):
            delattr(self, "orderResponse")

        # TR Data 수신
        if trCode == "OPTKWFID":
            data = self.__getOPTKWFID(trCode, rqName)
        else:
            data = self.__getData(trCode, rqName)
        setattr(self, trCode, data)

        self.isNext = 0 if ((inquiry == "0") or (inquiry == "")) else 2  # 추가조회 여부

        # TR loop 탈출
        try:
            self.requestLoop.exit()
        except AttributeError:
            pass

        # TR 이벤트 logging
        eventDetail = {
            "TIME": dt.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "BASC_DT": dt.now().strftime("%Y-%m-%d"),
            "EVENT": "eventReceiveTrData",
            "REQUEST_NAME": rqName,
            "TR_CODE": trCode,
        }
        self.logger.debug(eventDetail)

    def eventReceiveChejanData(self, gubun, itemCnt, fidList):
        """ 주문 접수/확인 수신시 이벤트
        주문요청후 주문접수, 체결통보, 잔고통보를 수신할 때 마다 호출됩니다.

        Parameters
        ----------
        gubun: str
            체결구분('0': 주문접수/주문체결, '1': 잔고통보, '3': 특이신호)
        itemCnt: int
            fid의 갯수
        fidList: str
            fidList 구분은 ;(세미콜론) 이다.
        """
        if gubun != '0': # 주문접수/주문체결이 아니면 logging 안함
            return
        
        orderStatus = self.getChejanData('913').strip() # 주문상태 "접수" or "체결" or "확인"
        if orderStatus == '접수':
            table = 'orders_submitted'
            fidDict = getattr(FidList, 'SUBMITTED')
        elif orderStatus == '체결':
            table = 'orders_executed'
            fidDict = getattr(FidList, 'EXECUTED')
        elif orderStatus == '확인': #주문취소
            table = 'orders_cancelled'
            fidDict = getattr(FidList, 'CANCELLED')
        else:
            table = None # 지정된 table 명이 없으면 json파일 생성 안함
            fidDict = getattr(FidList, 'ALL')

        resultDict = {
            "BASC_DT": dt.now().strftime("%Y-%m-%d")
        }
        fids = fidList.split(";")
        for fid in fids:
            fidName = fidDict.get(fid)
            if fidName is None:
                continue
            data = self.getChejanData(fid).strip()
            resultDict[fidName] = data
        self.logger.debug(resultDict)

        
        # 체결내역은 json으로 임시저장하고, 
        # 비동기 watcher를 지정해서 DB에 쓰는 방식으로 최적화
        if table is not None:
            t = dt.now().strftime('%Y%m%d%H%M%S%f')
            file_path = os.path.join(self.order_log_path, f'{table}-{t}')
            try:
                writeJson(resultDict, file_path)
            except Exception as e:
                self.logger.error(f'ERROR: Order JSON logging {e}')
        
    ###############################################################
    #################### 로그인 관련 메서드   ######################
    ###############################################################

    def commConnect(self):
        """ 로그인 시도 """

        if not self.connectState:
            self.dynamicCall("CommConnect()")
            self.loginLoop = QEventLoop()
            self.loginLoop.exec_()  # eventConnect에서 loop를 종료

    @property
    def connectState(self):
        """ 현재 접속상태를 반환합니다.

        Returns
        ----------
        int
            0(미연결), 1(연결)
        """

        return self.dynamicCall("GetConnectState()")

    @property
    def accNos(self):
        accounts = self.getLoginInfo("ACCNO").rstrip(";")
        return accounts.split(";")

    def getLoginInfo(self, tag):
        """ 사용자의 tag에 해당하는 정보를 반환한다.
        tag에 올 수 있는 값은 아래와 같다.
        ACCOUNT_CNT, ACCNO, USER_ID, USER_NAME, GetServerGubun

        Parameters
        ----------
        tag: str
        isConnectState: bool
            접속상태을 확인할 필요가 없는 경우 True로 설정.

        Returns
        -----------
        info : str
            입력한 tag에 대응하는 정보
        """

        if not self.connectState:  # 1: 연결, 0: 미연결
            raise KiwoomConnectError()

        tags = ["ACCOUNT_CNT", "ACCNO", "USER_ID", "USER_NAME", "GetServerGubun"]
        if tag not in tags:
            raise ParameterValueError()

        if tag == "GetServerGubun":
            info = self.getServerGubun()
        else:
            info = self.dynamicCall('GetLoginInfo("{}")'.format(tag))
        return info

    def getServerGubun(self):
        """ 서버구분 정보를 반환한다.

        Returns
        ----------
        server_status: str
            "1": 모의투자서버 else: 실서버
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
        """ TR 전송에 필요한 값을 설정한다.

        Parameters
        ----------
        key: str
            TR에 명시된 input 이름, ex) 계좌번호, 종목코드
        value: str
            key에 해당하는 값, ex) 88231524, 005930
        """

        if not isinstance(key, str):
            key = str(key)

        if not isinstance(value, str):
            value = str(value)

        if (key == "계좌번호") and (value not in self.accNos):
            raise KiwoomProcessingError("ERROR: Invalid 계좌번호")

        if (key == "종목코드") and (value not in self.codes):
            raise KiwoomProcessingError("ERROR: Invalid 종목코드")

        self.dynamicCall("SetInputValue(QString, QString)", key, value)

    def commRqData(self, rqName, trCode, inquiry, scrNo):
        """ 키움서버에 TR 요청을 한다.
        요청한 데이터는 데이터 수신 이벤트 발생 시 eventReceiveTrData 매서드에서 처리

        1초에 5회 제한

        Parameters
        ----------
        rqName: str
            TR 요청명(사용자 정의)
        trCode: str
        inquiry: int
            조회(0: 조회, 2: 남은 데이터 이어서 요청)
        scrNo: str
            화면번호(4자리)

        Returns
        ----------
        returnCode: str
            0(정상), -200(시세과부하), -201(조회전문작성 에러)
        """

        if not self.connectState:
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

        if returnCode != 0:  # 0이외엔 실패
            self.logger.error(
                "{} commRqData {} Request Failed!, CAUSE: {}".format(
                    dt.now(), rqName, getattr(ReturnCode, "CAUSE").get(returnCode)
                )
            )
            raise KiwoomProcessingError()

        # 루프 생성: eventReceiveTrData() 메서드에서 루프를 종료시킨다.
        self.logger.debug("{}  commRqData {}".format(dt.now(), rqName))
        self.requestLoop = QEventLoop()
        self.requestLoop.exec_()

    def getRepeatCnt(self, trCode, rqName):
        """ 서버로 부터 전달받은 데이터의 갯수를 리턴합니다.(멀티데이터의 갯수)
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

        Parameters
        ----------
        trCode: str
        rqName: str

        Returns
        ----------
        cnt : int
            서버에서 전달받은 데이터 갯수
        """

        if not (isinstance(trCode, str) and isinstance(rqName, str)):
            raise ParameterTypeError()

        cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trCode, rqName)
        return cnt

    def getCommData(self, trCode, rqName, index, key):
        """ 데이터 획득 메서드
        evnetReceiveTrData() 이벤트 메서드가 호출될 때, 그 안에서
        조회데이터를 얻어오는 메서드입니다. 이 함수는 반드시 OnReceiveTRData()
        이벤트가 호출될때 그 안에서 사용해야 합니다.

        싱글데이터는 index=0
        멀티데이터는 getRepeatCnt 매서드로 데이터 수를 확인한 후,
        loop문으로 index를 1씩 늘리며 접근

        Parameters
        -----------
        trCode: str
        rqName: str
            TR 요청명(commRqData() 메소드 호출시 사용된 rqName)
        index: int
        key: str
            수신 데이터에서 얻고자 하는 값의 키(출력항목이름)

        Returns
        ----------
        data: str
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
        """ 멀티 데이터 획득
        조회 수신데이터 크기가 큰 차트데이터를 한번에 가져올 목적으로 만든 전용함수입니다.
        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.

        Parameters
        ----------
        trCode: str
        multiDataName: str
            KOA에 명시된 멀티데이터명

        Returns
        ----------
        data: list
            중첩리스트
        """

        if not (isinstance(trCode, str) and isinstance(multiDataName, str)):
            raise ParameterTypeError()

        data = self.dynamicCall(
            "GetCommDataEx(QString, QString)", trCode, multiDataName
        )
        return data

    def commKwRqData(self, arrCode, next, codeCount, rqName, scrNo, typeFlag=0):
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

        if not self.connectState:
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
            raise KiwoomProcessingError()

        # logging
        self.logger.debug("{}  commKwRqData {}".format(dt.now(), rqName))

        # eventReceiveTrData()에서 loop 종료 or timeout
        self.requestLoop = QEventLoop()
        QTimer.singleShot(1000, self.requestLoop.exit)  # timout in 1000 ms
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

        """ 주식 주문 메서드

        sendOrder() 메소드 실행시,
        OnReceiveMsg, OnReceiveTrData, OnReceiveChejanData 이벤트가 발생한다.
        이 중, 주문에 대한 결과 데이터를 얻기 위해서는 OnReceiveChejanData 이벤트를 통해서 처리한다.

        OnReceiveTrData 이벤트를 통해서는 주문번호를 얻을 수 있는데,
        주문후 OnReceiveTrData에서 주문번호가 ''공백으로 전달되면 주문접수 실패를 의미한다.

        ※  시장가, 최유리지정가, 최우선지정가, 시장가IOC, 최유리IOC,시장가FOK,
            최유리FOK, 장전시간외, 장후시간외 주문시 
            주문가격(price)을 0으로 입력.
        
        Paramters
        ----------
        rqName: str
            주문 요청명(사용자 정의)
        scrNo: str
            화면번호(4자리)
        accNo: str
            계좌번호(10자리)
        orderType: int
            주문유형(1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도정정)
        code: str
            종목코드
        qty: int
            주문수량
        price: int
            주문단가
        hogaType: str
            거래구분(00: 지정가, 03: 시장가, 05: 조건부지정가, 06: 최유리지정가, 그외에는 api 문서참조)
        originOrderNo: str
            원주문번호(신규주문에는 공백, 정정및 취소주문시 원주문번호를 입력합니다.)

        """
        orderParams = {
            "rqName": rqName,
            "scrNo": scrNo,
            "accNo": accNo,
            "orderType": orderType,
            "code": code,
            "qty": qty,
            "price": price,
            "hogaType": hogaType,
            "originOrderNo": originOrderNo,
        }

        # order response data
        self.orderResponse = {
            "time": dt.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "orderNo": "",
        }
        self.orderResponse.update(orderParams)

        # server connection check
        if not self.connectState:
            msg = "Server not connected"
            self.orderResponse.update({"msg": msg})
            raise KiwoomConnectError(msg)

        # Error: code not supported
        if not code in self.codes:

            msg = f"Code not supported: {code}"
            self.orderResponse.update({"msg": msg})
            raise KiwoomProcessingError("ERROR: sendOrder() : {}".format(msg))

        # API 제한 확인
        self.orderDelayCheck.checkDelay()

        # 주문 전송
        try:
            returnCode = self.dynamicCall(
                "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                list(orderParams.values()),
            )

        except Exception as msg:
            self.orderResponse.update({"msg": msg})
            raise KiwoomProcessingError("ERROR: sendOrder() : {}".format(msg))

        if returnCode != 0:
            msg = getattr(ReturnCode, "CAUSE").get(returnCode)
            self.orderResponse.update({"msg": msg})
            raise KiwoomProcessingError("ERROR: sendOrder() : {}".format(msg))

        # eventReceiveTrData() 에서 루프종료 or timeout
        self.orderLoop = QEventLoop()
        #QTimer.singleShot(1000, self.orderLoop.exit)  # timout in 1000 ms
        self.orderLoop.exec_()

    def getChejanData(self, fid):
        """ 주문접수, 주문체결, 잔고정보를 얻어오는 메서드
        이 메서드는 receiveChejanData() 이벤트 메서드가 호출될 때
        그 안에서 사용해야 합니다.

        Parameters
        ===========================
        fid: str

        return
        ===========================
        data: str
        """

        if not isinstance(fid, str):
            raise ParameterTypeError()

        data = self.dynamicCall(f'GetChejanData("{fid}")')
        return data

    def __getData(self, trCode, rqName):

        returnDict = {}
        if getattr(TRKeys, trCode).get("멀티데이터", False):
            returnDict["멀티데이터"] = self.__getMultiData(trCode, rqName)
        if getattr(TRKeys, trCode).get("싱글데이터", False):
            returnDict["싱글데이터"] = self.__getSingleData(trCode, rqName)
        return returnDict

    def __getSingleData(self, trCode, rqName):

        data = {}

        keyList = getattr(TRKeys, trCode).get("싱글데이터")
        for key in keyList:
            val = self.getCommData(trCode, rqName, 0, key)
            if key.endswith("호가") or key in getattr(TRKeys, "NOSIGNKEY"):
                val = removeSign(val)
            data[key] = val
        return data

    def __getMultiData(self, trCode, rqName):

        data = []
        cnt = self.getRepeatCnt(trCode, rqName)
        keyList = getattr(TRKeys, trCode).get("멀티데이터")

        for i in range(cnt):
            tmpDict = {}
            for key in keyList:
                val = self.getCommData(trCode, rqName, i, key)
                if key.endswith("호가") or key in getattr(TRKeys, "NOSIGNKEY"):
                    val = removeSign(val)
                tmpDict[key] = val
            data.append(tmpDict)
        return data

    def __getOPTKWFID(self, trCode, rqName):

        data = {}

        tmpData = self.getCommDataEx(trCode, rqName)
        keyList = getattr(TRKeys, trCode).get("멀티데이터")

        for key, ls in zip(keyList, zip(*tmpData)):
            if key.endswith("호가") or key in getattr(TRKeys, "NOSIGNKEY"):
                ls = map(removeSign, ls)
            data[key] = list(ls)
        data = dictListToListDict(data)  # dict of list to list of dict
        data = {"멀티데이터": data}
        return data

    def __getCodeListByMarket(self, market):
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

        if not self.connectState:
            raise KiwoomConnectError()

        if not isinstance(market, str):
            raise ParameterTypeError()

        if market not in ["0", "3", "4", "5", "6", "8", "9", "10", "30"]:
            raise ParameterValueError()

        codes = self.dynamicCall('GetCodeListByMarket("{}")'.format(market))
        return codes.split(";")

    @property
    def codes(self):
        if not self.connectState:
            raise KiwoomConnectError()

        codes = self.__getCodeListByMarket("0")  # KOSPI
        codes += self.__getCodeListByMarket("10")  # KOSDAQ
        codes += self.__getCodeListByMarket("8")  # ETF
        return codes

    """
    def __killOldProcess(self):

        path = os.path.abspath("__file__")
        filePath = os.path.join(path, "pid.txt")

        try:
            last_pid = int(readTxt(filePath))

        except FileNotFoundError:
            return

        cur_pid = os.getpid()

        if cur_pid != last_pid:
            os.kill(last_pid, signal.SIGTERM)
            saveTxt(filePath, cur_pid)
        """


class APIDelayCheck:
    def __init__(self, logger=None):
        """
        Kiwoom API 요청 제한을 피하기 위해 요청을 지연하는 클래스입니다.

        Parameters
        ----------
        logger: 
            Kiwoom Class의 logger, defalut=None
        """
        # 1초에 5회, 1시간에 1,000회 제한
        self.rqHistory = deque(maxlen=1000)

        if logger:
            self.logger = logger

    def checkDelay(self):
        """ TR 1초 5회 제한을 피하기 위해, 조회 요청을 지연합니다. """
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
