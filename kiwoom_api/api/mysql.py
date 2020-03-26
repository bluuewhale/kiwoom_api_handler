import pymysql

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
        
    