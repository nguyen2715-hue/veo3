# -*- coding: utf-8 -*-
import os, base64, json, requests, re
from typing import List, Tuple
from services.core.config import load as load_config
from services.core.key_manager import refresh, rotated_list

def _tokens_of(kinds:Tuple[str,...])->List[str]:
    out=[]; c=load_config(); refresh()
    # New structured lists
    if "elevenlabs" in kinds:
        out += [k for k in (c.get("elevenlabs_api_keys") or []) if k]
    if "openai" in kinds:
        out += [k for k in (c.get("openai_api_keys") or []) if k]
    if "google" in kinds or "gemini" in kinds or "google_tts" in kinds:
        out += [k for k in (c.get("google_api_keys") or []) if k]
        if c.get("google_api_key"): out.append(c.get("google_api_key"))
    # Legacy mixed store
    for t in (c.get("tokens") or []):
        if isinstance(t, dict) and (t.get("kind") in kinds):
            v=t.get("token") or t.get("value") or ""
            if v: out.append(v)
        elif isinstance(t, str) and len(t)>30:
            if "labs" in kinds:
                out.append(t)
    # de-dup preserve order
    seen=set(); arr=[]
    for k in out:
        if k and k not in seen: arr.append(k); seen.add(k)
    # rotate by first matched provider
    provider = "google" if ("google" in kinds or "gemini" in kinds or "google_tts" in kinds) else ("openai" if "openai" in kinds else ("elevenlabs" if "elevenlabs" in kinds else "labs"))
    try:
        arr = rotated_list(provider, arr)
    except Exception:
        pass
    return arr
