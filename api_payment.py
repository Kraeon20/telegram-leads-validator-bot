import os
import json
import requests
from dotenv import load_dotenv
import time
from payment_utils import mark_leads_as_sold, get_payment_by_id, update_payment_status
import os
from uuid import UUID

load_dotenv()
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
order_id = order_id = f"order-{int(time.time())}"


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
    
def create_payment_response_data(payment_id):
    headers = {
        'x-api-key': NOWPAYMENTS_API_KEY
    }
    url = f"https://api.nowpayments.io/v1/payment/{payment_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {}
    

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
                # Payment confirmed, retrieve order and lead details
                payment = get_payment_by_id(payment_id)
                if payment:
                    order_description = payment['order_description']
                    location, quantity = order_description.split()[1:3]  # e.g., "bell_bc 10k"
                    quantity = int(quantity.replace("k", "000"))  # Convert to number of leads

                    # Reserve the leads
                    leads = mark_leads_as_sold(location, quantity)
                    
                    # Create a text file with the reserved leads
                    leads_file_path = f"{payment['username']}_leads_{location}_{quantity}.txt"
                    with open(leads_file_path, "w") as file:
                        for lead in leads:
                            file.write(f"{lead['phone_number']}\n")  # Assuming `phone_number` is in the collection
                    
                    # Notify the user with the leads file (this is handled in `main.py` below)
                    print(f"Leads reserved and saved in {leads_file_path}")
                
                # Update payment status to 'confirmed'
                update_payment_status(payment_id, "confirmed")
                break

            time.sleep(2)  # Check every 2 seconds
        else:
            print(f"Failed to get payment status for Payment ID: {payment_id}. Error: {response.text}")
            break