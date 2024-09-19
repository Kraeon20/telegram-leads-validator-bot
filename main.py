import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
from dotenv import load_dotenv
import os
from api_payment import create_invoice

load_dotenv()
API_TOKEN = os.getenv('TELEGRAM_BOT_API_TOKEN')


bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    # Adding buttons for the three carriers
    markup.add(InlineKeyboardButton("Bell", callback_data='bell'))
    markup.add(InlineKeyboardButton("Telsus", callback_data='telsus'))
    markup.add(InlineKeyboardButton("Rogers", callback_data='rogers'))
    
    bot.send_message(message.chat.id, "Welcome! Please select a carrier:", reply_markup=markup)

# Function to show available quantities for Bell
def show_bell_options(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Bell BC - 10k - $20 USD", callback_data='bell_bc_10k'))
    markup.add(InlineKeyboardButton("Bell BC - 20k - $35 USD", callback_data='bell_bc_20k'))
    markup.add(InlineKeyboardButton("Bell Ontario - 10k - $20 USD", callback_data='bell_ontario_10k'))
    markup.add(InlineKeyboardButton("Bell Ontario - 20k - $35 USD", callback_data='bell_ontario_20k'))
    markup.add(InlineKeyboardButton("Bell Alberta - 10k - $20 USD", callback_data='bell_alberta_10k'))
    markup.add(InlineKeyboardButton("Bell Alberta - 20k - $35 USD", callback_data='bell_alberta_20k'))
    markup.add(InlineKeyboardButton("Custom Order (50k+)", callback_data='bell_custom'))
    
    bot.edit_message_text("Select the quantity and region for Bell Leads:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

# Function to show available quantities for Telsus
def show_telsus_options(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Telsus BC - 10k - $20 USD", callback_data='telsus_bc_10k'))
    markup.add(InlineKeyboardButton("Telsus BC - 20k - $35 USD", callback_data='telsus_bc_20k'))
    markup.add(InlineKeyboardButton("Telsus Ontario - 10k - $20 USD", callback_data='telsus_ontario_10k'))
    markup.add(InlineKeyboardButton("Telsus Ontario - 20k - $35 USD", callback_data='telsus_ontario_20k'))
    markup.add(InlineKeyboardButton("Telsus Alberta - 10k - $20 USD", callback_data='telsus_alberta_10k'))
    markup.add(InlineKeyboardButton("Telsus Alberta - 20k - $35 USD", callback_data='telsus_alberta_20k'))
    markup.add(InlineKeyboardButton("Custom Order (50k+)", callback_data='telsus_custom'))
    
    bot.edit_message_text("Select the quantity and region for Telsus Leads:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

# Function to show available quantities for Rogers
def show_rogers_options(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Rogers BC - 10k - $20 USD", callback_data='rogers_bc_10k'))
    markup.add(InlineKeyboardButton("Rogers BC - 20k - $35 USD", callback_data='rogers_bc_20k'))
    markup.add(InlineKeyboardButton("Rogers Ontario - 10k - $20 USD", callback_data='rogers_ontario_10k'))
    markup.add(InlineKeyboardButton("Rogers Ontario - 20k - $35 USD", callback_data='rogers_ontario_20k'))
    markup.add(InlineKeyboardButton("Rogers Alberta - 10k - $20 USD", callback_data='rogers_alberta_10k'))
    markup.add(InlineKeyboardButton("Rogers Alberta - 20k - $35 USD", callback_data='rogers_alberta_20k'))
    markup.add(InlineKeyboardButton("Custom Order (50k+)", callback_data='rogers_custom'))
    
    bot.edit_message_text("Select the quantity and region for Rogers Leads:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'bell':
        show_bell_options(call)
    elif call.data == 'telsus':
        show_telsus_options(call)
    elif call.data == 'rogers':
        show_rogers_options(call)
    elif call.data.endswith('10k'):
        amount = 20  # 10k leads cost $20
    elif call.data.endswith('20k'):
        amount = 35  # 20k leads cost $35
    
        # Create invoice based on the user’s selection
        description = f"Purchase {call.data.replace('_', ' ')}"
        invoice_url = create_invoice(price_amount=amount, price_currency="usd", order_description=description)
        
        if invoice_url:
            # Create a button for the payment link
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Complete Payment", url=invoice_url))
            bot.send_message(call.message.chat.id, "Click the button below to complete your payment:", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "Failed to create payment. Please try again later.")
    elif 'custom' in call.data:
        bot.send_message(call.message.chat.id, "For orders of 50k+, please contact us directly for a custom order.")

bot.polling()