
import os
from destsqldbfuncs import SqlDBFunctions
from commonutils import map_event_type_destination,map_source_db,split_etk_event_payloads
import json


def recondestination(dbclient,main_staging_collection,main_table_collection,recon_threshold_count,logger):

    # DONE: Query records in staging table
    results = main_staging_collection.find()
    reconstatus=True

    # DONE: Query for each record in destination db(based on row type)
    for row in results:
        # DONE: If found delete from staging if not update recon count column
        logger.debug('processing row')
        logger.debug(row)
        datasrc=''
        if row['datasource']:
            datasrc=row['datasource']
        else:
            continue
        if row['recon_count']:
            if row['recon_count']>recon_threshold_count:
                logger.error('recon count exceeded threshold. skipping row')
                continue
        if datasrc=='df':
            try:
                if row['eventType']:
                    bi_table_name=map_event_type_destination(row['eventType'])
                    bi_db_name=map_source_db(row['datasource'])
                    # print(bi_db_name)
                    # DONE: Query SQL DB
                    bi_sql_db_obj = SqlDBFunctions(bi_db_name, os.getenv('BI_SQL_DB_SERVER'),os.getenv('BI_SQL_DB_USERNAME'), os.getenv('BI_SQL_DB_PASSWORD'))
                    qrystr = bi_sql_db_obj.prepQuerystr(row['payloaddata'],row['datasource'])
                    table_name=bi_table_name
                    reconqrystr = f'SELECT * FROM {table_name} WHERE {qrystr}'
                    # print(reconqrystr)
                    found = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                    if found:
                        main_staging_collection.delete_one(row)
                        # DONE: If found save to master table
                        # DONE: Dedup before saving to master
                        query_main_table = main_table_collection.find(row)
                        if len(list(query_main_table)) > 0:
                            return True
                        else:
                            result = main_table_collection.insert_one(row)
                    else:
                        recon_count_val = (lambda x: 1 if not ('recon_count' in x.keys()) else x['recon_count'] + 1)(row)
                        new_column = {"$set": {"recon_count": recon_count_val}}
                        result = main_staging_collection.update_one(row, new_column)
            except Exception as e:
                reconstatus=False
                recon_count_val = (lambda x: 1 if not ('recon_count' in x.keys()) else x['recon_count'] + 1)(row)
                new_column = {"$set": {"recon_count": recon_count_val}}
                result = main_staging_collection.update_one(row, new_column)
                logger.error('error in recon for this row')
                logger.error(row)
                logger.error(e)
        elif datasrc=='etk':
            try:
                if row['eventType']:
                    bi_table_name=map_event_type_destination(row['eventType'])
                    bi_db_name=map_source_db(row['datasource'])
                    bi_events_table_name = os.getenv('BI_ETK_EVENTS_TABLE')
                    bi_violations_table_name = os.getenv('ETK_VIOLATIONS_TABLE_NAME')
                    bi_geo_table=os.getenv('ETK_GEOLOCATION_TABLE_NAME')
                    # print(bi_db_name)
                    # DONE: Query SQL DB
                    bi_sql_db_obj = SqlDBFunctions(bi_db_name, os.getenv('BI_SQL_DB_SERVER'),os.getenv('BI_SQL_DB_USERNAME'), os.getenv('BI_SQL_DB_PASSWORD'))
                    mainpayload,eventpayload,countspayload,geopayload=split_etk_event_payloads(row['payloaddata'],row['eventType'])
                    mainqrystr,eventqrystr,countsqrystr=None,None,None
                    mainfound, eventfound, countsfound,geofound = False, False, False,False
                    if mainpayload:
                        mainqrystr = bi_sql_db_obj.prepQuerystr(mainpayload,row['datasource'])
                        table_name=(lambda x: bi_geo_table if x['eventType']=='geolocation' else bi_table_name)(row)
                        # table_name = bi_table_name
                        reconqrystr = f'SELECT * FROM {table_name} WHERE {mainqrystr}'
                        mainfound = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                    if eventpayload:
                        eventqrystr = bi_sql_db_obj.prepQuerystr(eventpayload,row['datasource'])
                        table_name = bi_events_table_name
                        reconqrystr = f'SELECT * FROM {table_name} WHERE {eventqrystr}'
                        eventfound = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                    else:
                        eventfound=True
                    if countspayload:
                        for countsrw in countspayload:
                            tmp_countsrw=json.dumps(countsrw)
                            countsqrystr = bi_sql_db_obj.prepQuerystr(tmp_countsrw,row['datasource'])
                            print(countsqrystr)
                            table_name = bi_violations_table_name
                            reconqrystr = f'SELECT * FROM {table_name} WHERE {countsqrystr}'
                            countsfound = bi_sql_db_obj.reconQuery(reconqrystr,logger)
                            if not countsfound:
                                break
                    else:
                        countsfound=True
                    if geopayload:
                        eventqrystr = bi_sql_db_obj.prepQuerystr(geopayload, row['datasource'])
                        table_name = bi_geo_table
                        reconqrystr = f'SELECT * FROM {table_name} WHERE {eventqrystr}'
                        print(f'Here is: {reconqrystr}')
                        geofound = bi_sql_db_obj.reconQuery(reconqrystr, logger)
                    else:
                        geofound=True
                    # qrystr = bi_sql_db_obj.prepQuerystr(row['payloaddata'],row['datasource'])
                    
                    if mainfound and eventfound and countsfound and geofound:
                        main_staging_collection.delete_one(row)
                        # DONE: If found save to master table
                        # DONE: Dedup before saving to master
                        query_main_table = main_table_collection.find(row)
                        if len(list(query_main_table)) > 0:
                            return True
                        else:
                            result = main_table_collection.insert_one(row)
                    else:
                        recon_count_val = (lambda x: 1 if not ('recon_count' in x.keys()) else x['recon_count'] + 1)(row)
                        new_column = {"$set": {"recon_count": recon_count_val}}
                        result = main_staging_collection.update_one(row, new_column)
            except Exception as e:
                reconstatus=False
                recon_count_val = (lambda x: 1 if not ('recon_count' in x.keys()) else x['recon_count'] + 1)(row)
                new_column = {"$set": {"recon_count": recon_count_val}}
                result = main_staging_collection.update_one(row, new_column)
                logger.error('error in recon for this row')
                logger.error(row)
                logger.error(e)
    return reconstatus





 # try:
 #            if row['event_type'] and row['event_type']== 'event_1':
 #
 #                table_name=os.getenv('BI_SQL_APP1_TABLE1')
 #                # reconqrystr=f'SELECT * FROM {os.getenv("BI_SQL_APP1_DB")}.{os.getenv("BI_SQL_APP1_SCHEMA")}.{table_name} WHERE {qrystr}'
 #                # found=bi_sql_db_obj.reconQuery(reconqrystr)
 #                # print(qrystr)
 #                # found=False