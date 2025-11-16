import os
import base64
from typing import Tuple


def migrate_filesystem_to_db(db, cfg_manager) -> int:
    """Scan .sequential filesystem encrypted directories and copy entries into DB blobs.

    Returns the number of migrated entries.
    """
    base = cfg_manager.BASE
    migrated = 0
    for category in ('tokens', 'apis'):
        enc_dir = os.path.join(base, category, 'encrypted')
        if not os.path.isdir(enc_dir):
            continue
        for fname in os.listdir(enc_dir):
            # expect files named like .provider_config.token or .provider_config.api
            if not fname.startswith('.'):
                continue
            path = os.path.join(enc_dir, fname)
            try:
                # parse name
                name, _ext = os.path.splitext(fname)
                # name like .provider_config
                name = name.lstrip('.')
                if '_' not in name:
                    continue
                provider, cfg = name.split('_', 1)
                with open(path, 'rb') as f:
                    blob = f.read()
                blob_b64 = base64.b64encode(blob).decode('utf-8')
                db.set_blob(category, provider, cfg, {'blob': blob_b64})
                migrated += 1
            except Exception:
                continue
    return migrated


if __name__ == '__main__':
    # CLI helper for migration
    import argparse
    from core.database import Database
    from core.configs import ConfigManager
    from core.security import EncryptionManager

    parser = argparse.ArgumentParser()
    parser.add_argument('--migrate', action='store_true', help='Run filesystem->DB migration')
    args = parser.parse_args()
    if args.migrate:
        db = Database()
        enc = EncryptionManager(None)
        cfg = ConfigManager(db, enc)
        count = migrate_filesystem_to_db(db, cfg)
        print(f'Migrated {count} entries')