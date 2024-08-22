import logging
import os
from pymongo import MongoClient
from reconexceptions import reconExceptions

client=MongoClient(os.environ.get('MONGO_URL'))
db = client[os.environ.get('RECON_DB_NAME')]
main_staging_collection = db[os.getenv('MAIN_STG_COLLECTION')]
err_threshold=os.getenv('ERR_THRESHOLD_COUNT')
recon_threshold_count=int(os.getenv('RECON_THRESHOLD_COUNT'))

numeric_level = getattr(logging, os.getenv('LOG_LEVEL').upper(), 10)
# Set up logging
logging.basicConfig(
    # level=logging[os.getenv('LOG_LEVEL')],
    level=numeric_level,
    format='%(asctime)s %(levelname)s %(module)s:%(lineno)d [RIDE_RECON]: %(message)s'
)

def main():
  logging.info("Resend Exceptions process starting")

  reconExceptions(client,
                  main_staging_collection,
                  recon_threshold_count,
                  logging)
  
  logging.info("Resend Exceptions process finished")

main()