
import json, os

def _atomic_write_json(path, data):
    import json, os, tempfile
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_cfg_", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass



CFG_PATH = os.path.join(os.path.expanduser("~"), ".veo_image2video_cfg.json")

def load()->dict:
    try:
        if os.path.exists(CFG_PATH):
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"tokens":[], "default_project_id":"", "google_api_key":"", "download_root":""}

def save(cfg: dict)->dict:
    try:
        _atomic_write_json(CFG_PATH, cfg)
    except Exception:
        pass
    return cfg
