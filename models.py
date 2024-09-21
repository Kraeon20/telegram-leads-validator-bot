from pymongo import MongoClient
import certifi
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGO_URI = 'mongodb+srv://williams:Priscilla2058@foxscraper.gqqxf.mongodb.net/?retryWrites=true&w=majority&appName=foxscraper'
SUPER_ADMIN_ID = 6376544784

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['leads_bot']

# Collections
admins = db['admins']
subscribers = db['subscribers']
payments = db['payments']



carrier_collections = {
    'bell_bc': db['bell_bc'],
    'bell_ontario': db['bell_ontario'],
    'bell_alberta': db['bell_alberta'],
    'telsus_bc': db['telsus_bc'],
    'telsus_ontario': db['telsus_ontario'],
    'telsus_alberta': db['telsus_alberta'],
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
    # Check if the admin exists
    admin = admins.find_one({"admin_id": admin_id})
    if admin:
        # Remove the admin from the admins collection
        admins.delete_one({"admin_id": admin_id})
        
        # Update the subscriber's role to remove admin privileges
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
    

def save_payment(user_id, amount, status='pending'):
    payment_data = {
        'user_id': user_id,
        'amount': amount,
        'status': status,
        'date': datetime.utcnow()
    }
    payments.insert_one(payment_data)


def update_payment_status(user_id, status):
    payments.update_one(
        {'user_id': user_id, 'status': 'pending'}, 
        {'$set': {'status': status}}
    )


def check_payment_status(user_id):
    payment = payments.find_one({'user_id': user_id, 'status': 'completed'})
    return payment is not None

