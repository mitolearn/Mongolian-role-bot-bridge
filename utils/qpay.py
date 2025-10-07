import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

QPAY_USERNAME = os.getenv("QPAY_USERNAME")
QPAY_PASSWORD = os.getenv("QPAY_PASSWORD")
QPAY_INVOICE_CODE = os.getenv("QPAY_INVOICE_CODE")

def validate_qpay_credentials():
    """Validate that all QPay credentials are set"""
    if not QPAY_USERNAME or not QPAY_PASSWORD or not QPAY_INVOICE_CODE:
        raise RuntimeError(
            "Missing QPay credentials. Please set QPAY_USERNAME, QPAY_PASSWORD, and QPAY_INVOICE_CODE in Secrets."
        )

def get_qpay_token():
    if not QPAY_USERNAME or not QPAY_PASSWORD:
        print("QPay credentials not set")
        return None
        
    try:
        response = requests.post(
            "https://merchant.qpay.mn/v2/auth/token",
            auth=HTTPBasicAuth(QPAY_USERNAME, QPAY_PASSWORD),
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        print("QPay auth failed:", response.text)
        return None
    except Exception as e:
        print("QPay auth error:", e)
        return None

def create_qpay_invoice(amount_mnt: int, plan_name: str):
    token = get_qpay_token()
    if not token:
        return None, None, None

    try:
        response = requests.post(
            "https://merchant.qpay.mn/v2/invoice",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "invoice_code": QPAY_INVOICE_CODE,
                "sender_invoice_no": f"DISC_{int(datetime.now().timestamp())}",
                "invoice_receiver_code": plan_name,
                "invoice_description": f"Discord Role: {plan_name}",
                "amount": amount_mnt,
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("invoice_id"), data.get("qr_text", ""), data.get("qPay_shortUrl")
        print("QPay invoice failed:", response.text)
        return None, None, None
    except Exception as e:
        print("QPay invoice error:", e)
        return None, None, None

def check_qpay_payment_status(invoice_id: str):
    token = get_qpay_token()
    if not token:
        print(f"❌ QPay token failed for invoice {invoice_id}")
        return "unknown"

    try:
        payload = {"object_type": "INVOICE", "object_id": invoice_id}
        print(f"🔍 Checking QPay status for {invoice_id} with payload: {payload}")
        
        response = requests.post(
            "https://merchant.qpay.mn/v2/payment/check",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10
        )
        
        print(f"QPay Response Status: {response.status_code}")
        print(f"QPay Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if there are payment records in rows
            rows = data.get("rows", [])
            if rows and len(rows) > 0:
                # Get the payment status from the first row
                status = rows[0].get("payment_status", "unknown")
                print(f"✅ Payment status for {invoice_id}: {status}")
                return status
            else:
                print(f"⏳ Invoice {invoice_id} not paid yet - returning PENDING status")
                return "PENDING"
        else:
            print(f"❌ QPay API Error {response.status_code}: {response.text}")
            return "unknown"
    except Exception as e:
        print(f"❌ QPay status error for {invoice_id}: {e}")
        return "unknown"