import json
import os
from typing import Dict

TEMPLATES_DIR = '.sequential/templates'

DEFAULT_TEMPLATES = {
    'Discord': {'fields': ['bot_token'], 'notes': 'Enter your Discord Bot token.'},
    'GitHub': {'fields': ['personal_access_token'], 'notes': 'Token with repo and user scope as needed.'},
    'OpenAI': {'fields': ['api_key'], 'notes': 'OpenAI API key.'}
}


def ensure_templates():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    path = os.path.join(TEMPLATES_DIR, 'provider_templates.json')
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(DEFAULT_TEMPLATES, f, indent=2)


def load_templates() -> Dict[str, Dict]:
    ensure_templates()
    with open(os.path.join(TEMPLATES_DIR, 'provider_templates.json'), 'r') as f:
        return json.load(f)