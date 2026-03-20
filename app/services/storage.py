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

    def write_text(self, relative_path: Path, content: str) -> None:
        self.write_bytes(relative_path, content.encode("utf-8"))

    def write_retained_text(self, document_id: int, content: str) -> str:
        relative_path = Path("retained") / f"document-{document_id}.txt"
        self.write_text(relative_path, content)
        return str(relative_path)

    def write_llm_response(self, document_id: int, payload: dict) -> str:
        relative_path = Path("llm") / f"document-{document_id}.json"
        self.write_json(relative_path, payload)
        return str(relative_path)

    def store_original(self, user_id: str, filename: str, content: bytes) -> str:
        relative_path = Path("originals") / user_id / filename
        encrypted = self._crypto.encrypt(content)
        self.write_bytes(relative_path, encrypted)
        return str(relative_path)

    def load_original(self, location: str) -> bytes:
        encrypted = (self.root / location).read_bytes()
        return self._crypto.decrypt(encrypted)
