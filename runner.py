import asyncio
from datetime import datetime, timedelta
import functools
import os
import signal
import sys

import numpy as np
from PyQt5.QtWidgets import QApplication

from Kiwoom import *
from utility import *



class AutoRunDecorator:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        app = QApplication(sys.argv) # 앱 실행

        self.func(*args, **kwargs) # 함수 실행

        # 종료
        sys.exit(app.exec_())

    @staticmethod
    def asyncFullTime(delay):
        ''' 24시간(Full-Time) 비동기로 실행되는 coroutine decorator ex(서버 상태 확인) '''

        def wrapper(func):
            @functools.wraps(func)
            async def inner(*args, **kwargs):
                while True:
                    try:
                        await asyncio.sleep(delay)
                        await func(*args, **kwargs)

                    except Exception as e:
                        print(e)

            return inner
        return wrapper


    @staticmethod
    def asyncSpotTime(startTime, deadline=20, delay=1):
        ''' 특정 1회만 실행되는 coroutin decorator, ex: 매수집행

        params
        =======================================
        startTime: str ,(HH:MM:SS, 24시간 단위로) ==> 실행 시간
        deadline: int,  deadline(초) 이내로 실행 못하면 실행 하지 않음
        delay: int, 시간 확인 주기(초)
        '''

        startTime = int(startTime.replace(':', '')) # 09:00:10 => 90010
        endTime = startTime + deadline

        def wrapper(func):
            @functools.wraps(func)
            async def inner(*args, **kwargs):

                while True:
                    curTime = int(datetime.now().strftime('%H%M%S')) # 090010 => 90010

                    # 지정한 시간이 되면 실행
                    if (startTime <= curTime) & (curTime <= endTime):
                        try:
                            await func(*args, **kwargs)
                            break

                        except Exception as e:
                            print(e)

                    await asyncio.sleep(delay)
            return inner
        return wrapper


class OvernightReversalRunner:
    def __init__(self, feeder, orderCreator, executor, accountNum, *args, **kwargs):
        self.feeder = feeder
        self.orderCreator = orderCreator
        self.executor = executor
        self.broker = self.feeder.broker
        self.logger = self.broker.logger
        self.accountNum = accountNum

        # 폴더 생성
        if not 'data' in os.listdir('./'):
            os.mkdir('data')

        dateT = datetime.now().strftime('%Y%m%d')

        if not dateT in os.listdir('./data/'):
            os.mkdir('data/{}'.format(dateT))

    # 메인 함수
    def run(self):


        self.killOldProcess() # 기존 Process Kill

        coroutineList = [
            self.asyncServerCheck(),  # 서버 상태 체크
            self.asyncReconnectToServer(), # 서버에 재연결

            # 손절/익절
            #self.__asyncSendStopLossOrder(),
            #self.__asyncSendProfitTakingOrder(),

            # 개징 직후 시장가 + 공격적 지정가 매수
            self.__asyncSendBuyOrderAtOpen(),

            # 계단식 지정가 매수
            self.__asyncSendStairLimitBuyOrder(),

            # 매수 주문 취소
            self.__asyncSendBuyCancelOrder(),

            # 계단식 지정가 매도
            self.__asyncSendStairLimitSellOrder01(),
            self.__asyncSendStairLimitSellOrder02(),

            # 지정가 매도
            self.__asyncSendLimitSellOrder01(),
            self.__asyncSendLimitSellOrder02(),
            self.__asyncSendLimitSellOrder03(),

            # 시장가 매도
            self.__asyncSendMarketSellOrder01(),
            self.__asyncSendMarketSellOrder02(),
            self.__asyncSendMarketSellOrder03(),
            self.__asyncSendMarketSellOrder04(),


            # 일일 매매 결산
            self.asyncShowTradingSummary(),

            # 15:45:00 Process 종료
            self.asyncKillProcess(),
        ]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*coroutineList))

    #####################
    ##### coroutines ####
    #####################

    @AutoRunDecorator.asyncFullTime(delay=30)
    async def asyncServerCheck(self):
        self.checkServerStatus()

    @AutoRunDecorator.asyncFullTime(delay=600)
    async def asyncReconnectToServer(self):
        self.connect()


    # 손절/익절 주문 제출
    @AutoRunDecorator.asyncFullTime(delay=600)
    async def __asyncSendStopLossOrder(self):

        threshold = -0.05
        sellWeight = 0.3
        self.__sendStopLossOrder(threshold=threshold, sellWeight=sellWeight)

    @AutoRunDecorator.asyncFullTime(delay=600)
    async def __asyncSendProfitTakingOrder(self):

        threshold = -0.05
        sellWeight = 0.3
        self.__sendProfitTakingOrder(threshold=threshold, sellWeight=sellWeight)


    # 개장 직후 매수 주문
    @AutoRunDecorator.asyncSpotTime(startTime='09:00:35')
    async def __asyncSendBuyOrderAtOpen(self):

        paramDict = {
            'accountNum' : self.accountNum,
            'buyCodeList' : self.orderCreator.getBuyCodeList(),
            'minBuyVolume' : 2000000, # 200만원
            'maxBuyVolume' : 5000000, # 500만원
            'totalMaxBuyVolume' : 70000000, # 7,000만원
        }

        # 주문 정보 생성 (시장가 + 공격적 지정가 매수)
        buyOrderDictListAtOpen = self.orderCreator.getBuyOrderDictListAtOpen(**paramDict)

        # 주문 집행
        self.executor._sendOrder(buyOrderDictListAtOpen)

    # 계단식 지정가 매수주문
    @AutoRunDecorator.asyncSpotTime(startTime='09:01:05')
    async def __asyncSendStairLimitBuyOrder(self):

        buyCodeList = self.orderCreator.getBuyCodeList()

        deposit = self.feeder.getDeposit(self.accountNum)
        n = np.min((len(buyCodeList), 10)) # 최대 비중 1/10
        avgBuyVolume = deposit/n

        self.__sendStairLimitBuyOrder(buyCodeList=buyCodeList, avgBuyVolume=avgBuyVolume)


    # 계단식 지정가 매수주문 취소
    @AutoRunDecorator.asyncSpotTime(startTime='11:00:00')
    async def __asyncSendBuyCancelOrder(self):

        cancelCodeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=cancelCodeList)


    # 계단식 지정가 매도주문 제출
    @AutoRunDecorator.asyncSpotTime(startTime='14:32:30')
    async def __asyncSendStairLimitSellOrder01(self):

        cancelCodeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=cancelCodeList)

        sellCodeList = self.orderCreator.getBuyCodeList()
        self.__sendStairLimitSellOrder(
            sellCodeList=sellCodeList,
            sellWeight=1.0
        )

    @AutoRunDecorator.asyncSpotTime(startTime='14:43:00')
    async def __asyncSendStairLimitSellOrder02(self):

        cancelCodeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=cancelCodeList)

        sellCodeList = self.orderCreator.getBuyCodeList()
        self.__sendStairLimitSellOrder(
            sellCodeList=sellCodeList,
            sellWeight=1.0
        )


    # 지정가 매도주문 제출
    @AutoRunDecorator.asyncSpotTime(startTime='15:01:52')
    async def __asyncSendLimitSellOrder01(self):

        # 주문 취소
        cancelCodeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=cancelCodeList)

        # 지정가 매도
        paramDict1 = {
        'sellCodeList' : self.orderCreator.getBuyCodeList(),
        'tickShift' : 0, # 매도호가
        'sellWeight' : 0.5,
        }

        paramDict2 = {
            'sellCodeList' : self.orderCreator.getBuyCodeList(),
            'tickShift' : -1, # 매도호가 바로
            'sellWeight' : 0.25,
        }

        self.__sendLimitSellOrder(**paramDict1)
        self.__sendLimitSellOrder(**paramDict2)


    @AutoRunDecorator.asyncSpotTime(startTime='15:05:52')
    async def __asyncSendLimitSellOrder02(self):

        # 지정가 매도
        paramDict1 = {
        'sellCodeList' : self.orderCreator.getBuyCodeList(),
        'tickShift' : 0, # 매도호가
        'sellWeight' : 0.6,
        }

        paramDict2 = {
            'sellCodeList' : self.orderCreator.getBuyCodeList(),
            'tickShift' : -1, # 매도호가 바로
            'sellWeight' : 0.3,
        }


        self.__sendLimitSellOrder(**paramDict1)
        self.__sendLimitSellOrder(**paramDict2)


    @AutoRunDecorator.asyncSpotTime(startTime='15:10:03')
    async def __asyncSendLimitSellOrder03(self):

        # 주문 취소
        cancelCodeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=cancelCodeList)


        # 지정가 매도
        paramDict1 = {
        'sellCodeList' : self.orderCreator.getBuyCodeList(),
        'tickShift' : 0, # 매도호가
        'sellWeight' : 0.7,
        }

        paramDict2 = {
            'sellCodeList' : self.orderCreator.getBuyCodeList(),
            'tickShift' : -1, # 매도호가 바로
            'sellWeight' : 0.30,
        }

        self.__sendLimitSellOrder(**paramDict1)
        self.__sendLimitSellOrder(**paramDict2)


    # 시장가 매도주문 제출
    @AutoRunDecorator.asyncSpotTime(startTime='15:13:32')
    async def __asyncSendMarketSellOrder01(self):

        codeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=codeList)

        self.__sendMarketSellOrder(sellCodeList=codeList, sellWeight=0.3)

        # 지정가 매도
        paramDict = {
        'sellCodeList' : self.orderCreator.getBuyCodeList(),
        'tickShift' : 0, # 매도호가
        'sellWeight' : 1,
        }

        self.__sendLimitSellOrder(**paramDict)

    @AutoRunDecorator.asyncSpotTime(startTime='15:16:12')
    async def __asyncSendMarketSellOrder02(self):

        codeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=codeList)

        self.__sendMarketSellOrder(sellCodeList=codeList, sellWeight=0.4)

        # 지정가 매도
        paramDict = {
        'sellCodeList' : self.orderCreator.getBuyCodeList(),
        'tickShift' : 0, # 매도호가
        'sellWeight' : 1,
        }

        self.__sendLimitSellOrder(**paramDict)

    @AutoRunDecorator.asyncSpotTime(startTime='15:18:25')
    async def __asyncSendMarketSellOrder03(self):

        codeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=codeList)

        self.__sendMarketSellOrder(sellCodeList=codeList, sellWeight=0.5)

        # 지정가 매도
        paramDict = {
        'sellCodeList' : self.orderCreator.getBuyCodeList(),
        'tickShift' : 0, # 매도호가
        'sellWeight' : 1,
        }

        self.__sendLimitSellOrder(**paramDict)

    @AutoRunDecorator.asyncSpotTime(startTime='15:21:05') # 15:21:05 실행
    async def __asyncSendMarketSellOrder04(self):

        codeList = self.orderCreator.getBuyCodeList()
        self.__sendCancelOrder(cancelCodeList=codeList)

        self.__sendMarketSellOrder(sellCodeList=codeList, sellWeight=1.0)


    # 당일 매매 summary logging
    @AutoRunDecorator.asyncSpotTime(startTime='15:35:30')
    async def asyncShowTradingSummary(self):

        date = datetime.now().strftime('%Y%m%d')
        self.feeder.showTradingSummary(date)


    # Process 종료
    @AutoRunDecorator.asyncSpotTime(startTime='15:45:30')
    async def asyncKillProcess(self):

        self.__killProcess()


    #########################
    ### Protected Methods ###
    #########################

    def __sendOpenMarketBuyOrder(self, buyCodeList, indMinBuyVolume, indMaxBuyVolume, totalMaxBuyVolume):
        ''' 개장 직후 시장가 + 지정가 매수 주문 '''

        orderDictList = self.orderCreator.getOpenMarketBuyOrderDictList(
            accountNum=self.accountNum,
            buyCodeList=buyCodeList,
            indMinBuyVolume=indMinBuyVolume,
            indMaxBuyVolume=indMaxBuyVolume,
            totalMaxBuyVolume=totalMaxBuyVolume,
        )

        self.executor._sendOrder(orderDictList)

    def __sendStairLimitBuyOrder(self, buyCodeList, avgBuyVolume):
        ''' 계단식 지정가 매수주문 '''

        buyOrderDictList = self.orderCreator.getStairLimitBuyOrderDictList(
            accountNum=self.accountNum,
            buyCodeList=buyCodeList,
            avgBuyVolume=avgBuyVolume,
        )

        self.executor._sendOrder(buyOrderDictList) # 매수 주문 제출

    def __sendLimitSellOrder(self, sellCodeList, tickShift=0, sellWeight=1.0):
        ''' 지정가 매도주문 '''

        limitSellOrderDictList = self.orderCreator.getLimitSellOrderDictList(
            accountNum=self.accountNum,
            sellCodeList=sellCodeList,
            tickShift=tickShift,
            sellWeight=sellWeight
        )

        self.executor._sendOrder(limitSellOrderDictList)

    def __sendStairLimitSellOrder(self, sellCodeList, sellWeight=1.0):
        ''' 계단식 지정가 매도주문 '''

        stairLimitSellOrderDictList = self.orderCreator.getStairLimitSellOrderDictList(
            accountNum=self.accountNum,
            sellCodeList=sellCodeList,
            sellWeight=sellWeight,
        )

        self.executor._sendOrder(stairLimitSellOrderDictList)

    def __sendMarketSellOrder(self, sellCodeList, sellWeight=1.0):
        ''' 시장가 매도주문 '''

        marketSellOrderDictList = self.orderCreator.getMarketSellOrderDictList(
            accountNum=self.accountNum,
            sellCodeList=sellCodeList,
            sellWeight=sellWeight
        )

        self.executor._sendOrder(marketSellOrderDictList)

    def __sendCancelOrder(self, cancelCodeList):

        while True:

            cancelOrderDictList = self.orderCreator.getCancelOrderDictList(
                accountNum=self.accountNum,
                cancelCodeList=cancelCodeList
            )

            if cancelOrderDictList:
                self.executor._sendOrder(cancelOrderDictList)

            else:
                break

    def __sendStopLossOrder(self, threshold=-0.05, sellWeight=1.0):
        ''' 손절매 주문

        params
        ===============================
        threshold: float, 손절매 기준 수익률 defalut=-0.05 (-5%)
        sellWeight: float, 잔고 대비 매도 비중
        '''

        marketSellCodeList = []

        buyCodeList = self.orderCreator.getBuyCodeList()
        inventoryDictList = self.feeder.getInventoryDictList(self.accountNum)

        for dict in inventoryDictList:

            rt = dict['손익율']
            stockCode = dict['종목코드']

            if not stockCode in buyCodeList: # 해당 전략에서 매수하지 않은 종목은 건드리지 않음
                continue

            if rt < threshold: # -5% 이상 손실난 종목은 시장가로 청산
                marketSellCodeList.append(stockCode)

        # 주문정보 생성 및 집행
        marketSellOrderDictList = self.orderCreator.getMarketSellOrderDictList(
            accountNum=self.accountNum,
            sellCodeList=marketSellCodeList,
            sellWeight=sellWeight,
        )

        self.executor._sendOrder(marketSellOrderDictList)

    def __sendProfitTakingOrder(self, threshold=0.15, sellWeight=1.0):
        ''' 익절매 주문

        params
        ===============================
        threshold: float, 손절매 기준 수익률 defalut=0.15 (15%)
        sellWeight: float, 잔고 대비 매도 비중
        '''

        marketSellCodeList = []

        buyCodeList = self.orderCreator.getBuyCodeList()
        inventoryDictList = self.feeder.getInventoryDictList(self.accountNum)

        for dict in inventoryDictList:

            rt = dict['손익율']
            stockCode = dict['종목코드']

            if not stockCode in buyCodeList: # 해당 전략에서 매수하지 않은 종목은 건드리지 않음
                continue

            if rt > threshold: # 15% 이상 수익난 종목은 시장가로 청산
                marketSellCodeList.append(stockCode)

        marketSellOrderDictList = self.orderCreator.getMarketSellOrderDictList(
            accountNum=self.accountNum,
            sellCodeList=marketSellCodeList,
            sellWeight=sellWeight,
        )

        self.executor._sendOrder(marketSellOrderDictList)

    ##########################
    ##### Support Methods ####
    ##########################

    def connect(self):
        self.broker.commConnect()

    # Support Methods
    def checkServerStatus(self):
        try:
            serverStatus = self.broker.getConnectState() # 0 미연결, 1: 연결

            if serverStatus:
                self.logger.debug('{} Server Connection : OK'.format(datetime.now()))

            else:
                raise KiwoomConnectError

        except KiwoomConnectError:
            self.logger.error('{} Server Connection : Fail => Trying to reconnect to Server'.format(datetime.now()))
            self.connect()

    # Support Methods
    def killOldProcess(self):
        # 이전에 실행된 Process는 꺼버리고 새로운 Process로 실행 (중복 방지).
        try:
            pidPath = 'data/pid.txt'
            pid = int(readTxt(pidPath))

            os.kill(pid, signal.SIGTERM)

        except:
            pass

        finally: # 새롭게 실행한 Process ID를 기록
            newPid = os.getpid()
            saveTxt(newPid, pidPath)

    def __killProcess(self):
        ''' 현재 AlgoRuuner가 실행중인 process kill '''
        os.kill(os.getpid(), signal.SIGTERM)
