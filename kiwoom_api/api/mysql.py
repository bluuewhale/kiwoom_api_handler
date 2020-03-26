import pymysql
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from kiwoom_api.api._api_config import DatabaseConfig

class MySql:

    def __init__(self, *args, **kwargs):
        self.config = kwargs
    
    def insert(self, table, **kwargs):
        try:
            conn = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return

        try:
            curs = conn.cursor()
            keys = tuple(kwargs.keys())
            values = tuple(kwargs.values())

            sql = f'INSERT INTO {table}{keys} '.replace("'", "")
            sql += f'VALUES{values}'
            curs.execute(sql)
            conn.commit()

        finally:
            conn.close()
            

if __name__ == "__main__":
    config = getattr(DatabaseConfig, 'config')
    mysql = MySql(**config)
    data = {
        'ACCOUNT_NO': '8131214911',
        'BASC_DT': '20200326',
        'HOGA_TYPE': '시장가',
        'NAME': '삼성전자',
        'ORDER_GUBUN': '+매수',
        'ORDER_NO': '0176680',
        'ORDER_PRICE': '0',
        'ORDER_QTY': '1',
        'ORDER_STATUS': '체결',
        'ORDER_TRAN_TIME': '151922',
        'ORIGINAL_ORDER_NO': '0000000',
        'SELL_BUY_GUBUN': '2',
        'TICKER': 'A005930',
        'TRAN_NO': '570408',
        'TRAN_PRICE': '47850',
        'TRAN_QTY': '1',
        'UNEX_QTY': '0'
    }
    
    mysql.insert(table='order_executed', **data)

    