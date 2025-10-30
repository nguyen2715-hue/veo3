import base64, mimetypes, json, time, requests, os, re
from typing import List, Dict, Optional, Tuple, Callable, Any


# Optional default_project_id from user config (non-breaking)
try:
    from utils import config as _cfg_mod  # type: ignore
    _cfg = getattr(_cfg_mod, "load", lambda: {})() if hasattr(_cfg_mod, "load") else {}
    _cfg_pid = None
    if isinstance(_cfg, dict):
        _cfg_pid = _cfg.get("default_project_id") or (_cfg.get("labs") or {}).get("default_project_id")
    if _cfg_pid:
        DEFAULT_PROJECT_ID = _cfg_pid  # override safely if present
except Exception:
    pass


# Support both package and flat layouts
try:
    from services.endpoints import UPLOAD_IMAGE_URL, I2V_URL, T2V_URL, BATCH_CHECK_URL
except Exception:  # pragma: no cover
    from endpoints import UPLOAD_IMAGE_URL, I2V_URL, T2V_URL, BATCH_CHECK_URL

DEFAULT_PROJECT_ID = "87b19267-13d6-49cd-a7ed-db19a90c9339"

def _headers(bearer: str) -> dict:
    return {
        "authorization": f"Bearer {bearer}",
        "content-type": "application/json; charset=utf-8",
        "origin": "https://labs.google",
        "referer": "https://labs.google/",
        "user-agent": "Mozilla/5.0"
    }

def _encode_image_file(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("utf-8")
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return b64, mime

_URL_PAT = re.compile(r'^(https?://|gs://)', re.I)
def _collect_urls_any(obj: Any) -> List[str]:
    urls=set(); KEYS={"gcsUrl","gcsUri","signedUrl","signedUri","downloadUrl","downloadUri","videoUrl","url","uri","fileUri"}
    def visit(x):
        if isinstance(x, dict):
            for k,v in x.items():
                if k in KEYS and isinstance(v,str) and _URL_PAT.match(v): urls.add(v)
                else: visit(v)
        elif isinstance(x, list):
            for it in x: visit(it)
        elif isinstance(x, str):
            if _URL_PAT.match(x): urls.add(x)
    visit(obj)
    lst=list(urls); lst.sort(key=lambda u: (0 if "/video/" in u else 1, len(u)))
    return lst

def _normalize_status(item: dict) -> str:
    if item.get("done") is True:
        if item.get("error"): return "FAILED"
        return "DONE"
    s=item.get("status") or ""
    if s in ("MEDIA_GENERATION_STATUS_SUCCEEDED","SUCCEEDED","SUCCESS"): return "DONE"
    if s in ("MEDIA_GENERATION_STATUS_FAILED","FAILED","ERROR"): return "FAILED"
    return "PROCESSING"

def _trim_prompt_text(prompt_text: Any)->str:
    """If prompt is a large JSON string/object, reduce to essential fields to avoid 400 'invalid argument'."""
    if isinstance(prompt_text, str):
        s=prompt_text.strip()
        if len(s)<=1800: return s
        try:
            obj=json.loads(s)
        except Exception:
            return s[:1800]
    else:
        obj=prompt_text
    if isinstance(obj, dict):
        parts=[]
        if obj.get("Objective"): parts.append(str(obj["Objective"]))
        per=obj.get("Persona") or {}
        if isinstance(per, dict):
            tone=per.get("Tone"); role=per.get("Role")
            if role or tone: parts.append(f"Role: {role or ''}; Tone: {tone or ''}")
        inst=obj.get("Task_Instructions") or []
        if isinstance(inst, list):
            parts+= [str(x) for x in inst][:6]
        cons=obj.get("Constraints") or []
        if isinstance(cons, list):
            parts+= [str(x) for x in cons][:4]
        text=" | ".join([p for p in parts if p])
        if text: return text[:1800]
    try:
        return json.dumps(obj, ensure_ascii=False)[:1800]
    except Exception:
        return str(obj)[:1800]

class LabsClient:
    def __init__(self, bearers: List[str], timeout: Tuple[int,int]=(20,180), on_event: Optional[Callable[[dict], None]]=None):
        self.tokens=[t.strip() for t in (bearers or []) if t.strip()]
        if not self.tokens: raise ValueError("No Labs tokens provided")
        self._idx=0; self.timeout=timeout; self.on_event=on_event

    def _tok(self)->str:
        t=self.tokens[self._idx % len(self.tokens)]; self._idx+=1; return t

    def _emit(self, kind: str, **kw):
        if self.on_event:
            try: self.on_event({"kind":kind, **kw})
            except Exception: pass

    def _post(self, url: str, payload: dict) -> dict:
        last=None
        for attempt in range(3):
            try:
                r=requests.post(url, headers=_headers(self._tok()), json=payload, timeout=self.timeout)
                if r.status_code==200:
                    self._emit("http_ok", code=200)
                    try: return r.json()
                    except Exception: return {}
                det=""
                try: det=r.json().get("error",{}).get("message","")[:300]
                except Exception: det=(r.text or "")[:300]
                self._emit("http_other_err", code=r.status_code, detail=det); r.raise_for_status()
            except Exception as e:
                last=e; time.sleep(0.7*(attempt+1))
        raise last

    def upload_image_file(self, image_path: str, aspect_hint="IMAGE_ASPECT_RATIO_PORTRAIT")->Optional[str]:
        b64,mime=_encode_image_file(image_path)
        payload={"imageInput":{"rawImageBytes":b64,"mimeType":mime,"isUserUploaded":True,"aspectRatio":aspect_hint},
                 "clientContext":{"sessionId":f"{int(time.time()*1000)}"}}
        data=self._post(UPLOAD_IMAGE_URL,payload) or {}
        mid=(data.get("mediaGenerationId") or {}).get("mediaGenerationId")
        return mid

    def start_one(self, job: Dict, model_key: str, aspect_ratio: str, prompt_text: str, copies:int=1, project_id: Optional[str]=DEFAULT_PROJECT_ID)->int:
        """Start a scene with robust fallbacks: delay-after-upload, model ladder (I2V vs T2V), reupload-on-400, per-copy fallback, prompt trimming."""
        copies=max(1,int(copies)); base_seed=int(job.get("seed",0)) if str(job.get("seed","")).isdigit() else 0
        mid=job.get("media_id")

        # Give backend a moment to index the uploaded image (avoids 400/500 immediately after upload)
        time.sleep(1.0)

        # IMPORTANT: choose fallbacks based on whether we're doing I2V (has start image) or T2V (no image)
        FALLBACKS_I2V={
            "VIDEO_ASPECT_RATIO_PORTRAIT":[
                "veo_3_1_i2v_s_fast_portrait_ultra","veo_3_1_i2v_s_fast_portrait","veo_3_1_i2v_s_portrait","veo_3_1_i2v_s"
            ],
            "VIDEO_ASPECT_RATIO_LANDSCAPE":[
                "veo_3_1_i2v_s_fast_ultra","veo_3_1_i2v_s_fast","veo_3_1_i2v_s"
            ],
            "VIDEO_ASPECT_RATIO_SQUARE":[
                "veo_3_1_i2v_s_fast","veo_3_1_i2v_s"
            ]
        }
        FALLBACKS_T2V={
            "VIDEO_ASPECT_RATIO_PORTRAIT":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ],
            "VIDEO_ASPECT_RATIO_LANDSCAPE":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ],
            "VIDEO_ASPECT_RATIO_SQUARE":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ]
        }
        fallbacks = FALLBACKS_I2V if mid else FALLBACKS_T2V
        # start with the user's chosen model, then ladder through same-family models for the aspect
        models=[model_key]+[m for m in fallbacks.get(aspect_ratio, []) if m!=model_key]

        # compose prompt text (trim if huge/complex)
        prompt=_trim_prompt_text(prompt_text)

        def _make_body(use_model, mid_val, copies_n):
            reqs=[]
            for k in range(copies_n):
                seed=base_seed+k
                item={"aspectRatio":aspect_ratio,"seed":seed,"videoModelKey":use_model,"textInput":{"prompt":prompt}}
                if mid_val: item["startImage"]={"mediaId":mid_val}
                reqs.append(item)
            body={"requests":reqs}
            if project_id: body["clientContext"]={"projectId":project_id}
            return body

        def _try(body):
            url=I2V_URL if mid else T2V_URL
            return self._post(url, body) or {}

        def _is_invalid(e: Exception)->bool:
            s=str(e).lower()
            return ("400" in str(e)) or ("invalid json" in s) or ("invalid argument" in s)

        # 1) Try batch with model fallbacks
        data=None; last_err=None
        for mkey in models:
            try:
                data=_try(_make_body(mkey, mid, copies))
                last_err=None; break
            except Exception as e:
                last_err=e
                if not _is_invalid(e): break

        # 2) If invalid and have image -> reupload once then retry ladder (I2V only)
        if last_err and _is_invalid(last_err) and mid and job.get("image_path"):
            try:
                new_mid=self.upload_image_file(job["image_path"])
                if new_mid:
                    job["media_id"]=new_mid; mid=new_mid
                    for mkey in models:
                        try:
                            data=_try(_make_body(mkey, mid, copies)); last_err=None; break
                        except Exception as e2:
                            last_err=e2
                            if not _is_invalid(e2): break
            except Exception as e3:
                last_err=e3

        # 3) Per-copy fallback (still invalid)
        job.setdefault("operation_names",[]); job.setdefault("video_by_idx", [None]*copies); job.setdefault("thumb_by_idx", [None]*copies); job.setdefault("op_index_map", {})
        if data is None and last_err is not None:
            for k in range(copies):
                for mkey in models:
                    try:
                        dat=_try(_make_body(mkey, mid, 1))
                        ops=dat.get("operations",[]) if isinstance(dat,dict) else []
                        if ops:
                            nm=(ops[0].get("operation") or {}).get("name") or ops[0].get("name") or ""
                            if nm: job["operation_names"].append(nm); job["op_index_map"][nm]=k; break
                    except Exception: continue
            return len(job.get("operation_names",[]))

        # 4) Batch success
        ops=data.get("operations",[]) if isinstance(data,dict) else []
        for ci,op in enumerate(ops):
            nm=(op.get("operation") or {}).get("name") or op.get("name") or ""
            if nm: job["operation_names"].append(nm); job["op_index_map"][nm]=ci
        if job.get("operation_names"): job["status"]="PENDING"
        return len(job.get("operation_names",[]))

    def _wrap_ops(self, op_names: List[str])->dict:
        uniq=[]; seen=set()
        for s in op_names or []:
            if s and s not in seen: seen.add(s); uniq.append(s)
        return {"operations":[{"operation":{"name":s}} for s in uniq]}

    def batch_check_operations(self, op_names: List[str])->Dict[str,Dict]:
        if not op_names: return {}
        data=self._post(BATCH_CHECK_URL, self._wrap_ops(op_names)) or {}
        out={}
        def _dedup(xs):
            seen=set(); r=[]
            for x in xs:
                if x not in seen: seen.add(x); r.append(x)
            return r
        for item in data.get("operations",[]):
            key=(item.get("operation") or {}).get("name") or item.get("name") or ""
            st=_normalize_status(item)
            urls=_collect_urls_any(item.get("response",{})) or _collect_urls_any(item)
            vurls=[u for u in urls if "/video/" in u]; iurls=[u for u in urls if "/image/" in u]
            out[key or "unknown"]={"status": ("COMPLETED" if st=="DONE" and vurls else ("DONE_NO_URL" if st=="DONE" else st)),
                                   "video_urls": _dedup(vurls), "image_urls": _dedup(iurls), "raw": item}
        return out
