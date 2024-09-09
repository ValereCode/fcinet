from datetime import datetime, timedelta
import hmac
import hashlib
from fastapi import FastAPI, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
from .config import settings
from .schemas import UserPayload, CheckPay, PaymentNotification
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
    print('Hi World!')
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
        'metadata': user_pay.metadata
    }
    
    try:
        response = requests.post(f"{settings.cinetpay_base_url}", json=payload)
        return response.json()
    
    except requests.RequestException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/verify-payment/")
async def verify_payment(check_id: CheckPay):
    # Vous pouvez ajouter ici la logique pour traiter les notifications de paiement CinetPay
    check = {
        "apikey": settings.cinetpay_api_key,
        "site_id": settings.cinetpay_site_id,
        "transaction_id": check_id.trans_id
    }
    print(check)
    print(check_id)
    try:
        response = requests.post(f"{settings.cinetpay_base_url}/check", json=check)
        response_data = response.json()
        
        if response_data.get("data", {}).get("status") == "ACCEPTED":
            user_id = check_id.user_id
            user_ref = db.collection('candidates').document(user_id)
            
             # Mettre à jour les champs dans Firestore si ils sont nécessaires
            user_ref.update({
                "paymentDate": datetime.utcnow().timestamp(),
                "isPremium": True,
                "premiumEnd": (datetime.utcnow() + timedelta(days=30)).timestamp(),
                "premiumType": 'month'
            })
        
        return response_data
    
    except requests.RequestException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/payment-notification/")
async def notify_payment(request: Request,
    x_token: str = Header(None)  # Le token HMAC est passé dans l'en-tête 'x-token'
    ):
        
    try:
        # Extraire le corps de la requête
        payload = await request.form()  # Si les données sont envoyées en tant que formulaire

        # Afficher les données reçues pour déboguer
        print(payload)
        
        # Récupérer les informations importantes
        transaction_id = payload.get("cpm_trans_id")
        site_id = payload.get("cpm_site_id")
        custom_data = payload.get("cpm_custom")  # Correspond à la metadata envoyée à l'initialisation
        
        if not transaction_id or not site_id:
            raise HTTPException(status_code=400, detail="Transaction ID or Site ID missing")

        # Vérifier la signature HMAC pour valider l'intégrité des données
        secret_key = settings.cinetpay_secret_key  # Votre clé secrète pour générer le HMAC
        if not verify_hmac_signature(payload, x_token, secret_key):
            print('Votre HMAC est invalid')
            # raise HTTPException(status_code=400, detail="Invalid HMAC signature")
        
        
        # Vérifier si la transaction est déjà marquée comme succès dans votre base de données
        user_ref = db.collection('candidates').document(custom_data)
        # user_doc = user_ref.get()

        # if user_doc.exists and user_doc.get("paymentStatus") == "success":
        #     return {"status": "Payment already processed"}
        
        
        # Appeler l'API de vérification de CinetPay pour confirmer le statut du paiement
        verification_url = "https://api-checkout.cinetpay.com/v2/payment/check"
        # headers = {
        #     'Content-Type': 'application/json',
        #     'apikey': 'your_cinetpay_api_key'
        # }
        data = {
            "apikey": settings.cinetpay_api_key,
            "transaction_id": transaction_id,
            "site_id": site_id
        }

        verification_response = requests.post(verification_url, json=data)
        verification_data = verification_response.json()
        
        # Vérifier le statut de la transaction retournée par CinetPay
        if verification_data.get("code") == "00" and verification_data.get("data").get("status") == "ACCEPTED":
            # Mettre à jour le statut de l'utilisateur dans Firestore
            user_ref.update({
                "paymentDate": datetime.utcnow().timestamp(),
                "isPremium": True,
                "premiumEnd": (datetime.utcnow() + timedelta(days=30)).timestamp(),
                "premiumType": 'month',
                # "paymentStatus": "success"
            })
            return {"status": "user_updated_to_premium"}
        else:
            return {"status": "payment_not_accepted"}
        
        
        # Vérifier si le paiement est accepté
        """
        if payload.get('status') == "ACCEPTED":
            
            # Récupérer l'ID utilisateur depuis metadata
            # user_id = notification.metadata
            user_id = payload.get('metadata')
            
            # Mettre à jour l'utilisateur dans Firestore pour devenir Premium
            user_ref = db.collection('candidates').document(user_id)
            
            # Mettre à jour les champs dans Firestore si ils sont nécessaires
            user_ref.update({
                "paymentDate": datetime.utcnow().timestamp(),
                "isPremium": True,
                "premiumEnd": (datetime.utcnow() + timedelta(days=30)).timestamp(),
                "premiumType": 'month'
            })
            print('Everithings works')
            return {"status": "user_updated_to_premium"}
        else:
            print('Work but not at all , courage')
            return {"status": "payment_not_accepted"}
        """
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
        
        
# Utilisez cette fonction pour vérifier le HMAC envoyé par CinetPay
def verify_hmac_signature(data, received_signature, secret_key):
    sorted_data = "&".join(f"{key}={value}" for key, value in sorted(data.items()))
    calculated_signature = hmac.new(secret_key.encode(), sorted_data.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_signature, received_signature)
