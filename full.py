import telebot
import os
import re
import time
import threading
from dotenv import load_dotenv
from datetime import datetime, timezone
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import time
import json
import certifi
import requests
from pymongo import MongoClient


load_dotenv()
API_TOKEN = os.environ.get('TELEGRAM_BOT_API_TOKEN')
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN'))

MONGO_URI = os.getenv('MONGO_URI')
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
    'telus_alberta': db['telus_alberta'],
    'rogers_bc': db['rogers_bc'],
    'rogers_ontario': db['rogers_ontario'],
    'rogers_alberta': db['rogers_alberta']
}

payments = db['payments']

order_id = order_id = f"order-{int(time.time())}"


bot = telebot.TeleBot(API_TOKEN)
def get_user_role(user_id):
    if user_id == SUPER_ADMIN_ID:
        return 'super_admin'
    
    user = subscribers.find_one({'subscriber_id': user_id})
    if user:
        return 'admin' if user.get('role') == 'admin' else 'subscriber'
    return 'subscriber'


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_role = get_user_role(message.chat.id)

    user = subscribers.find_one({'subscriber_id': message.chat.id})
    if not user:
        add_subscribers(
            subscriber_id=message.chat.id,
            username=message.from_user.username,
            full_name=f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        )
    else:

        if user_role == 'subscriber':
            user_role = get_user_role(message.chat.id) 

    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)

    if user_role == 'subscriber':
        bell_button = KeyboardButton("Bell")
        telus_button = KeyboardButton("Telus")
        rogers_button = KeyboardButton("Rogers")
        markup.add(bell_button, telus_button, rogers_button)
    elif user_role in ['admin', 'super_admin']:
        markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        see_users_button = KeyboardButton("See Subscribers") if user_role == 'super_admin' else None
        upload_leads_button = KeyboardButton("Upload Leads")
    
        if see_users_button:
            markup.add(see_users_button)
        
        markup.add(upload_leads_button)

    if user_role == 'super_admin':
        manage_admins_button = KeyboardButton("Manage Admins")
        markup.add(manage_admins_button)

    bot.send_message(message.chat.id, "Welcome! Please select an option:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Back")
def back_to_main_menu(message):
    send_welcome(message)
    

@bot.message_handler(func=lambda message: message.text == "Manage Admins" and get_user_role(message.chat.id) == 'super_admin')
def manage_admins(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    add_admin_button = KeyboardButton("Add Admin")
    delete_admin_button = KeyboardButton("Delete Admin")
    show_admins_button = KeyboardButton("Show All Admins")

    back_button = KeyboardButton("Back")

    markup.add(add_admin_button, delete_admin_button, show_admins_button, back_button)
    
    bot.send_message(message.chat.id, "Choose an admin management option:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Add Admin" and get_user_role(message.chat.id) == 'super_admin')
def add_admin_handler(message):
    bot.send_message(message.chat.id, "Please send the chat ID of the new admin or press 'Back' to cancel:")
    bot.register_next_step_handler(message, handle_new_admin_id)  

@bot.message_handler(func=lambda message: message.text.isdigit() and get_user_role(message.chat.id) == 'super_admin')
def handle_new_admin_id(message):

    if message.text in ["Back", "Delete Admin", "Show All Admins"]:
        bot.send_message(message.chat.id, "Operation canceled.")
        if message.text == "Back":
            send_welcome(message)
        elif message.text == "Delete Admin":
            delete_admin_handler(message)
        elif message.text == "Show All Admins":
            show_admins_handler(message)
        return
    
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Invalid input. Please provide a valid chat ID (a numeric value) or press 'Back' to cancel.")
        bot.register_next_step_handler(message, handle_new_admin_id)
        return

    # Convert text to an integer
    chat_id = int(message.text)
    
    try:
        user_info = bot.get_chat(chat_id)
        
        username = user_info.username if user_info.username else "No username"
        full_name = f"{user_info.first_name} {user_info.last_name}" if user_info.last_name else user_info.first_name

        if admins.find_one({"admin_id": chat_id}):
            bot.send_message(message.chat.id, f"{full_name} with chat ID {chat_id} is already an admin.")
            return
        
        add_admin(chat_id, username, full_name, message.chat.id)
        subscribers.update_one(
            {'subscriber_id': chat_id}, 
            {'$set': {'role': 'admin', 'username': username, 'full_name': full_name, 'joined_at': datetime.now(timezone.utc)}}, 
            upsert=True
        )
        
        bot.send_message(message.chat.id, f"You added {full_name} with chat ID {chat_id} to admins.")
    except Exception as e:
        bot.send_message(message.chat.id, "Failed to add admin. Please ensure the chat ID is correct.")
        print(f"Error: {e}")

@bot.message_handler(func=lambda message: message.text == "Delete Admin" and get_user_role(message.chat.id) == 'super_admin')
def delete_admin_handler(message):
    admins = get_all_admins()
    markup = InlineKeyboardMarkup()

    for admin in admins:
        admin_id = admin['admin_id']
        full_name = admin['full_name']
        markup.add(InlineKeyboardButton(full_name, callback_data=f"delete_admin_{admin_id}"))

    if not admins:
        bot.send_message(message.chat.id, "No admins to delete.")
    else:
        bot.send_message(message.chat.id, "Select an admin to delete:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_admin_'))
def handle_delete_admin_callback(call):
    admin_id = int(call.data.split('_')[2])
    try:
        # Delete the admin
        delete_admin(admin_id)
        bot.answer_callback_query(call.id, text="Admin deleted successfully.")
        bot.send_message(call.message.chat.id, f"Admin with ID {admin_id} has been deleted.")
    except Exception as e:
        bot.answer_callback_query(call.id, text="Failed to delete admin.")
        print(f"Error: {e}")

@bot.message_handler(func=lambda message: message.text == "Show All Admins" and get_user_role(message.chat.id) == 'super_admin')
def show_admins_handler(message):
    admins = get_all_admins()
    admin_list = "\n".join([f"{admin['admin_id']}: {admin['full_name']}" for admin in admins])
    bot.send_message(message.chat.id, f"Current Admins:\n{admin_list}")



@bot.message_handler(func=lambda message: message.text == "See Subscribers" and get_user_role(message.chat.id) == 'super_admin')
def see_users(message):
    users = subscribers.find({})
    user_list = "\n".join([f"{user['subscriber_id']}: {user.get('username', 'No username')}" for user in users])
    bot.send_message(message.chat.id, f"Current Subscribers:\n{user_list}")


@bot.message_handler(func=lambda message: message.text == "Upload Leads" and get_user_role(message.chat.id) in ['admin', 'super_admin'])
def upload_leads(message):
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    bell_button = KeyboardButton("Bell")
    telus_button = KeyboardButton("Telus")
    rogers_button = KeyboardButton("Rogers")
    markup.add(bell_button, telus_button, rogers_button)
    
    back_button = KeyboardButton("Back")
    markup.add(back_button)
    
    bot.send_message(message.chat.id, "Please select a carrier to upload leads:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in ['Bell', 'Telus', 'Rogers'])
def handle_carrier_selection(message):
    carrier = message.text.lower()
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    
    if carrier == "bell":
        markup.add(KeyboardButton("Bell BC"), KeyboardButton("Bell Ontario"), KeyboardButton("Bell Alberta"))
    elif carrier == "telus":
        markup.add(KeyboardButton("Telus BC"), KeyboardButton("Telus Ontario"), KeyboardButton("Telus Alberta"))
    elif carrier == "rogers":
        markup.add(KeyboardButton("Rogers BC"), KeyboardButton("Rogers Ontario"), KeyboardButton("Rogers Alberta"))
    
    back_button = KeyboardButton("Back")
    markup.add(back_button)
    
    bot.send_message(message.chat.id, f"Please select a location for {message.text}:", reply_markup=markup)

user_selected_carriers = {}
@bot.message_handler(func=lambda message: message.text in ['Bell BC', 'Bell Ontario', 'Bell Alberta', 
                                                           'Telus BC', 'Telus Ontario', 'Telus Alberta',
                                                           'Rogers BC', 'Rogers Ontario', 'Rogers Alberta'])
def handle_location_selection(message):
    location = message.text.lower().replace(' ', '_')
    
    user_selected_carriers[message.chat.id] = location
    
    if message.chat.id == int(SUPER_ADMIN_ID):
        bot.send_message(message.chat.id, f"Upload file for {message.text}:")
    else:
        user = subscribers.find_one({'subscriber_id': message.chat.id})
        if user and user.get('role') in ['admin', 'super_admin']:
            bot.send_message(message.chat.id, f"Upload file for {message.text}:")
        else:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("10k - $20 USD", callback_data=f"{location}_10k"),
                       InlineKeyboardButton("20k - $35 USD", callback_data=f"{location}_20k"),
                       InlineKeyboardButton("Custom Order (50k+)", callback_data=f"{location}_custom"))
            bot.send_message(message.chat.id, f"Select the quantity for {message.text}:", reply_markup=markup)

            

@bot.callback_query_handler(func=lambda call: call.data.endswith('10k') or call.data.endswith('20k'))
def handle_quantity_selection(call):
    if call.data.endswith('10k'):
        amount = 20
        lead_quantity = 10000
    elif call.data.endswith('20k'):
        amount = 35
        lead_quantity = 20000

    location = call.data.split('_')[0]  # Extract location from the callback data
    description = f"Purchase {call.data.replace('_', ' ')}"

    # Payment creation
    payment_id, pay_address, pay_amount, payment_status = create_payment(price_amount=amount, price_currency="usd", order_description=description)

    user = subscribers.find_one({'subscriber_id': call.message.chat.id})
    if user:
        username = user.get('username', 'unknown')
        full_name = user.get('full_name', 'unknown')

        if pay_address:
            save_payment(
                user_id=call.message.chat.id,
                username=username,
                full_name=full_name,
                amount=amount,
                status=payment_status,
                payment_id=payment_id,
                order_description=description,
                price_currency="usd",
                pay_currency="usd"
            )

            bot.send_message(
                call.message.chat.id, 
                f"Your Payment ID is: {payment_id}\nPlease send {pay_amount} BTC to the following address:\n\n`{pay_address}`",
                parse_mode='Markdown'
            )

            # Start a new thread to monitor payment status
            thread = threading.Thread(target=check_payment_status, args=(payment_id, call.message.chat.id, location, lead_quantity))
            thread.start()
        else:
            bot.send_message(call.message.chat.id, "Failed to create payment. Please try again later.")
    else:
        bot.send_message(call.message.chat.id, "User not found.")
        
@bot.callback_query_handler(func=lambda call: 'custom' in call.data)
def handle_custom_order(call):
    bot.send_message(call.message.chat.id, "For orders of 50k+, please contact us directly for a custom order.")


@bot.callback_query_handler(func=lambda call: 'custom' in call.data)
def handle_custom_order(call):
    bot.send_message(call.message.chat.id, "For orders of 50k+, please contact us directly for a custom order.")

@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    user_role = get_user_role(message.chat.id)
    
    if user_role in ['admin', 'super_admin']:
        document = message.document
        file_name = document.file_name
        
        if file_name.endswith('.txt'):
            file_info = bot.get_file(document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            file_content = downloaded_file.decode('utf-8')
            
            process_and_store_numbers(file_content, message.chat.id)
            
            bot.send_message(message.chat.id, "Phone numbers uploaded successfully!")
        else:
            bot.send_message(message.chat.id, "Please upload a valid .txt file.")
    else:
        bot.send_message(message.chat.id, "You do not have permission to upload leads.")

def process_and_store_numbers(file_content, user_id):
    carrier = user_selected_carriers.get(user_id)
    
    if not carrier:
        bot.send_message(user_id, "Carrier selection not found. Please select a carrier first.")
        return

    phone_numbers = file_content.splitlines()

    valid_numbers = []
    for number in phone_numbers:
        clean_number = number.strip()
        if re.match(r"^\+?\d{10,15}$", clean_number):
            valid_numbers.append(clean_number)

    if valid_numbers:
        bulk_insert_data = [
            {   
                'uploaded_at': datetime.now(timezone.utc), 
                'uploaded_by': user_id,
                'phone_number': number,
                'carrier': carrier,  # Keep carrier in normalized form
                'sold': False
            }
            for number in valid_numbers
        ]
        
        if bulk_insert_data:
            db[carrier].insert_many(bulk_insert_data)
            bot.send_message(user_id, f"{len(valid_numbers)} valid phone numbers uploaded successfully to {carrier.replace('_', ' ').title()}.")
        else:
            bot.send_message(user_id, "No valid phone numbers found in the file.")
    else:
        bot.send_message(user_id, "No valid phone numbers found in the file.")



def create_payment(price_amount, price_currency, order_description):
    url = 'https://api.nowpayments.io/v1/payment'
    headers = {
        'x-api-key': NOWPAYMENTS_API_KEY,
        'Content-Type': 'application/json'
    }

    data = {
        "price_amount": price_amount,
        "price_currency": price_currency,
        "pay_currency": "btc",
        "order_description": order_description,
        "order_id": order_id
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 201:
        try:
            response_data = response.json()
            payment_id = response_data.get('payment_id')
            pay_address = response_data.get('pay_address')
            pay_amount = response_data.get('pay_amount')
            payment_status = response_data.get('payment_status')

            print(response_data)
            if payment_id and pay_address and pay_amount and payment_status:
                return payment_id, pay_address, pay_amount, payment_status
            else:
                return None, None, None, None
        except (KeyError, json.JSONDecodeError) as e:
            return None, None, None, None
    else:
        return None, None, None, None

    

def check_payment_status(payment_id, subscriber_id, carrier, lead_quantity):
    headers = {
        'x-api-key': NOWPAYMENTS_API_KEY
    }

    while True:
        url = f"https://api.nowpayments.io/v1/payment/{payment_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            payment_info = response.json()
            payment_status = payment_info.get('payment_status')

            print(f"Payment ID: {payment_id} - Status: {payment_status}")

            if payment_status == "finished":
                # Fetch the leads from the database
                send_leads_to_subscriber(subscriber_id, carrier, lead_quantity)
                break

        else:
            print(f"Failed to get payment status for Payment ID: {payment_id}. Error: {response.text}")
            break


def send_leads_to_subscriber(subscriber_id, carrier, lead_quantity):
    # Retrieve the correct carrier collection based on the input
    collection = carrier_collections.get(carrier)
    
    if collection:
        # Create a text file to store leads
        file_name = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(file_name, 'w') as f:
            # Fetch the requested number of unsold leads
            leads_cursor = collection.find({'sold': False}).limit(lead_quantity)  # Only fetch unsold leads
            leads = [lead['phone_number'] for lead in leads_cursor]
            
            if leads:
                for lead in leads:
                    f.write(f"{lead}\n")  # Write each lead to the file
                
                # Send the file to the subscriber
                with open(file_name, 'rb') as file:
                    bot.send_document(subscriber_id, file, caption=f"Here are your {lead_quantity} leads for {carrier.replace('_', ' ').title()}.")                
                # Mark leads as sold
                collection.update_many({'phone_number': {'$in': leads}}, {'$set': {'sold': True}})
                
                # Optionally, remove the file after sending it
                os.remove(file_name)
            else:
                bot.send_message(subscriber_id, "No leads found for your request.")
    else:
        bot.send_message(subscriber_id, "Invalid carrier specified.")


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
        "joined_at": datetime.now(timezone.utc),
        "subscriber_id": subscriber_id,
        "username": username,
        "full_name": full_name
        
    })
    

def save_payment(user_id, username, full_name, amount, status, payment_id, order_description, price_currency, pay_currency):
    payments.insert_one({
        "created_at": datetime.now(timezone.utc),
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



if __name__=='__main__':
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout = 5)
        except Exception as e:
            print(e)
            time.sleep(5)
            continue