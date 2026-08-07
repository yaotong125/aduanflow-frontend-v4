from cryptography.fernet import Fernet
import base64
import hashlib
from backend.app.config import settings

class EncryptionService:
    def __init__(self):
        # Generate a valid 32-byte Fernet key from settings or default secret
        raw_key = settings.ENCRYPTION_KEY.encode()
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())
        self.cipher = Fernet(derived_key)

    def encrypt(self, plain_text: str) -> str:
        """Encrypt sensitive text at rest."""
        if not plain_text:
            return ""
        return self.cipher.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        """Decrypt sensitive text for authorized view."""
        if not cipher_text:
            return ""
        try:
            return self.cipher.decrypt(cipher_text.encode()).decode()
        except Exception:
            return "[Decryption Error]"

    def mask_account(self, account_no: str) -> str:
        """Mask account number showing only last 4 digits."""
        if not account_no or len(account_no) < 4:
            return "Not found"
        return f"****{account_no[-4:]}"

encryption_service = EncryptionService()
