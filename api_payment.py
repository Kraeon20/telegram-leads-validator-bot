import os
import json
import requests
import time
import uuid  # Import the uuid module
from dotenv import load_dotenv

load_dotenv()
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
ORDER_ID = str(uuid.uuid4())

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
        "order_description": order_description
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        response_data = response.json()
        payment_id = response_data.get('id')  # Get the payment ID from the response
        invoice_url = response_data.get('invoice_url')  # Get the invoice URL for payment

        # Return both the payment_id and the invoice URL
        return payment_id, invoice_url
    else:
        print(f"Failed to create invoice: {response.text}")
        return None, None

