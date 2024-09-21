import os
import json
import requests
import uuid  # Import the uuid module
from dotenv import load_dotenv


load_dotenv()
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')

# Function to create an invoice using NowPayments
def create_invoice(price_amount, price_currency, order_description):
    url = 'https://api.nowpayments.io/v1/invoice'
    headers = {
        'x-api-key': NOWPAYMENTS_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Generate a unique order ID
    order_id = str(uuid.uuid4())

    data = {
        "price_amount": price_amount,
        "price_currency": price_currency,
        "pay_currency": "btc",
        "ipn_callback_url": "https://nowpayments.io",
        "order_id": order_id, 
        "order_description": order_description
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json().get('invoice_url')
    else:
        return None

def get_payment_status(payment_id, api_key):
    url = f"https://api.nowpayments.io/v1/payment/{payment_id}"

    headers = {
        'x-api-key': NOWPAYMENTS_API_KEY
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch payment status. Status code: {response.status_code}")
        return None



