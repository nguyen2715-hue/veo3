# -*- coding: utf-8 -*-
import requests, time, random
from typing import List, Optional
from services.core.config import load as load_config
from services.core.key_manager import get_all_keys, refresh
from services.core.api_config import GEMINI_TEXT_MODEL, gemini_text_endpoint

class MissingAPIKey(Exception): pass
class GeminiClient:
    def __init__(self, model: str = None, api_key: Optional[str] = None):
        refresh()
        keys: List[str] = get_all_keys('google')
        if api_key: keys = [api_key] + [k for k in keys if k != api_key]
        self.keys = list(dict.fromkeys(keys))
        if not self.keys: raise MissingAPIKey("Chưa nhập Google API Key trong Cài đặt.")
        random.shuffle(self.keys); self.rr=0; self.model=model or GEMINI_TEXT_MODEL
    def _next_key(self): k=self.keys[self.rr%len(self.keys)]; self.rr+=1; return k
    def _endpoint(self, key): return gemini_text_endpoint(key) if self.model == GEMINI_TEXT_MODEL else f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"
    def generate(self, system_text: str, user_text: str, timeout: int = 180)->str:
        last=None
        for i in range(5):
            key=self._next_key()
            try:
                body={"system_instruction":{"parts":[{"text":system_text}]},
                      "contents":[{"role":"user","parts":[{"text":user_text}]}]}
                r=requests.post(self._endpoint(key), json=body, timeout=timeout)
                if r.status_code in (429,408) or r.status_code>=500: raise requests.HTTPError(str(r.status_code), response=r)
                r.raise_for_status()
                data=r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except requests.RequestException as e:
                last=e; time.sleep(1.5*(i+1)); continue
        if last: raise last
        raise RuntimeError("Gemini không phản hồi")
