# -*- coding: utf-8 -*-
import os, math, json, datetime
from pathlib import Path
from typing import Dict, Any

def _cfg():
    try:
        from utils import config as cfg
        return cfg.load() if hasattr(cfg,'load') else {}
    except Exception:
        return {}

def default_project_name(now=None, base_dir=None)->str:
    d = (now or datetime.datetime.now()).strftime("%Y-%m-%d")
    root = Path(base_dir or _cfg().get('download_root') or Path.home()/ 'Downloads')
    idx = 1
    while (root / f"{d}-{idx}").exists():
        idx += 1
    return f"{d}-{idx}"

def ensure_project_dirs(project_name:str, base_dir=None)->Dict[str, Path]:
    root = Path(base_dir or _cfg().get('download_root') or Path.home() / 'Downloads') / project_name
    (root / "Video").mkdir(parents=True, exist_ok=True)
    (root / "Prompt").mkdir(parents=True, exist_ok=True)
    (root / "Ảnh xem trước").mkdir(parents=True, exist_ok=True)
    (root / "Audio").mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "video": root / "Video",
        "prompt": root / "Prompt",
        "preview": root / "Ảnh xem trước",
        "audio": root / "Audio",
        "social": root / "Bài đăng social.txt",
        "subtitle": root / "Phụ đề.srt",
        "thumbnail": root / "Ảnh thumbnail.png",
        "log": root / "nhat_ky_xu_ly.log",
    }

def calc_scenes(duration_sec:int)->int:
    if duration_sec<=0: return 1
    return max(1, math.ceil(duration_sec/8.0))

def write_text(p:Path, text:str):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text or "")

def append_log(p:Path, line:str):
    p.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")
