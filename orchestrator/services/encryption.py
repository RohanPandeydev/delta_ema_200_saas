# ============================================
# FILE: orchestrator/services/encryption.py
# ============================================
"""
Encryption service for API credentials
"""
from cryptography.fernet import Fernet
import base64
import os

class EncryptionService:
    """Handle encryption/decryption of sensitive data"""
    
    def __init__(self, key=None):
        if key is None:
            key = os.getenv('ENCRYPTION_KEY')
        
        if not key:
            # Generate a key for development (store this securely in production!)
            key = Fernet.generate_key()
            print(f"⚠️  Generated encryption key: {key.decode()}")
            print("⚠️  Set this as ENCRYPTION_KEY in production!")
        
        if isinstance(key, str):
            key = key.encode()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext):
        """Encrypt plaintext string"""
        if not plaintext:
            return None
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        return self.cipher.encrypt(plaintext).decode()
    
    def decrypt(self, ciphertext):
        """Decrypt ciphertext string"""
        if not ciphertext:
            return None
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode()
        return self.cipher.decrypt(ciphertext).decode()

# Global instance
encryption_service = EncryptionService()