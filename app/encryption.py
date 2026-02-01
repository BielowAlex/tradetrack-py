from cryptography.fernet import Fernet
from app.config import settings
import base64


class EncryptionService:
    def __init__(self):
        key = settings.encryption_key_fernet
        if not key:
            raise ValueError("ENCRYPTION_KEY_FERNET is not set")
        
        try:
            key_bytes = base64.urlsafe_b64decode(key)
            self.cipher = Fernet(base64.urlsafe_b64encode(key_bytes))
        except Exception:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return self.cipher.decrypt(ciphertext.encode()).decode()


encryption_service = EncryptionService()
