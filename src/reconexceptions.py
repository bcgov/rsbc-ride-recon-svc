import os
import json
import logging
from destsqldbfuncs import SqlDBFunctions
from commonutils import map_event_type_destination,map_source_db,split_etk_event_payloads
from errorretryfunctions import staging_retry_task
from pymongo import collection, MongoClient


def reconExceptions(dbclient: MongoClient,
                    main_staging_collection: collection.Collection,
                    recon_threshold_count: int,
                    logger: logging):

    results = main_staging_collection.find({ "recon_count": { "$gt": recon_threshold_count } })
    count=0
    datasrc=""

    for row in results:
        count +=1
        logger.info("processing row %i - %s", row["eventid"], row["eventType"])
        logger.debug(row["payloaddata"])
        
        datasrc=row['datasource']
        if datasrc=='df':
            try:
                if row['eventType']:
                    bi_table_name=map_event_type_destination(row['eventType'])
                    bi_db_name=map_source_db(row['datasource'])

                    bi_sql_db_obj = SqlDBFunctions(bi_db_name, os.getenv('BI_SQL_DB_SERVER'),os.getenv('BI_SQL_DB_USERNAME'), os.getenv('BI_SQL_DB_PASSWORD'))
                    qrystr = bi_sql_db_obj.prepQuerystr(row['payloaddata'],row['datasource'])
                    reconqrystr = f'SELECT * FROM {bi_table_name} WHERE {qrystr}'
                    found = bi_sql_db_obj.reconQuery(reconqrystr, logger)
                    if found:
                        new_column = {"$set": {"recon_count": 1}}
                        result = main_staging_collection.update_one(row, new_column)
                    else:
                        retry_status=staging_retry_task(dbclient,row,logger)
                        if retry_status:
                            main_staging_collection.delete_one(row)
            except Exception as e:
                logger.error('error in reconExceptions for this row')
                logger.error(row)
                logger.error(e)
                break
        elif datasrc=='etk':
            try:
                if row['eventType']:
                    bi_table_name=map_event_type_destination(row['eventType'])
                    bi_db_name=map_source_db(row['datasource'])
                    bi_events_table_name = os.getenv('BI_ETK_EVENTS_TABLE')
                    bi_violations_table_name = os.getenv('ETK_VIOLATIONS_TABLE_NAME')
                    bi_geo_table=os.getenv('ETK_GEOLOCATION_TABLE_NAME')

                    bi_sql_db_obj = SqlDBFunctions(bi_db_name, os.getenv('BI_SQL_DB_SERVER'),os.getenv('BI_SQL_DB_USERNAME'), os.getenv('BI_SQL_DB_PASSWORD'))
                    mainpayload,eventpayload,countspayload,geopayload=split_etk_event_payloads(row['payloaddata'],row['eventType'])
                    mainqrystr,eventqrystr,countsqrystr=None,None,None
                    mainfound, eventfound, countsfound,geofound = False, False, False,False
                    if mainpayload:
                        mainqrystr = bi_sql_db_obj.prepQuerystr(mainpayload,row['datasource'])
                        table_name=(lambda x: bi_geo_table if x['eventType']=='geolocation' else bi_table_name)(row)
                        reconqrystr = f'SELECT * FROM {table_name} WHERE {mainqrystr}'
                        logger.debug(f'here is the query string for main table: {reconqrystr}')
                        mainfound = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                    if eventpayload:
                        eventqrystr = bi_sql_db_obj.prepQuerystr(eventpayload,row['datasource'])
                        table_name = bi_events_table_name
                        reconqrystr = f'SELECT * FROM {table_name} WHERE {eventqrystr}'
                        logger.debug(f'here is the query string for event table: {reconqrystr}')
                        eventfound = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                    else:
                        eventfound=True
                    if countspayload:
                        for countsrw in countspayload:
                            send_countsrw = {}
                            send_countsrw['ticket_number'] = countsrw['ticket_number']
                            send_countsrw['count_number'] = countsrw['count_number']
                            tmp_countsrw=json.dumps(send_countsrw)
                            countsqrystr = bi_sql_db_obj.prepQuerystr(tmp_countsrw,row['datasource'])
                            print(countsqrystr)
                            table_name = bi_violations_table_name
                            reconqrystr = f'SELECT * FROM {table_name} WHERE {countsqrystr}'
                            logger.debug(f'here is the query string for counts table: {reconqrystr}')
                            countsfound = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                            if not countsfound:
                                break
                    else:
                        countsfound=True
                    if geopayload:
                        eventqrystr = bi_sql_db_obj.prepQuerystr(geopayload, row['datasource'])
                        table_name = bi_geo_table
                        reconqrystr = f'SELECT * FROM {table_name} WHERE {eventqrystr}'
                        logger.debug(f'here is the query string for geo table: {reconqrystr}')
                        geofound = bi_sql_db_obj.reconQuery(reconqrystr, logger)
                    else:
                        geofound=True
                    
                    if mainfound and eventfound and countsfound and geofound:
                        new_column = {"$set": {"recon_count": 1}}
                        result = main_staging_collection.update_one(row, new_column)
                        logger.debug("update result: %s", result)
                    else:
                        retry_status=staging_retry_task(dbclient,row,logger)
                        if retry_status:
                            main_staging_collection.delete_one(row)                   
            except Exception as e:
                logger.error('error in reconExceptions for this row')
                logger.error(row)
                logger.error(e)
                break
          
    logger.info("Count %i", count)



