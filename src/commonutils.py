
import os
import json

event_table_mapping = {
    'app_accepted': os.getenv('DF_APP_ACCPTED_TABLE_NAME'),
    'disclosure_sent': os.getenv('DF_DISCLOSURE_SENT_TABLE_NAME'),
    'evidence_submitted': os.getenv('DF_EV_SUBMTTED_TABLE_NAME'),
    'payment_received': os.getenv('DF_PAY_RECVD_TABLE_NAME'),
    'review_scheduled': os.getenv('DF_REV_SCHED_TABLE_NAME'),
    'etk_disputeupdate': os.getenv('ETK_DISP_UPDATE_TABLE_NAME'),
    'etk_issuance': os.getenv('ETK_ISSUANCE_TABLE_NAME'),
    'etk_violations': os.getenv('ETK_VIOLATIONS_TABLE_NAME'),
    'etk_payment': os.getenv('ETK_PAYMENT_TABLE_NAME'),
    'payment_query': os.getenv('ETK_PAYQUERY_TABLE_NAME'),
    'etk_dispute': os.getenv('ETK_DISPUTE_TABLE_NAME'),
    'geolocation': os.getenv('ETK_GEOLOCATION_TABLE_NAME'),
    'vi_submitted': os.getenv('DF_VI_SUBMITTED_TABLE_NAME'),
    '12hr_submitted': os.getenv('DF_12HR_SUBMITTED_TABLE_NAME'),
    '24hr_submitted': os.getenv('DF_24HR_SUBMITTED_TABLE_NAME')
}
source_db_mapping = {
    'df': os.getenv('DF_BI_DB'),
    'etk': os.getenv('ETK_BI_DB')
}

def map_event_type_destination(event_type):
    tableName = event_table_mapping.get(event_type)
    if tableName is None:
        raise ValueError(f"Table name not found for event type: {event_type}")
    return tableName

def map_source_db(source):
    return source_db_mapping.get(source)

def split_etk_event_payloads(payload,eventtype):
    payload_dict=json.loads(payload)
    eventpayload = None
    countspayload = None
    geopayload = None
    if eventtype=='geolocation':
        tmp_event=payload_dict.pop('event')
        main_event={}
        main_event['business_id']=payload_dict['ticket_number']
        payload_dict=main_event
    else:
        eventpayload=payload_dict.pop('event')
        countspayload=None
        geopayload=None
        if eventtype=='etk_issuance':
            countspayload=payload_dict.pop('counts')
            geopayload={}
            geopayload['business_id']=payload_dict['ticket_number']
            geopayload=json.dumps(geopayload)
            main_event = {}
            main_event['ticket_number'] = payload_dict['ticket_number']
            payload_dict = main_event
        eventpayload=json.dumps(eventpayload)
    return json.dumps(payload_dict),eventpayload,countspayload,geopayload

# def map_source_api_keys(source):
#     if source=='df':
#         return os.getenv('R')
#     elif source=='etk':
#         return os.getenv('ETK_BI_DB')