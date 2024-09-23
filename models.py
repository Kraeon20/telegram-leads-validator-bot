from pymongo import MongoClient
import os
import certifi
from datetime import datetime
from dotenv import load_dotenv
from api_payment import NOWPAYMENTS_API_KEY
from payment_utils import MONGO_URI, db

load_dotenv()
# MONGO_URI = os.environ.get('MONGO_URI')

# client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
# db = client['telegram_leads_bot']

admins = db['admins']
subscribers = db['subscribers']
payments = db['payments']


# carrier_collections = {
#     'bell_bc': db['bell_bc'],
#     'bell_ontario': db['bell_ontario'],
#     'bell_alberta': db['bell_alberta'],
#     'telus_bc': db['telsus_bc'],
#     'telus_ontario': db['telsus_ontario'],
#     'telus_alberta': db['telsus_alberta'],
#     'rogers_bc': db['rogers_bc'],
#     'rogers_ontario': db['rogers_ontario'],
#     'rogers_alberta': db['rogers_alberta']
# }

def add_admin(admin_id, username, full_name, added_by):
    if admins.find_one({"admin_id": admin_id}):
        raise ValueError("Admin already exists.")
    admins.insert_one({
        "created_at": datetime.utcnow(),
        "admin_id": admin_id,
        "username": username,
        "full_name": full_name,
        "added_by": added_by
    })


def delete_admin(admin_id):
    admin = admins.find_one({"admin_id": admin_id})
    if admin:
        admins.delete_one({"admin_id": admin_id})
        
        subscribers.update_one({"subscriber_id": admin_id}, {"$set": {"role": "subscriber"}})

        
def get_all_admins():
    return list(admins.find({}))

def add_subscribers(subscriber_id, username, full_name):
    subscribers.insert_one({
        "joined_at": datetime.utcnow(),
        "subscriber_id": subscriber_id,
        "username": username,
        "full_name": full_name
        
    })
    

def save_payment(user_id, username, full_name, amount, status, payment_id, order_description, price_currency, pay_currency):
    payments.insert_one({
        "created_at": datetime.utcnow(),
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "amount": amount,
        "status": status,
        "payment_id": payment_id,
        "order_description": order_description,
        "price_currency": price_currency,
        "pay_currency": pay_currency
    })





