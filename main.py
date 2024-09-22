import telebot
import os
import re
import time
import schedule
from dotenv import load_dotenv
from models import subscribers
from api_payment import create_invoice
from datetime import datetime, timezone
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from models import (SUPER_ADMIN_ID, db, admins, 
                    add_admin, add_subscribers, 
                    get_all_admins, 
                    delete_admin, save_payment, continuously_check_payment_status)


load_dotenv()
API_TOKEN = os.getenv('TELEGRAM_BOT_API_TOKEN')
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
        # Update their role if necessary
        if user_role == 'subscriber':
            user_role = get_user_role(message.chat.id)  # Re-check role

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
    # Check if the message is a command or button action like "Back", "Delete Admin", or "Show All Admins"
    if message.text in ["Back", "Delete Admin", "Show All Admins"]:
        bot.send_message(message.chat.id, "Operation canceled.")
        if message.text == "Back":
            send_welcome(message)
        elif message.text == "Delete Admin":
            delete_admin_handler(message)
        elif message.text == "Show All Admins":
            show_admins_handler(message)
        return
    
    # Ensure the input is a valid integer
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

        # Check if the admin already exists
        if admins.find_one({"admin_id": chat_id}):
            bot.send_message(message.chat.id, f"{full_name} with chat ID {chat_id} is already an admin.")
            return
        
        # Add the new admin since they do not exist
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
    # Fetch all admins and create an inline keyboard
    admins = get_all_admins()
    markup = InlineKeyboardMarkup()

    for admin in admins:
        admin_id = admin['admin_id']
        full_name = admin['full_name']
        # Add a button for each admin to delete
        markup.add(InlineKeyboardButton(full_name, callback_data=f"delete_admin_{admin_id}"))

    if not admins:
        bot.send_message(message.chat.id, "No admins to delete.")
    else:
        bot.send_message(message.chat.id, "Select an admin to delete:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_admin_'))
def handle_delete_admin_callback(call):
    admin_id = int(call.data.split('_')[2])  # Extract admin ID from the callback data
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
    
    # Store the selected carrier for the user
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
    elif call.data.endswith('20k'):
        amount = 35

    description = f"Purchase {call.data.replace('_', ' ')}"
    payment_id, invoice_url = create_invoice(price_amount=amount, price_currency="usd", order_description=description)

    # Get user details
    user = subscribers.find_one({'subscriber_id': call.message.chat.id})
    if user:
        username = user.get('username', 'unknown')
        full_name = user.get('full_name', 'unknown')
        
        if invoice_url:
            save_payment(
                user_id=call.message.chat.id,
                username=username,
                full_name=full_name,
                amount=amount,
                status="waiting",  
                payment_id=payment_id,  # Use the payment ID from the API
                order_description=description,
                price_currency="usd",
                pay_currency="usd"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Complete Payment", url=invoice_url))
            bot.send_message(call.message.chat.id, "Click the button below to complete your payment:", reply_markup=markup)
            continuously_check_payment_status(payment_id)  # Pass the payment ID to the function
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

# Process and store phone numbers in the database
def process_and_store_numbers(file_content, user_id):
    # Get the carrier location selected by the user
    carrier = user_selected_carriers.get(user_id)
    
    if not carrier:
        bot.send_message(user_id, "Carrier selection not found. Please select a carrier first.")
        return

    # Split content by new lines
    phone_numbers = file_content.splitlines()

    valid_numbers = []
    for number in phone_numbers:
        clean_number = number.strip()
        if re.match(r"^\+?\d{10,15}$", clean_number):
            valid_numbers.append(clean_number)

    if valid_numbers:
        bulk_insert_data = [
            {
                'phone_number': number,
                'uploaded_by': user_id,
                'uploaded_at': datetime.now(timezone.utc), 
                'carrier': carrier.replace('_', ' ').title()
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


if __name__=='__main__':
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout = 5)
        except Exception as e:
            print(e)
            time.sleep(5)
            continue