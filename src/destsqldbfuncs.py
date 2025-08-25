
import pymssql
import os
import json

class SqlDBFunctions():

    def __init__(self,dbname,dbserver,dbusername,dbpassword):
        self.dbcon=pymssql.connect(server=dbserver, database=dbname, user=dbusername, password=dbpassword)
        self.cursor = self.dbcon.cursor()

    @staticmethod
    def prepQuerystr(payload,datasource):
        # print('in prep str')
        # print(payload)
        tmpstr=''
        if datasource=='df':
            tmpPayload=json.loads(payload)
            keys=tmpPayload.keys()
            payloadKey=""
            for v in keys:
                if "payload".upper() in v.upper():
                    payloadKey=v
            if isinstance(tmpPayload[payloadKey], list):
                payloadForstr=tmpPayload[payloadKey][0]
            else:
                payloadForstr=tmpPayload[payloadKey]
            for k,v in payloadForstr.items():
                if not(v==None):
                    if (isinstance(v, str) and v.count("'") > 0):
                        value = v.replace("'", "''")
                    else:
                        value = v
                    tmpstr=tmpstr+f"{k}='{value}'"+ " AND "
            # print(tmpstr[:-5])
        else:
            tmpPayload = json.loads(payload)
            for k, v in tmpPayload.items():
                if not (v == None):
                    if (isinstance(v, str) and v.count("'") > 0):
                        value = v.replace("'", "''")
                    else:
                        value = v
                    tmpstr = tmpstr + f"{k}='{value}'" + " AND "
        return tmpstr[:-5]
       # else:
       #      tmpstr = ''
       #      tmpPayload = json.loads(payload)
       #      keys = tmpPayload.keys()
       #      payloadKey = ""
       #      for v in keys:
       #         if "payload" in v:
       #              payloadKey = v
       #      payloadForstr = tmpPayload[payloadKey][0]
       #      for k, v in payloadForstr.items():
       #          if not (v == None):
       #              tmpstr = tmpstr + f"{k}='{v}'" + " AND "
       #      # print(tmpstr[:-5])
       #      return tmpstr[:-5]



    def reconQuery(self,queryStr,logger):
        logger.debug(queryStr)
        recordfound=False
        result = self.cursor.execute(queryStr)
        rows = self.cursor.fetchall()
        logger.debug(rows)

        if len(rows)>0:
            recordfound=True

        return recordfound

