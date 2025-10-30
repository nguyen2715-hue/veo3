# -*- coding: utf-8 -*-
import os, time
from typing import List, Dict, Any
from utils import config as cfg
from services.labs_flow_service import LabsClient, DEFAULT_PROJECT_ID

_RATIO_MAP = {
    '16:9': 'VIDEO_ASPECT_RATIO_LANDSCAPE',
    '21:9': 'VIDEO_ASPECT_RATIO_LANDSCAPE',
    '9:16': 'VIDEO_ASPECT_RATIO_PORTRAIT',
    '4:5' : 'VIDEO_ASPECT_RATIO_PORTRAIT',
    '1:1' : 'VIDEO_ASPECT_RATIO_SQUARE',
}

def _aspect(ratio_str: str)->str:
    return _RATIO_MAP.get(ratio_str or '16:9', 'VIDEO_ASPECT_RATIO_LANDSCAPE')

def start_pipeline(project_name:str, ratio_str:str, scenes:List[Dict[str,Any]], image_style:str, product_text:str, lang:str,
                   model_imgs:List[str], product_imgs:List[str], copies:int=1)->Dict[str,Any]:
    st = cfg.load() or {}
    tokens = st.get("tokens") or []
    proj_id = st.get("default_project_id") or DEFAULT_PROJECT_ID
    client = LabsClient(tokens, on_event=None)
    aspect = _aspect(ratio_str)

    media_id = None
    try:
        if product_imgs: media_id = client.upload_image_file(product_imgs[0])
        elif model_imgs: media_id = client.upload_image_file(model_imgs[0])
    except Exception:
        media_id = None

    jobs = []
    for sc in scenes:
        body = {"project": project_name, "scene": sc.get("index"), "media_id": media_id}
        prompt_json = {"objective": sc.get("prompt_video") or sc.get("desc") or "", "language": lang, "image_style": image_style}
        rc = client.start_one(body, model_key="auto", aspect_ratio=aspect, prompt_text=prompt_json, copies=max(1, int(copies)), project_id=proj_id)
        op_names = body.get("operation_names") or getattr(client, "last_operation_names", []) or []
        for nm in op_names:
            jobs.append({"scene": sc.get("index"), "copy": 1, "op": nm})
    return {"jobs": jobs, "project_id": proj_id}

def poll_and_download(client:LabsClient, jobs:List[Dict[str,Any]], out_dir:str, on_progress=None, sleep_sec:int=5)->List[Dict[str,Any]]:
    os.makedirs(out_dir, exist_ok=True)
    done = []
    ops = [j["op"] for j in jobs]
    while ops:
        rs = client.batch_check_operations(ops) or {}
        new_ops = []
        for j in jobs:
            info = rs.get(j["op"]) or {}
            st = info.get("status") or "PROCESSING"
            if st in ("DONE","COMPLETED","DONE_NO_URL","FAILED","ERROR"):
                url = (info.get("video_urls") or [None])[0]
                if url and st in ("DONE","COMPLETED"):
                    import requests
                    fp = os.path.join(out_dir, f"scene_{j['scene']}_copy_{j['copy']}.mp4")
                    try:
                        r = requests.get(url, timeout=600); r.raise_for_status()
                        with open(fp, "wb") as f: f.write(r.content)
                        j["path"] = fp
                    except Exception:
                        pass
                j["status"] = st
                done.append(j)
            else:
                new_ops.append(j["op"])
            if callable(on_progress):
                try: on_progress(j, info)
                except Exception: pass
        ops = new_ops
        if ops:
            try: time.sleep(sleep_sec)
            except Exception: pass
    return done
