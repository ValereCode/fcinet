import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import requests
from .config import settings
from .schemas import UserPayload, CheckPay
from .firebase_config import db

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/initiate-payment/")
async def initiate_payment(user_pay: UserPayload):
    payload = {
        "apikey": settings.cinetpay_api_key,
        "site_id": settings.cinetpay_site_id,
        "transaction_id": user_pay.trans_id,
        "amount": user_pay.amount,
        "currency": "XOF",  # Ajustez selon votre devise
        "description": user_pay.description,
        "return_url": settings.return_url,
        "notify_url": settings.callback_url,
        "customer_name": user_pay.customer_name,
        "customer_email": user_pay.customer_email,
    }
    
    try:
        response = requests.post(f"{settings.cinetpay_base_url}", json=payload)
        response_data = response.json()
        print(response_data)
        # if response.status_code == status.HTTP_200_OK and response_data.get("code") == "00":
        #     return {"payment_url": response_data.get("data", {}).get("payment_url")}
        # else:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response_data.get("message", "Payment initiation failed"))
        return {"payment_url": response_data.get("data", {}).get("payment_url")}
    
    except requests.RequestException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/payment-notification/")
async def payment_notification(check_id: CheckPay):
    # Vous pouvez ajouter ici la logique pour traiter les notifications de paiement CinetPay
    check = {
        "apikey": settings.cinetpay_api_key,
        "site_id": settings.cinetpay_site_id,
        "transaction_id": check_id.trans_id
    }
    print(check)
    try:
        response = requests.post(f"{settings.cinetpay_base_url}/check", json=check)
        response_data = response.json()
        
        if response_data.get("data", {}).get("status") == "ACCEPTED":
            user_id = check_id.user_id
            user_ref = db.collection('candidates').document(user_id)
            
             # Mettre à jour les champs dans Firestore
            user_ref.update({
                "paymentDate": datetime.now().timestamp(),
                "isPremium": True,
                "premiumEnd": (datetime.now() + datetime.timedelta(days=30)).timestamp(),
                "premiumType": 'month'
            })
        
        return response_data
    
    except requests.RequestException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
