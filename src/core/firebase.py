import firebase_admin
from firebase_admin import auth, credentials
from src.core.config import get_config

settings = get_config()

cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
firebase_app = firebase_admin.initialize_app(cred)
