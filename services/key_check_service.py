# -*- coding: utf-8 -*-
import requests, datetime
from typing import Tuple

# Constants
MIN_JWT_TOKEN_LENGTH = 50  # Minimum expected length for JWT session tokens

def _ts(): return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def _fmt_err(prefix, r):
    try:
        j = r.json(); msg = ""
        if isinstance(j, dict):
            err = j.get("error") or {}
            msg = err.get("message") or j.get("message") or ""
        return f"{prefix} ({r.status_code}) — {msg} @ {_ts()}"
    except Exception:
        return f"{prefix} ({r.status_code}) — {r.text[:200]} @ {_ts()}"

def check(kind: str, key: str) -> Tuple[bool, str]:
    kind=(kind or '').lower(); k=(key or '').strip()
    try:
        if kind in ('labs','google_labs','google labs'):
            url='https://aisandbox-pa.googleapis.com/v1/video:batchCheck'
            h={'authorization': f'Bearer {k}', 'content-type':'application/json'}
            r=requests.post(url, json={}, headers=h, timeout=(10,20))
            if r.status_code in (200,400): return True, f'OK @ {_ts()}'
            if r.status_code in (401,403): return False, _fmt_err('Unauthorized', r)
            return False, _fmt_err('HTTP', r)
        if kind in ('google','gemini','google_api'):
            r=requests.get('https://generativelanguage.googleapis.com/v1/models', params={'key':k}, timeout=(10,20))
            if r.status_code==200: return True, f'OK @ {_ts()}'
            if r.status_code in (401,403): return False, _fmt_err('Unauthorized', r)
            return False, _fmt_err('HTTP', r)
        if kind in ('eleven','elevenlabs'):
            r=requests.get('https://api.elevenlabs.io/v1/user', headers={'xi-api-key':k}, timeout=(10,20))
            if r.status_code==200: return True, f'OK @ {_ts()}'
            if r.status_code in (401,403): return False, _fmt_err('Unauthorized', r)
            return False, _fmt_err('HTTP', r)
        if kind in ('openai',):
            r=requests.get('https://api.openai.com/v1/models', headers={'authorization': f'Bearer {k}'}, timeout=(10,20))
            if r.status_code==200: return True, f'OK @ {_ts()}'
            if r.status_code in (401,403): return False, _fmt_err('Unauthorized', r)
            return False, _fmt_err('HTTP', r)
        if kind in ('session', 'whisk_session'):
            # Session tokens are cookie-based, harder to validate without full context
            # Just check if it looks like a valid JWT token
            if k and len(k) > MIN_JWT_TOKEN_LENGTH and '.' in k:
                return True, f'Format OK (not fully validated) @ {_ts()}'
            return False, f'Invalid format @ {_ts()}'
    except Exception as e:
        return False, f'ERR {e} @ {_ts()}'
    return False, 'Unknown kind'
