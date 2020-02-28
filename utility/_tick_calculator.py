class TickCaculator:

    tickIntervalDict = {
        # KOSPI
        "KOSPI": (
            list(range(0, 1000, 1))  # 1,000원 미만
            + list(range(1000, 5000, 5))  # 1,000 ~ 5,000
            + list(range(5000, 10000, 10))  # 5,000 ~ 10,000
            + list(range(10000, 50000, 50))  # 10,000 ~ 50,000
            + list(range(50000, 100000, 100))  # 50,000 ~ 100,000
            + list(range(100000, 500000, 500))  # 100,000 ~ 500,000
            + list(range(500000, 5000000, 1000))  # 500,000 ~ 5,000,000
        ),
        # KOSDAQ
        "KOSDAQ": (
            list(range(0, 1000, 1))  # 1,000원 미만
            + list(range(1000, 5000, 5))  # 1,000 ~ 5,000
            + list(range(5000, 10000, 10))  # 5,000 ~ 10,000
            + list(range(10000, 50000, 50))  # 10,000 ~ 50,000
            + list(range(50000, 2000000, 100))  # 50,000 ~
        ),
    }

    def calPrice(self, curPrice, k, market):
        """
        현재가 기준으로 k틱 기준 가격을 반홥합니다.

        params
        ==========================================

        curPrice: int, 현재가
        k: int, 현재가 기준 틱 변화량
        market: str, KOSPI, KOSDAQ
        """

        if not market in ["KOSPI", "KOSDAQ"]:
            raise ParameterValueError()

        tickInvertalList = self.tickIntervalDict[market]

        idx = tickInvertalList.index(curPrice)

        newIdx = idx + k
        newPrice = tickInvertalList[newIdx]

        return newPrice
