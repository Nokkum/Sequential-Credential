import os
import json
import base64
import sqlite3
import logging
from threading import Lock
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('sequential.db')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(handler)


class Database:
    JSON_FILE = 'server_settings.json'
    SQLITE_FILE = 'server_settings.db'

    def __init__(self, sqlite_path: Optional[str] = None, use_psql: bool = False, pg_conn_str: Optional[str] = None):
        self.lock = Lock()
        self.json_path = self.JSON_FILE
        self.sqlite_path = sqlite_path or self.SQLITE_FILE
        self.use_psql = use_psql
        self.pg_conn_str = pg_conn_str

        self._init_json()
        self._init_sqlite()

    def _init_json(self):
        if not os.path.exists(self.json_path):
            with open(self.json_path, 'w') as f:
                json.dump({}, f)

    def _read_json(self) -> Dict[str, Any]:
        try:
            with open(self.json_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_json(self, data: Dict[str, Any]):
        with open(self.json_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _init_sqlite(self):
        conn = sqlite3.connect(self.sqlite_path)
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    category TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    config_name TEXT NOT NULL,
                    info TEXT,
                    blob BLOB,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (category, provider, config_name)
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    # JSON-centric API (backward compatibility)
    def get(self, category: str, provider_config: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            data = self._read_json()
            return data.get(category, {}).get(provider_config)

    def set(self, category: str, provider_config: str, info: Dict[str, Any]):
        with self.lock:
            data = self._read_json()
            data.setdefault(category, {})[provider_config] = {**info, 'updated_at': datetime.utcnow().isoformat()}
            self._write_json(data)
            logger.debug('Wrote JSON metadata for %s/%s', category, provider_config)

            provider, cfg = provider_config.split('_', 1)
            self._sqlite_upsert(category, provider, cfg, json.dumps(info), None)

    def delete(self, category: str, provider_config: str):
        with self.lock:
            data = self._read_json()
            if category in data and provider_config in data[category]:
                del data[category][provider_config]
                if not data[category]:
                    del data[category]
                self._write_json(data)
                logger.debug('Deleted JSON metadata for %s/%s', category, provider_config)

            provider, cfg = provider_config.split('_', 1)
            self._sqlite_delete(category, provider, cfg)

    def list_all(self) -> Dict[str, Any]:
        with self.lock:
            return self._read_json()

    # sqlite operations
    def _sqlite_upsert(self, category, provider, cfg, info_text, blob_bytes):
        conn = sqlite3.connect(self.sqlite_path)
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO metadata (category, provider, config_name, info, blob, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, provider, config_name) DO UPDATE SET
                    info = excluded.info,
                    blob = COALESCE(excluded.blob, metadata.blob),
                    updated_at = excluded.updated_at
            ''', (category, provider, cfg, info_text, blob_bytes, datetime.utcnow()))
            conn.commit()
        finally:
            conn.close()

    def _sqlite_delete(self, category, provider, cfg):
        conn = sqlite3.connect(self.sqlite_path)
        try:
            cur = conn.cursor()
            cur.execute('DELETE FROM metadata WHERE category=? AND provider=? AND config_name=?', (category, provider, cfg))
            conn.commit()
        finally:
            conn.close()

    def set_blob(self, category, provider, cfg, meta: Dict[str, Any]):
        with self.lock:
            blob_b64 = meta.get('blob')
            blob_bytes = base64.b64decode(blob_b64) if blob_b64 else None
            info = {k: v for k, v in meta.items() if k != 'blob'}
            # JSON mirror
            self.set(category, f"{provider}_{cfg}", info)
            # sqlite store
            self._sqlite_upsert(category, provider, cfg, json.dumps(info), blob_bytes)
            logger.debug('Stored blob in sqlite for %s/%s/%s', category, provider, cfg)

    def get_blob_entry(self, category, provider, cfg) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.sqlite_path)
        try:
            cur = conn.cursor()
            cur.execute('SELECT info, blob, updated_at FROM metadata WHERE category=? AND provider=? AND config_name=?', (category, provider, cfg))
            row = cur.fetchone()
            if not row:
                return None
            info_text, blob, updated = row
            info = json.loads(info_text) if info_text else {}
            blob_b64 = base64.b64encode(blob).decode('utf-8') if blob else None
            return {'info': info, 'blob': blob_b64, 'updated_at': updated}
        finally:
            conn.close()

    def export_provider(self, category, provider) -> Dict[str, Any]:
        out = {}
        all_meta = self._read_json().get(category, {})
        for key, meta in all_meta.items():
            if key.startswith(provider + '_'):
                out[key] = meta
                parts = key.split('_', 1)
                cfg = parts[1]
                entry = self.get_blob_entry(category, provider, cfg)
                if entry and entry.get('blob'):
                    out[key]['blob'] = entry['blob']
        return out

    def export_to_file(self, data: Dict[str, Any], path: str):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def import_from_file(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
        for key, meta in data.items():
            parts = key.split('_', 1)
            if len(parts) != 2:
                continue
            provider, cfg = parts
            blob = meta.get('blob')
            info = {k: v for k, v in meta.items() if k != 'blob'}
            self.set('tokens', key, info)
            if blob:
                self.set_blob('tokens', provider, cfg, {'blob': blob})