
import os, json, shutil, subprocess, datetime, random, random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, QSpinBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QLocale, QThread, pyqtSignal, QObject, QUrl
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.Qt import QDesktopServices
from utils import config as cfg
from services.labs_flow_service import LabsClient, DEFAULT_PROJECT_ID

_ASPECT_MAP = {
    "16:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "21:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "9:16": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "4:5": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "1:1": "VIDEO_ASPECT_RATIO_SQUARE",
}
_LANGS = [
    ("Tiếng Việt","vi"), ("Tiếng Anh","en"), ("Tiếng Nhật","ja"), ("Tiếng Hàn","ko"), ("Tiếng Trung","zh"),
    ("Tiếng Pháp","fr"), ("Tiếng Đức","de"), ("Tiếng Tây Ban Nha","es"), ("Tiếng Nga","ru"), ("Tiếng Thái","th"), ("Tiếng Indonesia","id")
]
_VIDEO_MODELS = [
    "veo_3_1_i2v_s_fast_portrait_ultra",
    "veo_3_1_i2v_s_fast_landscape_ultra",
    "veo_3_1_i2v_xl_portrait",
    "veo_3_1_i2v_xl_landscape",
]

def build_prompt_json(scene_index:int, desc_vi:str, desc_tgt:str, lang_code:str, ratio_str:str, style:str, seconds:int=8, copies:int=1, resolution_hint:str=None, character_bible=None):
    """
    Strict prompt JSON schema:
    - objective/persona/constraints/assets/hard_locks/character_details/setting_details/key_action/camera_direction/audio/graphics/negatives/generation
    - bilingual localization (vi + target)
    """
    ratio_map = {
        '16:9': ('1920x1080', 'VIDEO_ASPECT_RATIO_LANDSCAPE'),
        '21:9': ('2560x1080', 'VIDEO_ASPECT_RATIO_LANDSCAPE'),
        '9:16': ('1080x1920', 'VIDEO_ASPECT_RATIO_PORTRAIT'),
        '4:5' : ('1080x1350', 'VIDEO_ASPECT_RATIO_PORTRAIT'),
        '1:1' : ('1080x1080', 'VIDEO_ASPECT_RATIO_SQUARE'),
    }
    res_default, _ = ratio_map.get(ratio_str, ('1920x1080', 'VIDEO_ASPECT_RATIO_LANDSCAPE'))
    resolution = resolution_hint or res_default
    seconds = max(3, int(seconds or 8))
    copies = max(1, int(copies or 1))

    b1 = round(seconds * 0.25, 2)
    b2 = round(seconds * 0.55, 2)
    b3 = round(seconds * 0.80, 2)
    segments = [
        {"t": f"0.0-{b1}s", "shot": "Establish subject & scene; clean composition; slow, steady motion."},
        {"t": f"{b1}-{b2}s", "shot": "Key action / gesture; maintain framing consistency; avoid jump cuts."},
        {"t": f"{b2}-{b3}s", "shot": "Detail emphasis; micro-movements; texture & highlights."},
        {"t": f"{b3}-{seconds:.1f}s", "shot": "Clear end beat; micro push-in or hold; leave space for on-screen text."},
    ]

    style_tags = []
    sl = (style or "").lower()
    if "điện ảnh" in sl or "cinematic" in sl: style_tags += ["cinematic","natural light","soft shadows"]
    if "anime" in sl or "hoạt hình" in sl: style_tags += ["anime","flat colors","outlined"]
    if "tài liệu" in sl or "documentary" in sl: style_tags += ["documentary","handheld feel"]
    if not style_tags: style_tags = ["modern","clean"]

    hard_locks = {
        "identity": "Keep the same face, body, and identity across scenes.",
        "wardrobe": "Outfit consistency is required. Do NOT change outfit, color, or add accessories without instruction.",
        "hair_makeup": "Keep hair and makeup consistent; do NOT change length or color unless explicitly instructed.",
        "location": "Keep to single coherent environment; no random background swaps."
    }

    character_details = "Primary talent remains visually consistent across all scenes."
    if character_bible and isinstance(character_bible, list) and len(character_bible)>0:
        main = character_bible[0]
        nm = main.get("name",""); role = main.get("role",""); key = main.get("key_trait",""); mot = main.get("motivation","")
        character_details = f"{nm} ({role}) — trait: {key}; motivation: {mot}. Keep appearance and demeanor consistent."

    vo_text = (desc_tgt or desc_vi or "").strip()
    if len(vo_text)>240: vo_text = vo_text[:240] + "…"

    data = {
        "scene_id": f"s{scene_index:02d}",
        "objective": "Generate a short video clip for this scene based on screenplay and prompts.",
        "persona": {
            "role": "Creative Video Director",
            "tone": "Cinematic and evocative",
            "knowledge_level": "Expert in visual storytelling"
        },
        "constraints": {
            "duration_seconds": seconds,
            "aspect_ratio": ratio_str,
            "resolution": resolution,
            "visual_style_tags": style_tags,
            "camera": { "fps": 24, "lens_hint": "50mm look", "stabilization": "steady tripod-like" }
        },
        "assets": { "images": {} },
        "hard_locks": hard_locks,
        "character_details": character_details,
        "setting_details": "Clean composition, minimal props, no clutter; coherent lighting per scene style.",
        "key_action": (desc_tgt or desc_vi or "").strip(),
        "camera_direction": segments,
        "audio": {
            "voiceover": { "language": lang_code or "vi", "voice_hint": "neutral_narrative", "pace": 1.0, "text": vo_text },
            "music_bed": "subtle, minimal, non-intrusive"
        },
        "graphics": {
            "subtitles": { "enabled": True, "language": lang_code or "vi", "style": "clean small caps, bottom-safe" },
            "on_screen_text": []
        },
        "negatives": [
            "Do NOT change character identity, outfit, or location without instruction.",
            "Avoid jarring cuts or random background swaps.",
            "No brand logos unless present in references.",
            "No unrealistic X-ray views; use graphic overlays only."
        ],
        "generation": { "seed": __import__("random").randint(0, 2**31-1), "copies": copies },
        "localization": { "vi": {"prompt": (desc_vi or '').strip()}, "tgt": {"lang": lang_code, "prompt": (desc_tgt or desc_vi or '').strip()} }
    }
    return data

class _Worker(QObject):
    log = pyqtSignal(str)
    story_done = pyqtSignal(dict, dict)   # data, context (paths)
    job_card = pyqtSignal(dict)
    job_finished = pyqtSignal()

    def __init__(self, task, payload):
        super().__init__()
        self.task = task
        self.payload = payload

    def run(self):
        try:
            if self.task == "script":
                self._run_script()
            elif self.task == "video":
                self._run_video()
        except Exception as e:
            self.log.emit(f"[ERR] {e}")
        finally:
            if self.task == "video":
                self.job_finished.emit()

    def _run_script(self):
        p = self.payload
        self.log.emit("[INFO] Gọi LLM sinh kịch bản...")
        try:
            from services.llm_story_service import generate_script
        except Exception:
            from llm_story_service import generate_script
        data = generate_script(
            idea=p["idea"], style=p["style"], duration_seconds=p["duration"],
            provider=p["provider"], output_lang=p["out_lang_code"]
        )
        # auto-save to folders
        st = cfg.load()
        root = st.get("download_dir") or ""
        if not root:
            self.log.emit("[WARN] Chưa cấu hình thư mục tải về trong Cài đặt.")
        title = p["project"] or data.get("title_vi") or data.get("title_tgt") or "Project"
        prj_dir = os.path.join(root, title); os.makedirs(prj_dir, exist_ok=True)
        dir_script = os.path.join(prj_dir, "01_KichBan"); os.makedirs(dir_script, exist_ok=True)
        dir_prompts= os.path.join(prj_dir, "02_Prompts"); os.makedirs(dir_prompts, exist_ok=True)
        dir_videos = os.path.join(prj_dir, "03_Videos"); os.makedirs(dir_videos, exist_ok=True)

        try:
            with open(os.path.join(dir_script, "screenplay_vi.txt"), "w", encoding="utf-8") as f:
                f.write(data.get("screenplay_vi",""))
            with open(os.path.join(dir_script, "screenplay_tgt.txt"), "w", encoding="utf-8") as f:
                f.write(data.get("screenplay_tgt",""))
            with open(os.path.join(dir_script, "outline_vi.txt"), "w", encoding="utf-8") as f:
                f.write(data.get("outline_vi",""))
            with open(os.path.join(dir_script, "character_bible.json"), "w", encoding="utf-8") as f:
                json.dump(data.get("character_bible",[]), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log.emit(f"[WARN] Lưu kịch bản thất bại: {e}")

        ctx = {"title": title, "prj_dir": prj_dir, "dir_script": dir_script, "dir_prompts": dir_prompts, "dir_videos": dir_videos, "scenes": data.get("scenes",[])}
        self.log.emit("[INFO] Hoàn tất sinh kịch bản & lưu file.")
        self.story_done.emit(data, ctx)

    def _download(self, url, dst_path):
        try:
            import requests
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            with open(dst_path, "wb") as f:
                f.write(r.content)
            return True
        except Exception as e:
            self.log.emit(f"[ERR] Download fail: {e}")
            return False

    def _make_thumb(self, video_path, out_dir, scene, copy):
        try:
            os.makedirs(out_dir, exist_ok=True)
            thumb = os.path.join(out_dir, f"thumb_c{scene}_v{copy}.jpg")
            if shutil.which("ffmpeg"):
                cmd=["ffmpeg","-y","-ss","00:00:00","-i",video_path,"-frames:v","1","-q:v","3",thumb]
                subprocess.run(cmd, check=True)
                return thumb
        except Exception as e:
            self.log.emit(f"[WARN] Tạo thumbnail lỗi: {e}")
        return ""

    def _run_video(self):
        p = self.payload
        st = cfg.load()
        tokens = st.get("tokens") or []
        project_id = st.get("default_project_id") or DEFAULT_PROJECT_ID
        client = LabsClient(tokens, on_event=None)
        copies = p["copies"]
        title = p["title"]
        dir_videos = p["dir_videos"]
        up4k = p.get("upscale_4k", False)
        thumbs_dir = os.path.join(dir_videos, "thumbs")

        jobs = []
        for scene_idx, scene in enumerate(p["scenes"], start=1):
            ratio = scene["aspect"]
            model_key = p.get("model_key","")
            for copy_idx in range(1, copies+1):
                body = {"prompt": scene["prompt"], "copies": 1, "model": model_key, "aspect_ratio": ratio}
                self.log.emit(f"[INFO] Start scene {scene_idx} copy {copy_idx}…")
                rc = client.start_one(body, model_key, ratio, scene["prompt"], copies=1, project_id=project_id)
                card={"scene":scene_idx,"copy":copy_idx,"status":"PROCESSING","json":scene["prompt"],"url":"","path":"","thumb":"","dir":dir_videos}
                self.job_card.emit(card)
                if rc>0: jobs.append((card, body))
                else: card["status"]="FAILED_START"; self.job_card.emit(card)

        # polling
        for _ in range(120):
            if not jobs:
                break
            names=[op for (_,op) in jobs]
            rs = client.batch_check_operations(names)
            new_jobs=[]
            for (card, op) in jobs:
                v = rs.get(op) or {}
                stt = v.get('status') or 'PROCESSING'
                card['status']=stt
                self.job_card.emit(card)
                if stt in ('COMPLETED','DONE','DONE_NO_URL'):
                    url = (v.get('video_urls') or [None])[0]
                    if url:
                        fn=f"{title}_canh_{card['scene']}_video_{card['copy']}.mp4"
                        fp=os.path.join(dir_videos, fn)
                        if self._download(url, fp):
                            card['path']=fp; card['status']='DOWNLOADED'
                            th=self._make_thumb(fp, thumbs_dir, card['scene'], card['copy'])
                            if th: card['thumb']=th
                            self.job_card.emit(card)
                else:
                    new_jobs.append((card, op))
            jobs=new_jobs
            try:
                import time; time.sleep(5)
            except Exception: pass

        # 4K upscale

        if up4k:
            has_ffmpeg = shutil.which("ffmpeg") is not None
            if not has_ffmpeg:
                self.log.emit("[WARN] Không tìm thấy ffmpeg trong PATH — bỏ qua upscale 4K.")
            else:
                for (card, _) in jobs:
                    if card.get("path"):
                        src=card["path"]; dst=src.replace(".mp4","_4k.mp4")
                        cmd=["ffmpeg","-y","-i",src,"-vf","scale=3840:-2","-c:v","libx264","-preset","fast",dst]
                        try:
                            subprocess.run(cmd, check=True)
                            card["path"]=dst; card["status"]="UPSCALED_4K"; self.job_card.emit(card)
                        except Exception as e:
                            self.log.emit(f"[ERR] 4K upscale fail: {e}")
