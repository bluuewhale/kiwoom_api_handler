import os
import sys

from ..api.errors import ParameterTypeError, ParameterValueError


class TickCaculator:

    tickIntervalDict = {
        # KOSPI
        "KOSPI": (
            list(range(0, 1000, 1))  # 1,000원 미만 구간
            + list(range(1000, 5000, 5))  # 1,000 ~ 5,000 구간
            + list(range(5000, 10000, 10))  # 5,000 ~ 10,000 구간
            + list(range(10000, 50000, 50))  # 10,000 ~ 50,000 구간
            + list(range(50000, 100000, 100))  # 50,000 ~ 100,000 구간
            + list(range(100000, 500000, 500))  # 100,000 ~ 500,000 구간
            + list(range(500000, 5000000, 1000))  # 500,000 ~ 5,000,000 구간
        ),
        # KOSDAQ
        "KOSDAQ": (
            list(range(0, 1000, 1))  # 1,000원 미만 구간
            + list(range(1000, 5000, 5))  # 1,000 ~ 5,000 구간
            + list(range(5000, 10000, 10))  # 5,000 ~ 10,000 구간
            + list(range(10000, 50000, 50))  # 10,000 ~ 50,000 구간
            + list(range(50000, 2000000, 100))  # 50,000 이상 구간
        ),
    }

    def calcShiftedPrice(self, price, tickShift, market):
        """
        현재가 기준으로 k틱 기준 가격을 반홥합니다.
        ex) KOSPI 시장에 상장된 종목의 현재가가 6000원 일때,
        6020 == calShiftedPrice(6000, 2, "KOSPI")

        params
        ==========================================

        price: int, 현재가
        tickShift: int, 현재가 기준 틱 변화량
        market: str, KOSPI, KOSDAQ
        """
        if not (
            isinstance(price, int),
            isinstance(tickShift, int),
            isinstance(market, str),
        ):
            raise ParameterTypeError()

        if not ((price < 0), (market in ["KOSPI", "KOSDAQ"])):
            raise ParameterValueError()

        tickInvertalList = self.tickIntervalDict[market]

        idx = tickInvertalList.index(price)
        newIdx = idx + tickShift
        newPrice = tickInvertalList[newIdx]
        return newPrice
