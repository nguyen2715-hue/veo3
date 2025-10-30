# -*- coding: utf-8 -*-
import os, base64, json, requests, mimetypes, uuid
def _cfg():
    try:
        from utils import config as cfg
        return cfg.load() if hasattr(cfg, "load") else {}
    except Exception:
        return {}
def _google_keys():
    from services.keys_manager import refresh, rotated_list
    c=_cfg(); refresh()
    out=[]
    # prefer list field
    out += [k for k in (c.get("google_api_keys") or []) if k]
    # legacy single
    if c.get("google_api_key"): out.append(c["google_api_key"])
    # legacy mixed store
    for t in (c.get("tokens") or []):
        if isinstance(t, dict) and t.get("kind") in ("gemini","google"):
            v=t.get("token") or t.get("value")
            if v: out.append(v)
    # de-dup preserve order
    seen=set(); out2=[]
    for k in out:
        if k and (k not in seen):
            out2.append(k); seen.add(k)
    return rotated_list('google', out2)
