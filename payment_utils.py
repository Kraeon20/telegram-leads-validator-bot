from pymongo import MongoClient
import os
import certifi
from dotenv import load_dotenv

load_dotenv()
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN'))

MONGO_URI = os.getenv('MONGO_URI')


client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['telegram_leads_bot']

carrier_collections = {
    'bell_bc': db['bell_bc'],
    'bell_ontario': db['bell_ontario'],
    'bell_alberta': db['bell_alberta'],
    'telus_bc': db['telsus_bc'],
    'telus_ontario': db['telsus_ontario'],
    'telus_alberta': db['telus_alberta'],
    'rogers_bc': db['rogers_bc'],
    'rogers_ontario': db['rogers_ontario'],
    'rogers_alberta': db['rogers_alberta']
}

payments = db['payments']

def mark_leads_as_sold(carrier_collection, amount):
    leads = carrier_collections[carrier_collection].find({"sold": False}).limit(amount)
    lead_ids = [lead['_id'] for lead in leads]
    carrier_collections[carrier_collection].update_many({"_id": {"$in": lead_ids}}, {"$set": {"sold": True}})
    return leads

def get_payment_by_id(payment_id):
    return payments.find_one({"payment_id": payment_id})

def update_payment_status(payment_id, new_status):
    payments.update_one({"payment_id": payment_id}, {"$set": {"status": new_status}})