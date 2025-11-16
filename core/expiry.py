from datetime import datetime, timedelta
from typing import Optional


def compute_expiry_from_provider(provider: str, info: dict) -> Optional[str]:
    """Try to compute an expiry date string for tokens that supply TTL metadata.

    Returns ISO timestamp or None
    """
    # Placeholder heuristics — real implementations require provider APIs
    if provider.lower() == 'discord':
        # Discord bot tokens do not expire by default; return None
        return None
    if provider.lower() == 'github':
        # If info contains 'expires_in' use it
        expires_in = info.get('expires_in')
        if expires_in:
            return (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat()
    return None