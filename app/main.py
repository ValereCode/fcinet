from datetime import datetime, timedelta
import hmac
import hashlib
from fastapi import FastAPI, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
from .config import settings
from .schemas import UserPayload, VerifyTransaction
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


@app.post("/payment-notification/")
async def notify_payment(request: Request, x_token: str = Header(None)):
        
    try:
        # Extraire le corps de la requête
        payload = await request.form()  # Si les données sont envoyées en tant que formulaire
        
        print("Payload reçu : ", payload)


        # Récupérer les informations importantes
        transaction_id = payload.get("cpm_trans_id")
        site_id = payload.get("cpm_site_id")
        custom_data = payload.get("cpm_custom")  # Correspond à la metadata envoyée à l'initialisation
        
        if not transaction_id or not site_id:
            raise HTTPException(status_code=400, detail="Transaction ID or Site ID missing")

        # Vérifier la signature HMAC pour valider l'intégrité des données
        secret_key = settings.cinetpay_secret_key  # Votre clé secrète pour générer le HMAC
        # Générer le HMAC token à partir des données de la requête
        generated_token = generate_hmac_token(payload, secret_key)

        # Comparer le token généré avec celui reçu dans l'en-tête
        if not hmac.compare_digest(generated_token, x_token):
            raise HTTPException(status_code=400, detail="Invalid HMAC token")
        
        # Vérifier si la transaction est déjà marquée comme succès dans votre base de données
        user_ref = db.collection('users').document(custom_data)
        
        print("User Ref: ", user_ref)
        
        match user_ref:
            case "Pupil":
                userProfileData = db.collection('pupils').document(custom_data)
            case "Candidate":
                userProfileData = db.collection('candidates').document(custom_data)
        
        # Appeler l'API de vérification de CinetPay pour confirmer le statut du paiement
        verification_url = "https://api-checkout.cinetpay.com/v2/payment/check"
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
            userProfileData.update({
                "paymentDate": datetime.utcnow().timestamp(),
                "isPremium": True,
                "premiumEnd": (datetime.utcnow() + timedelta(days=30)).timestamp(),
                "premiumType": 'month',
            })
            return {"status": "user_updated_to_premium"}
        else:
            return {"status": "payment_not_accepted"}
    
    except Exception as e:
        print(f"Erreur lors de la notification de paiement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 

@app.post("/verify-payment/")
async def verify_payment(trans_id: VerifyTransaction):
    payload ={
        "apikey": settings.cinetpay_api_key,
        "site_id": settings.cinetpay_site_id,
        "transaction_id": trans_id.trans_id,
    }
    verification_url = "https://api-checkout.cinetpay.com/v2/payment/check"
    
    try:
        verification_response = requests.post(verification_url, json=payload)
        return verification_response.json()
    
        # response = requests.post(f"{settings.cinetpay_base_url}", json=payload)
        # return response.json()
    
    except requests.RequestException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Fonction pour générer le token HMAC comme spécifié par CinetPay
def generate_hmac_token(payload, secret_key):
    # Concaténer les données dans l'ordre spécifié
    data = (
        payload.get("cpm_site_id", "") +
        payload.get("cpm_trans_id", "") +
        payload.get("cpm_trans_date", "") +
        payload.get("cpm_amount", "") +
        payload.get("cpm_currency", "") +
        payload.get("signature", "") +
        payload.get("payment_method", "") +
        payload.get("cel_phone_num", "") +
        payload.get("cpm_phone_prefixe", "") +
        payload.get("cpm_language", "") +
        payload.get("cpm_version", "") +
        payload.get("cpm_payment_config", "") +
        payload.get("cpm_page_action", "") +
        payload.get("cpm_custom", "") +
        payload.get("cpm_designation", "") +
        payload.get("cpm_error_message", "")
    )

    # Générer le HMAC avec SHA-256
    token = hmac.new(secret_key.encode(), data.encode(), hashlib.sha256).hexdigest()

    return token