import os
import json
import requests
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
    data = {
        "price_amount": price_amount,
        "price_currency": price_currency,
        "pay_currency": "btc",
        "ipn_callback_url": "https://nowpayments.io",
        "order_id": "RGDBP-21314",
        "order_description": order_description
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json().get('invoice_url')
    else:
        return None