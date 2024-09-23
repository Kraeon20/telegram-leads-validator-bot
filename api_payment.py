import os
import json
import requests
from dotenv import load_dotenv
import time

load_dotenv()
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')

# Function to create an invoice using NowPayments
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
        "order_id": "order-123456"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 201:
        try:
            response_data = response.json()
            payment_id = response_data.get('payment_id')
            pay_address = response_data.get('pay_address')
            pay_amount = response_data.get('pay_amount')


            print(response_data)
            if payment_id and pay_address and pay_amount:
                return payment_id, pay_address, pay_amount
            else:
                return None, None, None
        except (KeyError, json.JSONDecodeError) as e:
            return None, None, None
    else:
        return None, None, None
    


def check_payment_status(payment_id):
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

            if payment_status == "confirmed":
                # You can send a message to the user here
                print("Payment confirmed")
                break
            
            # Add a delay before the next check
            time.sleep(2)  # Check every 2 seconds
        else:
            print(f"Failed to get payment status for Payment ID: {payment_id}. Error: {response.text}")
            break