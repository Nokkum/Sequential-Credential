import os
import base64
import getpass
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class EncryptionManager:
    """Manages master-key derived from MASTER_PASSWORD and performs encryption/decryption.

    Accepts an explicit master_password (str) or will check the MASTER_PASSWORD env var
    or prompt on the console as a final fallback.
    """

    BASE = '.sequential'
    SALT_FILE = os.path.join(BASE, 'master_salt')

    def __init__(self, master_password: Optional[str] = None):
        os.makedirs(self.BASE, exist_ok=True)
        self.key = self._derive_key(master_password)

    def _derive_key(self, master_password: Optional[str]) -> bytes:
        pwd = master_password or os.environ.get('MASTER_PASSWORD')
        if pwd is None:
            try:
                pwd = getpass.getpass('Enter master password: ')
            except Exception:
                pwd = 'default_master_password'
        pwdb = pwd.encode('utf-8')

        if os.path.exists(self.SALT_FILE):
            salt = open(self.SALT_FILE, 'rb').read()
        else:
            salt = os.urandom(32)
            with open(self.SALT_FILE, 'wb') as f:
                f.write(salt)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=300000,
        )
        return base64.urlsafe_b64encode(kdf.derive(pwdb))

    def encrypt(self, plaintext: str) -> bytes:
        return Fernet(self.key).encrypt(plaintext.encode('utf-8'))

    def decrypt(self, ciphertext: bytes) -> str:
        return Fernet(self.key).decrypt(ciphertext).decode('utf-8')