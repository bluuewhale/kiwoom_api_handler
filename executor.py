

class Executor:
    def __init__(self, broker):
        self.broker = broker

    def _sendOrder(self, orderDictList):
        '''
        API(broker)를 통해 주문을 제출하는 메서드

        params
        ===============================================
        Kiwoom.py sendOrder method의 arguments 참조

        orderInfoList : list
        => each element = {
            'requestName' : str,
            'screenNum' : str,
            'accountNum' : str,
            'orderType' : int
            'code' : str,
            'qty' : int,
            'price' : int
            'hogaType' : str
            'originOrderNum' : str,
        }
        '''

        if isinstance(orderDictList, list):
            for orderDict in orderDictList:
                self.broker.sendOrder(**orderDict)

        elif isinstance(orderDictList, dict):
            self.broker.sendOrder(**orderDictList)
