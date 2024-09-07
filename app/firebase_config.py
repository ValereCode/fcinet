import firebase_admin
from firebase_admin import credentials, firestore
from .config import settings
import json

cred = credentials.Certificate(json.loads(settings.google_application_credentials))
#cred = credentials.Certificate(settings.google_application_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()