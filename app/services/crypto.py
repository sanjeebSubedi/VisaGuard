from cryptography.fernet import Fernet


class EncryptionService:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, content: bytes) -> bytes:
        return self._fernet.encrypt(content)

    def decrypt(self, content: bytes) -> bytes:
        return self._fernet.decrypt(content)
