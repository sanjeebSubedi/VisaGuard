import json
from pathlib import Path

from app.services.crypto import EncryptionService


class ArtifactStorage:
    def __init__(self, root: Path, encryption_key: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._crypto = EncryptionService(encryption_key)

    def write_bytes(self, relative_path: Path, content: bytes) -> None:
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


    def write_json(self, relative_path: Path, payload: dict) -> None:
        self.write_bytes(relative_path, json.dumps(payload).encode("utf-8"))

    def store_original(self, user_id: str, filename: str, content: bytes) -> str:
        relative_path = Path("originals") / user_id / filename
        encrypted = self._crypto.encrypt(content)
        self.write_bytes(relative_path, encrypted)
        return str(relative_path)

    def load_original(self, location: str) -> bytes:
        encrypted = (self.root / location).read_bytes()
        return self._crypto.decrypt(encrypted)
