import time
import requests
from models import payments  # Import payments here
from api_payment import NOWPAYMENTS_API_KEY
def continuously_check_payment_status(order_id, check_interval=30):
    while True:
        try:
            # Fetch the payment record based on the order_id
            
            if not payments:
                print("No payment found with the given order ID.")
                return
            
            payment_id = payments['order_id']  # Use the order_id for API call
            url = f"https://api.nowpayments.io/v1/payment/{payment_id}"
            headers = {
                'x-api-key': NOWPAYMENTS_API_KEY 
            }

            # Make the API request to get the payment status
            response = requests.get(url, headers=headers)
            response_data = response.json()

            # Check if the API call was successful
            if response.status_code != 200:
                print(f"API call failed: {response_data.get('error', 'Unknown error')}")
                return

            payment_status = response_data.get('payment_status')

            # Update the payment status in the database if it's confirmed
            if payment_status == "confirmed":
                payments.update_one(
                    {"order_id": order_id},
                    {"$set": {"status": "paid"}}
                )
                print(f"Payment status updated to 'paid' for order ID: {order_id}")
                break  # Exit the loop after updating

            else:
                print(f"Current payment status for order ID {order_id} is '{payment_status}'. Checking again in {check_interval} seconds.")

        except Exception as e:
            print(f"An error occurred: {e}")

        # Wait for the specified interval before checking again
        time.sleep(check_interval)



