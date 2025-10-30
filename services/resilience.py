# -*- coding: utf-8 -*-
import threading
from contextlib import contextmanager

def _cfg():
    try:
        from utils import config as cfg
        return cfg.load() if hasattr(cfg,'load') else {}
    except Exception:
        return {}

def _limit(name:str, default:int):
    c=_cfg()
    return int(c.get('resilience', {}).get('concurrency', {}).get(name, default))

_SEMAPHORES = {
    'labs': threading.Semaphore(_limit('labs', 3)),
    'google': threading.Semaphore(_limit('google', 5)),
    'openai': threading.Semaphore(_limit('openai', 5)),
    'elevenlabs': threading.Semaphore(_limit('elevenlabs', 3)),
}

@contextmanager
def acquire(provider:str):
    sem = _SEMAPHORES.get(provider)
    if sem is None:
        sem = threading.Semaphore(_limit(provider, 3))
        _SEMAPHORES[provider] = sem
    sem.acquire()
    try:
        yield
    finally:
        sem.release()
