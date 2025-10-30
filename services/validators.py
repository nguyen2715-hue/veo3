# -*- coding: utf-8 -*-
from typing import Dict, List, Any

def validate_video_job(job:Dict[str,Any]) -> List[str]:
    errs = []
    prompt = (job.get("prompt") or "").strip()
    if not prompt:
        errs.append("Thiếu prompt (mô tả nội dung).")
    width = int(job.get("width") or 0)
    height = int(job.get("height") or 0)
    if not (width and height):
        errs.append("Thiếu kích thước video (width/height).")
    if width and height and (width % 16 != 0 or height % 16 != 0):
        errs.append("Kích thước phải chia hết cho 16 (yêu cầu codec).")
    fps = int(job.get("fps") or 0)
    if fps and fps not in (8, 12, 15, 16, 20, 24, 25, 30):
        errs.append("FPS không hợp lệ (chỉ chấp nhận 8,12,15,16,20,24,25,30).")
    dur = float(job.get("duration") or 0)
    if dur and (dur <= 0 or dur > 10.0):
        errs.append("Thời lượng không hợp lệ (0 < duration ≤ 10s).")
    project_id = (job.get("project_id") or "").strip()
    if not project_id:
        errs.append("Thiếu Project ID cho Flow.")
    return errs
