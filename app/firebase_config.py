import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("./app/service_account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()