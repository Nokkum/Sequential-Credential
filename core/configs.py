import os
from typing import Optional


class ConfigManager:
    BASE = '.sequential'

    def __init__(self, db, encryption):
        os.makedirs(self.BASE, exist_ok=True)
        os.makedirs(os.path.join(self.BASE, 'tokens', 'encrypted'), exist_ok=True)
        os.makedirs(os.path.join(self.BASE, 'tokens', 'key'), exist_ok=True)
        os.makedirs(os.path.join(self.BASE, 'apis', 'encrypted'), exist_ok=True)
        os.makedirs(os.path.join(self.BASE, 'apis', 'key'), exist_ok=True)
        self.db = db
        self.encryption = encryption

    def _file_paths(self, category, provider, cfg):
        ext = '.token' if category == 'tokens' else '.api'
        enc_dir = os.path.join(self.BASE, category, 'encrypted')
        key_dir = os.path.join(self.BASE, category, 'key')
        token_file = os.path.join(enc_dir, f".{provider.lower()}_{cfg}{ext}")
        key_file = os.path.join(key_dir, f".{provider.lower()}_{cfg}.key")
        return token_file, key_file

    def save_to_filesystem(self, category, provider, cfg, encrypted_bytes: bytes) -> dict:
        token_file, key_file = self._file_paths(category, provider, cfg)
        with open(token_file, 'wb') as f:
            f.write(encrypted_bytes)
        with open(key_file, 'wb') as f:
            f.write(b'fingerprint')
        meta = {'token_file': token_file, 'key_file': key_file, 'length': len(encrypted_bytes)}
        return meta

    def load_from_filesystem(self, category, provider, cfg) -> Optional[str]:
        token_file, _ = self._file_paths(category, provider, cfg)
        if not os.path.exists(token_file):
            return None
        with open(token_file, 'rb') as f:
            enc = f.read()
        try:
            return self.encryption.decrypt(enc)
        except Exception:
            return None

    def delete_filesystem(self, category, provider, cfg):
        token_file, key_file = self._file_paths(category, provider, cfg)
        if os.path.exists(token_file):
            os.remove(token_file)
        if os.path.exists(key_file):
            os.remove(key_file)

    def list_configs(self, category, provider):
        all_meta = self.db.list_all().get(category, {})
        out = []
        for key in all_meta.keys():
            if key.startswith(provider + '_'):
                out.append(key.split('_', 1)[1])
        return out