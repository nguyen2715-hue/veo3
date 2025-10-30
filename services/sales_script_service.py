# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import datetime, json, re
from services.gemini_client import GeminiClient, MissingAPIKey

def _scene_count(total_sec:int)->int:
    return max(1, (int(total_sec)+8-1)//8)

def _json_sanitize(raw:str)->str:
    s = raw.find("{"); e = raw.rfind("}")
    if s != -1 and e != -1 and e > s:
        return raw[s:e+1]
    return raw

def _try_parse_json(raw:str)->Dict[str,Any]:
    raw = _json_sanitize(raw)
    try:
        return json.loads(raw)
    except Exception:
        raw = raw.replace("```json","").replace("```","")
        return json.loads(_json_sanitize(raw))

def _models_description(first_model_json:str)->str:
    return first_model_json if first_model_json else "No specific models described."

def _images_refs(has_model:bool, product_count:int)->str:
    out=[]
    if has_model: out.append("- An image is provided with source reference 'model-1'")
    for i in range(product_count): out.append(f"- An image is provided with source reference 'product-{i+1}'")
    return "\\n".join(out)

def _build_system_prompt(cfg:Dict[str,Any], sceneCount:int, models_json:str, product_count:int)->str:
    visualStyleString = cfg.get("image_style") or "Cinematic"
    idea = cfg.get("idea") or ""
    content = cfg.get("product_main") or ""
    duration = int(cfg.get("duration_sec") or 0)
    scriptStyle = cfg.get("script_style") or "story-telling"
    languageCode = cfg.get("speech_lang") or "vi"
    aspectRatio = cfg.get("ratio") or "9:16"
    voiceId = cfg.get("voice_id") or "ElevenLabs_VoiceID"
    imagesList = _images_refs(bool(models_json.strip()), product_count)

    return f"""
Objective: Create a detailed video script in JSON format. The output MUST be a valid JSON object with a "scenes" key containing an array of scene objects. The entire script, including all descriptions and voiceovers, MUST be in the language specified by the languageCode ({languageCode}).

Video Idea: {idea}
Core Content: {content}
Total Duration: Approximately {duration} seconds.
Script Style: {scriptStyle}
Visual Style: {visualStyleString}
Setting/Background Generation: You MUST invent a suitable and compelling setting/background for the video based on the idea, content, and characters. The setting must be consistent with the overall theme.
Models/Characters:
{_models_description(models_json)}

Reference Images:
{imagesList if imagesList else '- No reference images provided.'}

Task Instructions:
1.  Analyze all provided information.
2.  Break down the video into exactly {sceneCount} distinct scenes for the {duration}-second duration.
3.  For each scene, provide a concise description in the target language ({languageCode}).
4.  Create a separate voiceover field containing the dialogue/narration in the target language ({languageCode}). This field MUST include descriptive audio tags in square brackets to guide the text-to-speech model. The tags should also be in the target language if appropriate (e.g., for actions like [cười], [khóc]). This is a critical requirement.
    Available Audio Tags (Adapt these to the target language for the voiceover):
    {{
      "emotion_tags": {{"happy": "[vui vẻ]", "excited": "[hào hứng]", "sad": "[buồn bã]", "angry": "[tức giận]", "surprised": "[ngạc nhiên]", "disappointed": "[thất vọng]", "scared": "[sợ hãi]", "confident": "[tự tin]", "nervous": "[lo lắng]", "crying": "[khóc]", "laughs": "[cười]", "sighs": "[thở dài]"}},
      "tone_tags": {{"whispers": "[thì thầm]", "shouts": "[hét lên]", "sarcastic": "[mỉa mai]", "dramatic_tone": "[giọng kịch tính]", "reflective": "[suy tư]", "gentle_voice": "[giọng nhẹ nhàng]", "serious_tone": "[giọng nghiêm túc]"}},
      "style_tags": {{"storytelling": "[giọng kể chuyện]", "advertisement": "[giọng quảng cáo]"}},
      "timing_tags": {{"pause": "[ngừng lại]", "hesitates": "[do dự]", "rushed": "[vội vã]", "slows_down": "[chậm lại]"}},
      "action_tags": {{"clears_throat": "[hắng giọng]", "gasp": "[thở hổn hển]"}}
    }}
5.  The voicer field MUST be set to this exact value: {voiceId}.
6.  The languageCode field MUST be set to {languageCode}.
7.  Generate a detailed prompt object for a text-to-video AI model.
8.  The prompt.Output_Format.Structure must be filled with specific details (English):
    - character_details: reference image ('model-1') + EXACT clothing/hairstyle/gender from Models/Characters.
    - setting_details, key_action (may reference 'product-1'), camera_direction.
    - original_language_dialogue: copy top-level voiceover without audio tags (in {languageCode}).
    - dialogue_or_voiceover: English translation of the original dialogue.
9.  Audio tags appear ONLY in the top-level voiceover.
10. Output ONLY a valid JSON object. No extra text.

Output Format (Strictly Adhere):
{{
  "scenes": [
    {{
      "scene": 1,
      "description": "A short summary of the scene, in the target language.",
      "voiceover": "[emotion][pause] sample voiceover in target language.",
      "voicer": "{voiceId}",
      "languageCode": "{languageCode}",
      "prompt": {{
        "Objective": "Generate a short video clip for this scene.",
        "Persona": {{
          "Role": "Creative Video Director",
          "Tone": "Cinematic and evocative",
          "Knowledge_Level": "Expert in visual storytelling"
        }},
        "Task_Instructions": [
          "Create a video clip lasting approximately {{round({duration} / {sceneCount})}} seconds."
        ],
        "Constraints": [
          "Aspect ratio: {aspectRatio}",
          "Visual style: {visualStyleString}"
        ],
        "Input_Examples": [],
        "Output_Format": {{
          "Type": "JSON",
          "Structure": {{
            "character_details": "In English...",
            "setting_details": "In English...",
            "key_action": "In English...",
            "camera_direction": "In English...",
            "original_language_dialogue": "In {languageCode}, no audio tags.",
            "dialogue_or_voiceover": "In English translation."
          }}
        }}
      }}
    }}
  ]
}}
""".strip()

def _build_image_prompt(struct:Dict[str,Any], visualStyleString:str)->str:
    camera = (struct or {}).get("camera_direction","")
    setting = (struct or {}).get("setting_details","")
    character = (struct or {}).get("character_details","")
    action = (struct or {}).get("key_action","")
    return f"""Objective: Generate ONE SINGLE photorealistic, high-quality preview image for a video scene, meticulously following all instructions. The output MUST be a single, unified image.

--- SCENE COMPOSITION ---
- Overall Style: {visualStyleString}.
- Camera & Shot: {camera}.
- Setting: {setting}.
- Character & Clothing: {character}.
- Key Action: {action}.

--- ABSOLUTE, NON-NEGOTIABLE RULES ---
1. SINGLE IMAGE OUTPUT (CRITICAL): The output MUST be ONE single, coherent image. NO collages, grids, split-screens, or multi-panel images are allowed under any circumstances.
2. CHARACTER FIDELITY: The character's clothing, hairstyle, and gender MUST PERFECTLY and EXACTLY match the description provided in the scene composition. This OVERRIDES ALL other instructions.
3. NO TEXT OR WATERMARKS: The image MUST be 100% free of any text, letters, words, subtitles, captions, logos, watermarks, or any form of typography.

--- NEGATIVE PROMPT (Elements to strictly AVOID) ---
- collage, grid, multiple panels, multi-panel, split screen, diptych, triptych, multiple frames.
- text, words, letters, logos, watermarks, typography, signatures, labels, captions, subtitles.
- cartoon, illustration, drawing, sketch, anime, 3d render.
""".strip()

def build_outline(cfg:Dict[str,Any])->Dict[str,Any]:
    sceneCount = _scene_count(int(cfg.get("duration_sec") or 0))
    models_json = cfg.get("first_model_json") or ""
    product_count = int(cfg.get("product_count") or 0)
    client = GeminiClient()
    sys_prompt = _build_system_prompt(cfg, sceneCount, models_json, product_count)
    raw = client.generate(sys_prompt, "Return ONLY the JSON object. No prose.", timeout=240)
    script_json = _try_parse_json(raw)

    scenes = script_json.get("scenes", [])
    if not isinstance(scenes, list): scenes = []
    if len(scenes) > sceneCount: scenes = scenes[:sceneCount]
    if len(scenes) < sceneCount:
        base_lang = cfg.get("speech_lang") or "vi"
        voiceId = cfg.get("voice_id") or "ElevenLabs_VoiceID"
        for i in range(len(scenes)+1, sceneCount+1):
            scenes.append({"scene": i, "description": "", "voiceover": "", "voicer": voiceId, "languageCode": base_lang,
                           "prompt":{"Output_Format":{"Structure": {"character_details":"","setting_details":"","key_action":"","camera_direction":"","original_language_dialogue":"","dialogue_or_voiceover":""}}}})
    script_json["scenes"] = scenes

    visualStyleString = cfg.get("image_style") or "Cinematic"
    outline_scenes = []
    for sc in scenes:
        struct = (((sc or {}).get("prompt",{}) or {}).get("Output_Format",{}) or {}).get("Structure",{}) or {}
        img_prompt = _build_image_prompt(struct, visualStyleString)
        outline_scenes.append({
            "index": sc.get("scene"),
            "title": f"Cảnh {sc.get('scene')}",
            "desc": sc.get("description",""),
            "speech": sc.get("voiceover",""),
            "prompt_video": json.dumps(sc.get("prompt",{}), ensure_ascii=False),
            "prompt_image": img_prompt
        })

    return {
        "meta": {"created_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), "scenes": len(outline_scenes),
                 "ratio": cfg.get("ratio") or "9:16"},
        "script_json": script_json,
        "scenes": outline_scenes,
        "screenplay_text": json.dumps(script_json, ensure_ascii=False, indent=2)
    }
