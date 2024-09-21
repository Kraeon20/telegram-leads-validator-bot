import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import os
from dotenv import load_dotenv
from api_payment import create_invoice

load_dotenv()
API_TOKEN = os.getenv('TELEGRAM_BOT_API_TOKEN')
SUPER_ADMIN_ID = [int(x) for x in os.getenv('ADMIN_CHAT_ID').split(',')]
ADMIN_CHAT_ID = [int(x) for x in os.getenv('ADMIN_CHAT_ID').split(',')]

bot = telebot.TeleBot(API_TOKEN)

def is_super_admin(user_id):
    return str(user_id) == SUPER_ADMIN_ID

def is_admin(user_id):
    return str(user_id) == ADMIN_CHAT_ID


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id == SUPER_ADMIN_ID:
        markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        open_shop_button = KeyboardButton("OPEN SHOP")
        open_admins_corner_button = KeyboardButton("OPEN ADMINS CORNER")
        markup.add(open_shop_button, open_admins_corner_button)
        bot.send_message(message.chat.id, "Welcome, Super Admin!", reply_markup=markup)
    elif message.from_user.id in ADMIN_CHAT_ID:
        markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        open_shop_button = KeyboardButton("OPEN SHOP")
        open_admins_corner_button = KeyboardButton("OPEN ADMINS CORNER")
        markup.add(open_shop_button, open_admins_corner_button)
        bot.send_message(message.chat.id, "Welcome, Admin!", reply_markup=markup)
    else:
        markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        bell_button = KeyboardButton("Bell")
        telsus_button = KeyboardButton("Telsus")
        rogers_button = KeyboardButton("Rogers")
        markup.add(bell_button, telsus_button, rogers_button)
        bot.send_message(message.chat.id, "Welcome! Please select a carrier:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "OPEN SHOP")
def open_shop(message):
    # Open the shop (same as users see it)
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    bell_button = KeyboardButton("Bell")
    telsus_button = KeyboardButton("Telsus")
    rogers_button = KeyboardButton("Rogers")
    markup.add(bell_button, telsus_button, rogers_button)
    bot.send_message(message.chat.id, "Welcome to the shop!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "OPEN ADMINS CORNER")
def open_admins_corner(message):
    if message.from_user.id == SUPER_ADMIN_ID:
        markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        see_users_button = KeyboardButton("See Users")
        add_admin_button = KeyboardButton("Add New Admin")
        upload_leads_button = KeyboardButton("Upload Leads")
        markup.add(see_users_button, add_admin_button, upload_leads_button)
        bot.send_message(message.chat.id, "Welcome to the Admins Corner!", reply_markup=markup)
    elif message.from_user.id in SUPER_ADMIN_ID:
        markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        upload_leads_button = KeyboardButton("Upload Leads")
        markup.add(upload_leads_button)
        bot.send_message(message.chat.id, "Welcome to the Admins Corner!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "See Users")
def see_users(message):
    # Implement logic to show all bot users (only for Super Admin)
    pass

@bot.message_handler(func=lambda message: message.text == "Add New Admin")
def add_admin(message):
    # Implement logic to add new admin (only for Super Admin)
    pass

@bot.message_handler(func=lambda message: message.text == "Upload Leads")
def upload_leads(message):
    # Implement logic to upload new leads
    pass


@bot.message_handler(func=lambda message: message.text in ['Bell', 'Telsus', 'Rogers'])
def handle_carrier_selection(message):
    carrier = message.text.lower()
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    
    if carrier == "bell":
        markup.add(KeyboardButton("Bell BC"), KeyboardButton("Bell Ontario"), KeyboardButton("Bell Alberta"))
    elif carrier == "telsus":
        markup.add(KeyboardButton("Telsus BC"), KeyboardButton("Telsus Ontario"), KeyboardButton("Telsus Alberta"))
    elif carrier == "rogers":
        markup.add(KeyboardButton("Rogers BC"), KeyboardButton("Rogers Ontario"), KeyboardButton("Rogers Alberta"))
    
    bot.send_message(message.chat.id, f"Please select a location for {message.text}:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['Bell BC', 'Bell Ontario', 'Bell Alberta', 
                                                           'Telsus BC', 'Telsus Ontario', 'Telsus Alberta',
                                                           'Rogers BC', 'Rogers Ontario', 'Rogers Alberta'])
def handle_location_selection(message):
    location = message.text.lower().replace(' ', '_')
    markup = InlineKeyboardMarkup()
    
    markup.add(InlineKeyboardButton("10k - $20 USD", callback_data=f"{location}_10k"),
               InlineKeyboardButton("20k - $35 USD", callback_data=f"{location}_20k"),
               InlineKeyboardButton("Custom Order (50k+)", callback_data=f"{location}_custom"))
    
    bot.send_message(message.chat.id, f"Select the quantity for {message.text}:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.endswith('10k') or call.data.endswith('20k'))
def handle_quantity_selection(call):
    if call.data.endswith('10k'):
        amount = 20  # 10k leads cost $20
    elif call.data.endswith('20k'):
        amount = 35  # 20k leads cost $35
    
    description = f"Purchase {call.data.replace('_', ' ')}"
    invoice_url = create_invoice(price_amount=amount, price_currency="usd", order_description=description)
    
    if invoice_url:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Complete Payment", url=invoice_url))
        bot.send_message(call.message.chat.id, "Click the button below to complete your payment:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "Failed to create payment. Please try again later.")

@bot.callback_query_handler(func=lambda call: 'custom' in call.data)
def handle_custom_order(call):
    bot.send_message(call.message.chat.id, "For orders of 50k+, please contact us directly for a custom order.")

bot.polling()