from collections import defaultdict
from datetime import datetime

import pandas as pd


class Feeder:

    def __init__(self, broker):

        self.broker = broker
        self.accountNum = self.getAccountNum()

        # 각 시장에 상장된 종목 코드
        self.kospiCodeList = self.broker.getCodeListByMarket('0')
        self.kosdaqCodeList = self.broker.getCodeListByMarket('10')
        self.etfCodeList = self.broker.getCodeListByMarket('8')

    ### logging 관련 매서드
    def showTradingSummary(self, date):

        # logging할 데이터
        traSummaryDict = self.getOpt10074(self.accountNum, date)

        date = '-'.join((date[:4], date[4:6], date[6:])) # YYYY-MM-DD 꼴로 수정

        totalBuy = int(traSummaryDict['총매수금액'])
        totalSell = int(traSummaryDict['총매도금액'])
        netProfit = int(traSummaryDict['실현손익'])
        accoundDict = self.getOpw00004(self.accountNum)
        balanceEnd = int(accoundDict['account']['추정예탁자산'].replace(',', '')) # 마감 잔고
        balanceStart = balanceEnd - netProfit
        stratRt = balanceEnd/balanceStart -1

        summaryDict = {
            'TABLE' : 'trading_summary',
            'BASC_DT' : date,
            'STRAT_BUY' : totalBuy,
            'STRAT_SELL' : totalSell,
            'STRAT_NET_PROFIT' : netProfit,
            'BALANCE_START' : balanceStart,
            'BALANCE_END' : balanceEnd,
            'STRAT_RET_PCT' : stratRt
        }

        self.broker.logger.debug('='*70)
        self.broker.logger.debug('{')

        for key, val in loggingDict.items():

            self.broker.logger.debug('"{}" : "{}" ,'.format(key, val))

        self.broker.logger.debug('}')
        self.broker.logger.debug('='*70)

        return summaryDict

    ###############################################################
    ############## TR,주문 및 잔고 관련 헬퍼 메서드   ###############
    ###############################################################

    def __OPTKWFID(self, codes):
        codesCnt = len(codes.split(';'))
        self.broker.commKwRqData(codes, 0, codesCnt, '관심종목정보요청', '1111', typeFlag=0)

    def getOPTKWFID(self, codeList):
        '''  관심종목정보요청

        한번에 100 종목 이상까지 조회가능하도록 수정한 헬퍼 매서드입니다.
        요청한 데이터는 self.broker.OPTKWFIDData에 저장됩니다.

        params
        =====================================
        codeList: list, 종목코드가 담긴 list

        return
        ======================================
        data: pandas.DataFrame - row(개별 종목), columns(기준가, 시가 등 63개의 열)
        '''

        data = pd.DataFrame()

        for start, end in zip(range(0, len(codeList), 100),
                              range(100, len(codeList)+100, 100)):
            # input params
            tmpCodeList = codeList[start:end]
            tmpCodes = ';'.join(tmpCodeList)

            # TR 전송
            self.__OPTKWFID(tmpCodes)

            data = pd.concat((data, self.broker.OPTKWFIDData), axis=0, copy=False)

        data.reset_index(drop=True, inplace=True)
        return data

    def __opt10004(self, code):
        self.broker.setInputValue('종목코드', code)
        self.broker.commRqData('주식호가요청', 'opt10004', 0, '2000')

    def getOpt10004(self, code):
        ''' 주식호가요청

        params
        ===========================
        code: str, 종목코드

        return
        ============================
        data: dict
        '''

        self.__opt10004(code)

        data = self.broker.opt10004Data
        return data

    def __opt10005(self, code):
        self.broker.setInputValue('종목코드', code)
        self.broker.commRqData('주식일주월시분요청', 'opt10005', 0, '2000')

    def getOpt10005(self, code, idx=None):
        ''' 주식일주월시분요청

        params
        =========================
        code: str, 종목코드
        idx: int or list optional, default=None
            반환받을 행을 선택, none일 경우, 전체를 반환
        '''

        self.__opt10005(code)
        data = self.broker.opt10005Data

        if idx is not None:
            data = data.loc[idx]

        return data

    def __opt10059(self, date, code, gumaekGubun=1, maemaeGubun=0, danwiGubun=1):
        self.broker.setInputValue('일자', date)
        self.broker.setInputValue('종목코드', code)
        self.broker.setInputValue('금액수량구분', gumaekGubun)
        self.broker.setInputValue('매매구분', maemaeGubun)
        self.broker.setInputValue('단위구분', danwiGubun)

        self.broker.commRqData('종목별투자자기관별요청', 'opt10059', 0, '2000')

    def getOpt10059(self, date, code, idx=None, gumaekGubun='1', maemaeGubun='0', danwiGubun='1'):
        ''' 종목별투자자기관별요청

        params
        ======================================================

        date: str, YYMMDD
        code: str, ex) 005930
        idx: int, 조회할 이전 영업일 수, defalut=None 전체조회;
        gumaekGubun: str, 금액수량구분, 1:금액 ; 2:수량
        maemaeGubun: str, 매매구분, 0:순매수, 1: 매수, 2:매도
        danwiGubun: str, 단위구분, 1:주, 1000:천주
        '''
        self.__opt10059(date, code, gumaekGubun, maemaeGubun, danwiGubun)
        opt10059Data = self.broker.opt10059Data

        if idx is not None:
            opt10059Data = opt10059Data.loc[idx]

        return opt10059Data

    def __opw00001(self, accountNum, password, inquiry):
        self.broker.setInputValue('계좌번호', accountNum)

        if password:
            self.broker.setInputValue('비밀번호',  password)
            self.broker.setInputValue('조회구분', inquiry)

        self.broker.commRqData('예수금상세현황요청', 'opw00001', 0, '2001')

    def getOpw00001(self, accountNum, password='', inquiry='2'):
        '''예수금상세현황요청(주문가능금액)
        주문가능금액을 반환합니다.

        params
        ===========================================================
        accountNum: str
        password: str
        inquiry: str - 조회구분 = 1:추정조회, 2:일반조회

        return
        ===========================================================
        opw00001Data: int, 주문가능금액
        '''

        self.__opw00001(accountNum, password, inquiry)
        opw00001Data = self.broker.opw00001Data

        return opw00001Data

    def __opw00004(self, accountNum, password, inquiry):
        # data reset
        self.broker.opw00004Data = {'account': {}, 'stocks': []}

        # 데이터 요청
        self.broker.setInputValue('계좌번호', accountNum)

        if password:
            self.broker.setInputValue('비밀번호', password)
            self.broker.setInputValue('조회구분', inquiry)

        self.broker.commRqData('계좌평가현황요청', 'opw00004', 0, '2004')

        # 20개씩 반복 요청
        while self.broker.inquiry == 2:
            self.broker.setInputValue('계좌번호', accountNum)
            self.broker.setInputValue('비밀번호', password)
            self.broker.setInputValue('조회구분', inquiry)

            self.broker.commRqData('계좌평가현황요청', 'opw00004', 2, '2004')

    def getOpw00004(self, accountNum, password='', inquiry='2'):
        ''' 계좌평가잔고내역요청
        계좌정보 및 보유종목 정보를 반환합니다.

        params
        =========================================================
        accountNum: str
        password: str
        inquiry: str

        return
        =========================================================
        opw00018Data : Dict, {
            'account' : Dict
            'stocks' : Dict
        }
        '''

        self.__opw00004(accountNum, password, inquiry)
        opw00004Data = self.broker.opw00004Data

        # 종목코드에서 A제거
        inventoryList = opw00004Data['stocks']
        for dict in inventoryList:
            dict['종목코드'] = dict['종목코드'].replace('A', '')

        return opw00004Data

    def __opw00007(self, date, accountNum, inquiry):
        # data reset
        self.broker.opw00007Data = []

        self.broker.setInputValue('주문일자', date) # YYYYMMDD
        self.broker.setInputValue('계좌번호', accountNum)
        self.broker.setInputValue('조회구분', inquiry)

        self.broker.commRqData('계좌별주문체결내역상세요청', 'opw00007', 0, '2007')

        # 30개씩 반복 요청
        while self.broker.inquiry == 2:
            self.broker.setInputValue('주문일자', date) # YYYYMMDD
            self.broker.setInputValue('계좌번호', accountNum)
            self.broker.setInputValue('조회구분', inquiry)

            self.broker.commRqData('계좌별주문체결내역상세요청', 'opw00007', 2, '2007')

    def getOpw00007(self, date, accountNum, inquiry='1'):
        '''
        계좌별주문체결내역상세요청

        주문 정보
        params
        ===================================
        date: str - YYYYMMDD
        accountNum: str
        inquiry: str - 1:주문순, 2:역순, 3:미체결, 4:체결내역만
        '''

        self.__opw00007(date, accountNum, inquiry)
        return self.broker.opw00007Data

    def __opt10075(self, accountNum, inquiry, inquiry2):
        # data reset
        self.broker.opt10075Data = []

        self.broker.setInputValue('계좌번호', accountNum)
        self.broker.setInputValue('체결구분', inquiry)
        self.broker.setInputValue('매매구분', inquiry2)

        self.broker.commRqData('실시간미체결요청', 'opt10075', 0, '1075')

        # 30개씩 반복 요청
        while self.broker.inquiry == 2:
            self.broker.setInputValue('계좌번호', accountNum)
            self.broker.setInputValue('체결구분', inquiry)
            self.broker.setInputValue('매매구분', inquiry2)

            self.broker.commRqData('실시간미체결요청', 'opt10075', 2, '1075')

    def getOpt10075(self, accountNum, inquiry='1', inquiry2='0'):
        '''
        실시간미체결요청

        params
        =======================================================
        accountNum: str
        inquiry: str - 0:체결+미체결, 1:미체결, 2:체결
        inquiry2: str - 0:전체, 1:매도, 2:매수
        '''
        self.__opt10075(accountNum, inquiry, inquiry2)
        return self.broker.opt10075Data

    def __opt10074(self, accountNum, date):
        # data reset
        self.broker.opt10074Data = []

        self.broker.setInputValue('계좌번호', accountNum)
        self.broker.setInputValue('시작일자', date)
        self.broker.setInputValue('종료일자', date)

        self.broker.commRqData('일자별실현손익요청', 'opt10074', 0, '1074')

        # 30개씩 반복 요청
        while self.broker.inquiry == 2:
            self.broker.setInputValue('계좌번호', accountNum)
            self.broker.setInputValue('시작일자', date)
            self.broker.setInputValue('종료일자', date)

            self.broker.commRqData('일자별실현손익요청', 'opt10074', 2, '1074')

    def getOpt10074(self, accountNum, date):
        ''' 일자별실현손익요청

        params
        =======================================================
        accountNum: str
        date: str, YYYYMMDD
        '''

        self.__opt10074(accountNum, date)
        return self.broker.opt10074Data

    ##########################################
    ########## 계좌 조회 관련 메서드 ##########
    ##########################################

    def getAccountNum(self):
        return self.broker.getLoginInfo('ACCNO').rstrip(';')

    def getDeposit(self, accountNum):
        #  계좌 정보
        opw00004Data = self.getOpw00004(accountNum)

        deposit = int(opw00004Data['account']['D+2추정예수금'].replace(',', ''))
        return deposit

    def getUnexOrderDictList(self, accountNum):
        inquiry = '1' # 미체결
        inquiry2 = '0' # 매수+매도

        unexOrderDictList = self.getOpt10075(accountNum, inquiry, inquiry2)
        return unexOrderDictList

    def getAccountDict(self, accountNum):
        opw00004Data = self.getOpw00004(accountNum)

        accountDict = opw00004Data['account']
        return accountDict

    def getInventoryDictList(self, accountNum):
        # 개별 종목 정보
        opw00004Data = self.getOpw00004(accountNum)

        inventoryDictList = opw00004Data['stocks']
        return inventoryDictList

    def getInventoryCodeList(self, accountNum):
        inventoryDictList = self.getInventoryDictList(accountNum)

        codeList = [dict['종목코드'] for dict in inventoryDictList]
        return codeList

    ##########################################
    ############# utility 메서드 #############
    ##########################################

    def getMarketByCode(self, code):
        '''
        해당 종목이 상장된 시장정보 반환
        '''

        if code in self.kospiCodeList:
            return 'KOSPI'

        elif code in self.kosdaqCodeList:
            return 'KOSDAQ'

        elif code in self.etfCodeList:
            return 'ETF'

        return None

    def dropIssueStock(self, codeList):
        '''
        관리종목, 거래정지 종목을 제거합니다.

        return
        =======================
        cleanList
        '''

        cleanList = []

        for code in codeList:
            stateList = self.broker.getMasterStockState(code)

            if '관리종목' in stateList or '거래정지' in stateList:
                continue

            cleanList.append(code)

        return cleanList

    def getCodesFromKRX(self, market='all'):
        ''' 상장기업 목록 (한국거래소) '''

        kospiURL = 'https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType=stockMkt&searchType=13'
        kosdaqURL = 'https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType=kosdaqMkt&searchType=13'

        if market == 'all':
            kospiCodeList = list(pd.read_html(kospiURL, header=0)[0]['종목코드'].map('{:06d}'.format))
            kosdaqCodeList = list(pd.read_html(kosdaqURL, header=0)[0]['종목코드'].map('{:06d}'.format))

            codeList = kospiCodeList + kosdaqCodeList

        if market == 'KOSPI':
            codeList = list(pd.read_html(kospiURL, header=0)[0]['종목코드'].map('{:06d}'.format))

        if market == 'KOSDAQ':
            codeList = list(pd.read_html(kosdaqURL, header=0)[0]['종목코드'].map('{:06d}'.format))

        codeList = [c for c in codeList if not '스팩' in c] # 스팩 제거
        return codeList
