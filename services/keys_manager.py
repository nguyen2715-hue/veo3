# -*- coding: utf-8 -*-
import threading
from typing import List, Dict
def _cfg():
    try:
        from utils import config as cfg
        return cfg.load() if hasattr(cfg,'load') else {}
    except Exception:
        return {}
class RoundRobinPool:
    def __init__(self, items: List[str]):
        self._items=[x for x in (items or []) if x]; self._i=0; self._lock=threading.Lock()
    def take(self)->str:
        with self._lock:
            if not self._items: return ''
            x=self._items[self._i % len(self._items)]; self._i+=1; return x
    def set_items(self, items: List[str]):
        with self._lock:
            self._items=[x for x in (items or []) if x]; self._i=0
    def snapshot(self)->List[str]: return list(self._items)
_POOLS: Dict[str, RoundRobinPool] = {
    'google': RoundRobinPool([]),
    'openai': RoundRobinPool([]),
    'elevenlabs': RoundRobinPool([]),
    'labs': RoundRobinPool([]),
}
def refresh():
    c=_cfg()
    _POOLS['google'].set_items(c.get('google_api_keys') or ([c.get('google_api_key')] if c.get('google_api_key') else []))
    _POOLS['openai'].set_items(c.get('openai_api_keys') or [])
    _POOLS['elevenlabs'].set_items(c.get('elevenlabs_api_keys') or [])
    _POOLS['labs'].set_items(c.get('labs_tokens') or c.get('tokens') or [])
    return _POOLS
def take(provider:str)->str:
    if provider not in _POOLS: refresh()
    return _POOLS.get(provider, RoundRobinPool([])).take()
def rotated_list(provider:str, base:list)->list:
    base=[x for x in (base or []) if x]
    if not base: return base
    k=take(provider)
    if not k or k not in base: return base
    return [k] + [x for x in base if x!=k]
