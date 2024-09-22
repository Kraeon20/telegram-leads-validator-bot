from pymongo import MongoClient
import os
import time
import requests
import certifi
from datetime import datetime
from dotenv import load_dotenv
from api_payment import NOWPAYMENTS_API_KEY

load_dotenv()
MONGO_URI = os.environ.get('MONGO_URI')
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN'))

print(MONGO_URI)
print("SUPER_ADMIN_ID:", SUPER_ADMIN_ID)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['telegram_leads_bot']

admins = db['admins']
subscribers = db['subscribers']
payments = db['payments']


carrier_collections = {
    'bell_bc': db['bell_bc'],
    'bell_ontario': db['bell_ontario'],
    'bell_alberta': db['bell_alberta'],
    'telus_bc': db['telsus_bc'],
    'telus_ontario': db['telsus_ontario'],
    'telus_alberta': db['telsus_alberta'],
    'rogers_bc': db['rogers_bc'],
    'rogers_ontario': db['rogers_ontario'],
    'rogers_alberta': db['rogers_alberta']
}

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
    

def add_lead_to_carrier(carrier, phone_number, admin_id):
    """
    carrier: the key representing the carrier, e.g., 'bell_bc', 'rogers_ontario'
    phone_number: the phone number to insert
    admin_id: the ID of the admin who uploaded the lead
    """
    if carrier in carrier_collections:
        carrier_collections[carrier].insert_one({
            "uploaded_at": datetime.utcnow(),
            "phone_number": phone_number,
            "uploaded_by": admin_id,
            "carrier": carrier.replace('_', ' ').title()
        })
    else:
        raise ValueError(f"Invalid carrier: {carrier}")
    

def save_payment(user_id, username, full_name, amount, status, payment_id, order_description, price_currency, pay_currency):
    payments.insert_one({
        "created_at": datetime.utcnow(),
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "amount": amount,
        "status": "waiting",
        "payment_id": payment_id,
        "order_description": order_description,
        "price_currency": price_currency,
        "pay_currency": pay_currency
    })
    


def continuously_check_payment_status(order_id, check_interval=30):
    while True:
        try:
            print(f"Checking payment status for order ID: {order_id}")  # Print the order ID being checked

            # Retrieve the payment from the 'payments' collection by the order_id
            payment = payments.find_one({"order_id": order_id})
            if payment is None:
                print(f"No payment found with order ID: {order_id}")
                return

            payment_id = payment['order_id']  # Corrected the way to retrieve payment_id
            url = f"https://api.nowpayments.io/v1/payment/{payment_id}"
            headers = {
                'x-api-key': NOWPAYMENTS_API_KEY 
            }

            response = requests.get(url, headers=headers)
            
            # Log the response text for detailed debugging
            print(f"API response: {response.status_code}, {response.text}")

            response_data = response.json()

            if response.status_code != 200:
                print(f"API call failed: {response_data.get('error', 'Unknown error')}")
                return

            payment_status = response_data.get('payment_status')

            if payment_status == "confirmed":
                payments.update_one(
                    {"order_id": order_id},
                    {"$set": {"status": "paid"}}
                )
                print(f"Payment status updated to 'paid' for order ID: {order_id}")
                break

            else:
                print(f"Current payment status for order ID {order_id} is '{payment_status}'. Checking again in {check_interval} seconds.")

        except Exception as e:
            print(f"An error occurred: {e}")

        time.sleep(check_interval)