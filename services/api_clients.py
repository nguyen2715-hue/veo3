# -*- coding: utf-8 -*-
from typing import Dict, Any, Tuple
from services.http_retry import request_json
from services.core.key_manager import get_all_keys
from services.resilience import acquire

def labs_call(method:str, url:str, *, json_body=None, params=None, headers=None):
    tokens = get_all_keys('labs')
    last_err = ""; last_code = 0; last_headers = {}
    for t in tokens or [""]:
        h = dict(headers or {})
        if t: h['authorization'] = f'Bearer {t}'
        with acquire('labs'):
            ok, data, err, code, resp_headers = request_json(method, url, headers=h, params=params, json_body=json_body)
        if ok: return ok, data, code, resp_headers
        last_err, last_code, last_headers = err, code, resp_headers
        if code in (401, 403): continue
        break
    return False, {"error": last_err, "trace": last_headers.get("x-request-id","")}, last_code, last_headers

def google_call(method:str, url:str, *, json_body=None, params=None, headers=None):
    keys = get_all_keys('google')
    last_err = ""; last_code = 0; last_headers = {}
    for k in keys or [""]:
        p = dict(params or {})
        if k: p['key'] = k
        with acquire('google'):
            ok, data, err, code, resp_headers = request_json(method, url, headers=headers, params=p, json_body=json_body)
        if ok: return ok, data, code, resp_headers
        last_err, last_code, last_headers = err, code, resp_headers
        if code in (401, 403): continue
        break
    return False, {"error": last_err, "trace": last_headers.get("x-request-id","")}, last_code, last_headers

def openai_call(method:str, url:str, *, json_body=None, params=None, headers=None):
    keys = get_all_keys('openai')
    last_err = ""; last_code = 0; last_headers = {}
    for k in keys or [""]:
        h = dict(headers or {})
        if k: h['authorization'] = f'Bearer {k}'
        with acquire('openai'):
            ok, data, err, code, resp_headers = request_json(method, url, headers=h, params=params, json_body=json_body)
        if ok: return ok, data, code, resp_headers
        last_err, last_code, last_headers = err, code, resp_headers
        if code in (401, 403): continue
        break
    return False, {"error": last_err, "trace": last_headers.get("x-request-id","")}, last_code, last_headers

def eleven_call(method:str, url:str, *, json_body=None, params=None, headers=None):
    keys = get_all_keys('elevenlabs')
    last_err = ""; last_code = 0; last_headers = {}
    for k in keys or [""]:
        h = dict(headers or {})
        if k: h['xi-api-key'] = k
        with acquire('elevenlabs'):
            ok, data, err, code, resp_headers = request_json(method, url, headers=h, params=params, json_body=json_body)
        if ok: return ok, data, code, resp_headers
        last_err, last_code, last_headers = err, code, resp_headers
        if code in (401, 403): continue
        break
    return False, {"error": last_err, "trace": last_headers.get("x-request-id","")}, last_code, last_headers
