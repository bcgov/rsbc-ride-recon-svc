import json

from fastapi import FastAPI,Response,Query,Request
from fastapi.responses import PlainTextResponse,JSONResponse
import os
from pymongo import MongoClient
import uvicorn
import logging
from typing import List, Optional

from reconfunctions import recondestination
from errorretryfunctions import error_retry_task


numeric_level = getattr(logging, os.getenv('LOG_LEVEL').upper(), 10)
# Set up logging
logging.basicConfig(
    # level=logging[os.getenv('LOG_LEVEL')],
    level=numeric_level,
    format='%(asctime)s %(levelname)s %(module)s:%(lineno)d [RIDE_RECON]: %(message)s'
)

app = FastAPI()



client=MongoClient(os.environ.get('MONGO_URL'))
# db = client['kafkaevents']
db = client[os.environ.get('RECON_DB_NAME')]
main_staging_collection = db[os.getenv('MAIN_STG_COLLECTION')]
err_staging_collection = db[os.getenv('ERR_STG_COLLECTION')]
main_table_collection = db[os.getenv('MAIN_TABLE_COLLECTION')]
err_table_collection=db[os.getenv('ERR_TABLE_COLLECTION')]
err_threshold=os.getenv('ERR_THRESHOLD_COUNT')
recon_threshold_count=int(os.getenv('RECON_THRESHOLD_COUNT'))

@app.get('/ping', response_class=JSONResponse)
async def main_ping():
    return JSONResponse(status_code=200, content={"status":"working"})



@app.post('/savemainstaging', response_class=JSONResponse)
async def save_main_staging_data(payload: dict):
    logging.info('triggering call to save payload in main staging table')
    respstatus={"status":"failure"}
    status_code=500
    try:
        payloadinput=payload.copy()
        payloadinput['payloadstr']=json.dumps(payload["payloaddata"])
        logging.debug('here is the payload to be saved to main staging table')
        logging.debug(payloadinput)
        # DONE: Dedup before saving to error staging
        query_main_staging = main_staging_collection.find(payloadinput)
        if len(list(query_main_staging)) > 0:
            logging.info('skipping saving to main staging.found duplicate.')
        else:
            result = main_staging_collection.insert_one(payloadinput)
        respstatus = {"status": "success"}
        status_code=200
    except Exception as e:
        logging.info('error in saving to staging main table')
        logging.error('error in saving to staging main table')
        logging.error(e)

    return JSONResponse(status_code=status_code, content=respstatus)

@app.post('/saveerrorstaging', response_class=JSONResponse)
async def save_err_staging_data(payload: dict):
    logging.info('triggering call to save payload in error staging table')
    respstatus={"status":"failure"}
    status_code = 500
    try:
        payloadinput=payload.copy()
        payloadinput['payloadstr']=json.dumps(payload["payloaddata"])
        logging.debug('here is the payload to be saved to error staging table')
        logging.debug(payloadinput)
        # DONE: Dedup before saving to error staging
        query_err_staging=err_staging_collection.find(payloadinput)
        if len(list(query_err_staging))>0:
            logging.info('skipping saving to error staging.found duplicate.')
        else:
            result = err_staging_collection.insert_one(payloadinput)
        respstatus = {"status": "success"}
        status_code = 200
    except Exception as e:
        logging.info('error in saving to error main table')
        logging.error('error in saving to error main table')
        logging.error(e)

    return JSONResponse(status_code=status_code, content=respstatus)

@app.get('/riderecon', response_class=JSONResponse)
async def recon_destination():
    logging.info('trigering recon job')
    respstatus = {"status": "failure"}
    status_code = 500
    try:
        recon_out=recondestination(client,main_staging_collection,main_table_collection,recon_threshold_count,logging)
        if not(recon_out):
            raise Exception('error in one of the rows during recon')
        respstatus = {"status": "success"}
        status_code = 200
    except Exception as e:
        logging.info('error in recon job')
        logging.error('error in recon job')
        logging.error(e)

    return JSONResponse(status_code=status_code, content=respstatus)

@app.get('/rideerrorretry', response_class=JSONResponse)
async def error_retry():
    logging.info('trigering error retry job')
    respstatus = {"status": "failure"}
    status_code = 500
    try:
        error_retry_out=error_retry_task(client,err_staging_collection,err_table_collection,err_threshold,logging)
        if not(error_retry_out):
            raise Exception('error in one of the rows during retry')
        respstatus = {"status": "success"}
        status_code = 200
    except Exception as e:
        logging.info('error in error retry job')
        logging.error('error in eror retry job')
        logging.error(e)

    return JSONResponse(status_code=status_code, content=respstatus)


@app.get("/querytable", response_class=JSONResponse)
async def get_records(request: Request,collection_name: Optional[str] = Query(..., title="collection_name")):
    status_code = 500
    qry_resp=[]
    try:
        query = {}
        params = request.query_params
        logging.info('trigering query')
        qry_staging_collection = db[collection_name]
        # print(collection)
        for key, value in params.items():
            if key=="collection_name":
                pass
            elif key=="eventid":
                query[key]=int(value)
            else:
                query[key]=value
        if len(query)==0:
            query_rslt = qry_staging_collection.find()
        else:
            query_rslt = qry_staging_collection.find(query)
            # print(list(query_rslt))
        qry_resp=list(query_rslt)
        for rec in qry_resp:
            rec["_id"] = str(rec["_id"])
            rec["payloaddata"]=json.loads(rec["payloaddata"])
        if len(qry_resp) == 0:
            logging.info('no records found for the query')
            logging.error('no records found for the query')
            status_code = 404
        else:
            status_code=200
    except Exception as e:
        logging.info('error in query')
        logging.error('error in query')
        logging.error(e)
    return JSONResponse(status_code=status_code, content=qry_resp)


@app.patch('/updateevent/{eventid}', response_class=JSONResponse)
async def update_status(eventid: int, payload: dict):
    logging.info('trigering update')
    respstatus = {"status": "failure"}
    status_code = 500
    try:
        logging.debug('here is the payload')
        logging.debug(payload)
        collection_name=payload.get('collectionName',None)
        if collection_name is None:
            status_code = 400
            raise Exception('collection name not passed in payload')
        datapayload=payload.get('payloaddata',None)
        if datapayload is None:
            status_code = 400
            raise Exception('payloaddata not passed in payload')
        db_collection = db[collection_name]
        # query_main_staging = main_staging_collection.find({"eventid":eventid})
        db_query = db_collection.find_one({"eventid":eventid})
        if len(list(db_query)) == 0:
            logging.info('no record found for the event id')
            status_code = 404
            raise Exception('no record found for the event id')
        else:
            result = db_collection.update_one({"eventid":eventid},{"$set":datapayload})
        respstatus = {"status": "success"}
        status_code = 200
    except Exception as e:
        logging.info('error in updating status')
        logging.error('error in updating status')
        logging.error(e)

    return JSONResponse(status_code=status_code, content=respstatus)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5001, reload=True)
