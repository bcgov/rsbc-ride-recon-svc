
import os
import json

def map_event_type_destination(event_type):
    if event_type=='app_accepted':
        return os.getenv('DF_APP_ACCPTED_TABLE_NAME')
    elif event_type=='disclosure_sent':
        return os.getenv('DF_DISCLOSURE_SENT_TABLE_NAME')
    elif event_type=='evidence_submitted':
        return os.getenv('DF_EV_SUBMTTED_TABLE_NAME')
    elif event_type=='payment_received':
        return os.getenv('DF_PAY_RECVD_TABLE_NAME')
    elif event_type=='review_scheduled':
        return os.getenv('DF_REV_SCHED_TABLE_NAME')
    elif event_type=='etk_disputeupdate':
        return os.getenv('ETK_DISP_UPDATE_TABLE_NAME')
    elif event_type=='etk_issuance':
        return os.getenv('ETK_ISSUANCE_TABLE_NAME')
    elif event_type=='etk_violations':
        return os.getenv('ETK_VIOLATIONS_TABLE_NAME')
    elif event_type=='etk_payment':
        return os.getenv('ETK_PAYMENT_TABLE_NAME')
    elif event_type=='payment_query':
        return os.getenv('ETK_PAYQUERY_TABLE_NAME')
    elif event_type=='etk_dispute':
        return os.getenv('ETK_DISPUTE_TABLE_NAME')
    elif event_type == 'geolocation':
        return os.getenv('ETK_GEOLOCATION_TABLE_NAME')

def map_source_db(source):
    if source=='df':
        return os.getenv('DF_BI_DB')
    elif source=='etk':
        return os.getenv('ETK_BI_DB')


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