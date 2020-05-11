import os
import sys

from .errors import ParameterTypeError


class Executor:
    def __init__(self, kiwoom):
        self.kiwoom = kiwoom

    def createOrderSpec(
        self,
        rqName,
        scrNo,
        accNo,
        orderType,
        code,
        qty,
        price,
        hogaType,
        originOrderNo="",
    ):
        """ 주문정보를 생성하는 매서드,
        생성된 주문정보는 sendOrder() 매서드를 통해 제출 가능

        params
        =======================================================================
        rqName: string - 주문 요청명(사용자 정의)
        scrNo: string - 화면번호(4자리)
        accNo: string - 계좌번호(10자리)
        orderType: int -
            주문유형(1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소,
            5: 매수정정, 6: 매도정정)
        code: string - 종목코드
        qty: int - 주문수량
        price: int - 주문단가
        hogaType: string
            거래구분(00: 지정가, 03: 시장가, 05: 조건부지정가, 06: 최유리지정가,
            그외에는 api 문서참조)
        originOrderNo: string
            원주문번호(신규주문에는 공백, 정정및 취소주문시 원주문번호를 입력합니다.)

        ※  시장가, 최유리지정가, 최우선지정가, 시장가IOC, 최유리IOC,시장가FOK,
            최유리FOK, 장전시간외, 장후시간외 주문시 주문가격을 입력하지 않습니다.
        """

        orderSpecDict = {
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

        return orderSpecDict

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
        originOrderNo="",
    ):
        """ API(kiwoom)를 통해 주문을 제출하는 메서드
        매개변수 설명은 createOrderSpec() 매서드 참고

        params
        ===============================================
        """
        if not isinstance(orderType, int):
            orderType = int(orderType)

        if not isinstance(qty, int):
            qty = int(qty)

        if not isinstance(price, int):
            price = int(price)

        self.kiwoom.sendOrder(
            rqName, scrNo, accNo, orderType, code, qty, price, hogaType, originOrderNo,
        )
        return getattr(self.kiwoom, "orderResponse")

