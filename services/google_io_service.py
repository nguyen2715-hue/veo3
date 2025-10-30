# -*- coding: utf-8 -*-
import os, csv, io, re, json, requests
from typing import List, Dict
def to_csv_export_url(sheet_url:str)->str:
    if "export?format=csv" in sheet_url: return sheet_url
    m=re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m: raise RuntimeError("Sheet URL không hợp lệ.")
    sid=m.group(1); gid="0"; mg=re.search(r"[?&#]gid=([0-9]+)", sheet_url)
    if mg: gid=mg.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
def read_sheet_rows(sheet_url:str)->List[Dict[str,str]]:
    url=to_csv_export_url(sheet_url); r=requests.get(url, timeout=60)
    if r.status_code>=400: raise RuntimeError(f"Không đọc được Sheet CSV (HTTP {r.status_code}).")
    data=r.content.decode("utf-8"); reader=csv.DictReader(io.StringIO(data))
    return [{k.strip(): (v or "").strip() for k,v in row.items()} for row in reader]
def drive_id_from_url(url:str)->str:
    pats=[r"https?://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/",r"https?://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",r"https?://drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)",r"https?://drive\.google\.com/uc\?export=download&id=([a-zA-Z0-9_-]+)"]
    for pat in pats:
        m=re.search(pat, url)
        if m: return m.group(1)
    return ""
def download_drive_file(url_or_id:str, out_path:str)->str:
    fid = url_or_id if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", url_or_id) else drive_id_from_url(url_or_id)
    if not fid: raise RuntimeError("Không nhận diện được file id từ Google Drive URL.")
    url=f"https://drive.google.com/uc?export=download&id={fid}"
    r=requests.get(url, timeout=120)
    if r.status_code>=400: raise RuntimeError(f"Tải Google Drive thất bại HTTP {r.status_code}")
    with open(out_path,"wb") as f: f.write(r.content)
    return out_path
def slugify(text:str):
    import unicodedata, re
    s=unicodedata.normalize('NFD', text); s=s.encode('ascii','ignore').decode('utf-8')
    s=re.sub(r'[^a-zA-Z0-9\- ]+','', s).strip().lower(); s=re.sub(r'\s+','-', s); return s or "product"
