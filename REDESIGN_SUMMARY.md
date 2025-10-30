# Video Bán Hàng - Redesign Summary

## 🎯 Overview

Complete redesign of the "Video Bán Hàng" tab with a new 3-step workflow and improved UI.

---

## 📊 What Changed

### New Files Created

1. **`services/llm_service.py`**
   - Wrapper for Gemini text generation API
   - Supports configurable temperature for creative output
   - Handles API key management

2. **`services/whisk_service.py`**
   - Google Labs Whisk (Image Remix) integration
   - Image upload functionality
   - Reference-based image generation (subject, style, scene)
   - Automatic fallback to Gemini on failure

3. **Enhanced `services/image_gen_service.py`**
   - Added `generate_image_gemini()` function
   - Implemented rate limiting (2.5s delay between requests)
   - Key rotation and retry logic
   - Handles 429 rate limit errors

4. **Enhanced `services/sales_script_service.py`**
   - Added social media content generation (3 versions)
   - New `_build_social_media_prompt()` function
   - Added `generate_thumbnail_with_text()` for text overlay
   - Returns `social_media` field in outline with:
     - Caption (with emojis)
     - Hashtags array
     - Thumbnail prompt
     - Text overlay
     - Platform and language metadata

5. **Completely Redesigned `ui/video_ban_hang_panel.py`**
   - 2-column layout (380px fixed + flexible)
   - 3-step workflow buttons
   - Social media tabs (3 versions)
   - Image thumbnail displays
   - Dark theme for results area

### Removed Files

- Old panel backed up and removed
- Temporary build artifacts cleaned

---

## 🎨 UI Changes

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │              │  │                                     │  │
│  │  LEFT COL    │  │         RIGHT COL (DARK)            │  │
│  │  (380px)     │  │         (Flexible)                  │  │
│  │  Light Blue  │  │                                     │  │
│  │              │  │  ┌─────────────────────────────┐   │  │
│  │  • Project   │  │  │ Social Media Tabs (3)       │   │  │
│  │  • Model     │  │  │  - Caption + Hashtags       │   │  │
│  │  • Product   │  │  │  - Thumbnail Preview        │   │  │
│  │  • Settings  │  │  └─────────────────────────────┘   │  │
│  │              │  │                                     │  │
│  │              │  │  ┌─────────────────────────────┐   │  │
│  │              │  │  │ Scene Results               │   │  │
│  │              │  │  │  - Preview cards            │   │  │
│  │              │  │  └─────────────────────────────┘   │  │
│  │              │  │                                     │  │
│  │              │  │  ┌─────────────────────────────┐   │  │
│  │              │  │  │ Processing Log              │   │  │
│  │              │  │  └─────────────────────────────┘   │  │
│  │              │  │                                     │  │
│  │              │  │  [📝 Viết KB] [🎨 Tạo ảnh] [🎬 Video] │
│  └──────────────┘  └────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Color Scheme

**Left Column (Settings):**
- Background: `#e8f4f8` (light blue)
- Group boxes: `#f0f8fc` (lighter blue)
- Borders: `#c5e1eb` (blue-gray)
- Buttons: `#0891b2` (cyan)

**Right Column (Results):**
- Background: `#1a202c` (dark gray)
- Cards: `#2d3748` (medium dark)
- Borders: `#4a5568` (gray)
- Text: `#e2e8f0` (light gray)
- Accent: `#60a5fa` (blue)

---

## 🔄 Workflow Changes

### Old Workflow (2 buttons)
1. "Viết kịch bản" → Generate script + preview images immediately
2. "Bắt đầu tạo video" → Generate videos

### New Workflow (3 steps)

#### Step 1: 📝 Viết kịch bản (Write Script)
**Input:**
- Project idea
- Product content
- Model description
- Settings (style, duration, platform)

**Output:**
- Detailed scene breakdown
- **3 Social Media versions** with:
  - Engaging caption (2-3 lines, emojis)
  - 5-8 relevant hashtags
  - Thumbnail prompt (9:16)
  - Text overlay for thumbnail
  - Platform and language tags

**UI Changes:**
- Displays 3 tabs for social versions
- Shows scene cards (no images yet)
- Enables "Tạo ảnh" button

#### Step 2: 🎨 Tạo ảnh (Generate Images)
**Input:**
- Script from Step 1
- Model reference images
- Product reference images
- Image model selection (Whisk/Gemini)

**Process:**
1. For each scene:
   - Try Whisk with reference images
   - Fallback to Gemini if Whisk fails
   - Apply 2.5s delay between requests (rate limiting)
2. For each social version:
   - Generate base thumbnail image
   - Add text overlay using Pillow

**Output:**
- Scene preview images (displayed in cards)
- 3 Thumbnail images with text overlay
- All images saved to project folder

**UI Changes:**
- Updates scene cards with preview images
- Updates social tabs with thumbnails
- Enables "Tạo video" button

#### Step 3: 🎬 Tạo video (Generate Videos)
**Input:**
- Scene images from Step 2
- Video prompts from Step 1
- Video settings

**Process:**
- Uses existing `sales_pipeline` infrastructure
- Uploads images to Labs API
- Creates video generation jobs
- Polls for completion
- Downloads final videos

**Output:**
- Video files saved to project folder

---

## 📦 New Features

### 1. Image Selection with Thumbnails

**Model Images:**
- Click "📁 Chọn ảnh người mẫu" button
- Select multiple images
- Displays first 5 as 60x60px thumbnails
- Shows "+N" badge if more than 5

**Product Images:**
- Click "📁 Chọn ảnh sản phẩm" button
- Select multiple images
- Same thumbnail display logic

### 2. Social Media Tabs

Each tab shows:
- **Caption:** Engaging text with emojis (editable, readonly)
- **Copy button:** One-click copy to clipboard
- **Hashtags:** Space-separated tags
- **Thumbnail:** 9:16 preview with text overlay (180x320px)
- **Metadata:** Platform, language automatically set

### 3. Scene Cards

Each scene displays:
- Scene number and title
- Scene description (truncated)
- Preview image placeholder
- Updates with generated image in Step 2

### 4. Video Settings Grid

Organized as 2 columns × 5 rows:
- Row 1: Script style | Image style
- Row 2: Script model | Image model
- Row 3: Voice ID | Language
- Row 4: Duration | Videos per scene
- Row 5: Aspect ratio | Platform

### 5. Processing Log

Real-time updates showing:
- Script generation progress
- Image generation status (Whisk/Gemini)
- Rate limiting delays
- Error messages
- Success confirmations

---

## 🔧 Technical Implementation

### Rate Limiting

```python
# Gemini API rate limit handling
def generate_image_with_rate_limit(prompt: str, delay: float = 2.5):
    time.sleep(delay)  # Wait 2.5s before request
    return generate_image_gemini(prompt)
```

Applied to:
- Scene image generation (delay between each)
- Thumbnail generation (cumulative delay)
- Prevents 429 errors

### Whisk Fallback Logic

```python
# Try Whisk first
try:
    img_data = whisk_service.generate_image(
        prompt=prompt,
        model_image=model_paths[0],
        product_image=product_paths[0]
    )
    log("Using Whisk ✓")
except:
    log("Whisk failed, fallback to Gemini...")
    img_data = None

# Fallback to Gemini
if img_data is None:
    img_data = image_gen_service.generate_image_with_rate_limit(prompt, 2.5)
    log("Using Gemini ✓")
```

### Thumbnail Text Overlay

```python
# Using Pillow for text overlay
from PIL import Image, ImageDraw, ImageFont

def generate_thumbnail_with_text(base_image_path, text, output_path):
    img = Image.open(base_image_path)
    draw = ImageDraw.Draw(img)
    
    # Load font (with fallbacks)
    font = ImageFont.truetype("/path/to/font.ttf", 40)
    
    # Draw semi-transparent background
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw.rectangle(bg_bbox, fill=(0, 0, 0, 180))
    
    # Composite and draw text
    img = Image.alpha_composite(img, overlay)
    draw.text((x, y), text.upper(), font=font, fill=(255, 255, 255))
    
    img.save(output_path)
```

### Worker Thread Architecture

```python
class ImageGenerationWorker(QThread):
    progress = pyqtSignal(str)
    scene_image_ready = pyqtSignal(int, bytes)
    thumbnail_ready = pyqtSignal(int, bytes)
    finished = pyqtSignal(bool)
    
    def run(self):
        # Generate scene images
        for scene in scenes:
            img_data = generate_with_rate_limit(...)
            self.scene_image_ready.emit(scene_idx, img_data)
        
        # Generate thumbnails
        for version in social_versions:
            base_img = generate_image(...)
            final_img = add_text_overlay(base_img, text)
            self.thumbnail_ready.emit(version_idx, final_img)
```

---

## ✅ Testing Results

### Unit Tests

1. **UI Creation Test** ✅
   - Panel instantiation
   - Widget presence verification
   - Initial button states
   - Tab count verification

2. **Script Structure Test** ✅
   - Scene count calculation
   - JSON sanitization
   - Prompt generation
   - Social media prompt

3. **Thumbnail Generation Test** ✅
   - Text overlay rendering
   - Image size preservation
   - Output file creation
   - Pillow integration

### Test Command
```bash
python3 /tmp/test_ui.py
python3 /tmp/test_script_gen.py
python3 /tmp/test_thumbnail.py
```

All tests pass successfully! ✅

---

## 📋 Requirements Met

### From Problem Statement

- ✅ **Workflow mới (3 bước tách biệt)**
  - ✅ Bước 1: Viết kịch bản (3 phiên bản social)
  - ✅ Bước 2: Tạo ảnh (scene + thumbnail với text)
  - ✅ Bước 3: Tạo video (từ ảnh đã tạo)

- ✅ **UI mới (2 cột)**
  - ✅ Cột 1: Light Blue (380px fixed)
  - ✅ Cột 2: Dark theme (flexible width)
  - ✅ Social Media tabs (3 versions)
  - ✅ Grid 2x5 settings
  - ✅ Thumbnails 60x60px, max 5 + "+N"

- ✅ **Tích hợp Whisk**
  - ✅ Upload ảnh → mediaGenerationId
  - ✅ runImageRecipe API
  - ✅ Fallback to Gemini

- ✅ **Fix UI Issues**
  - ✅ Button handlers connected
  - ✅ Thumbnail display working
  - ✅ Gemini rate limit (2.5s delay)
  - ✅ Settings grid layout

- ✅ **LLM Output mới**
  - ✅ outline_vi field
  - ✅ scenes array with index, desc, speech, emotion, duration
  - ✅ social_media with versions array
  - ✅ Each version: caption, hashtags, thumbnail_prompt, text_overlay

---

## 🚀 Usage Guide

### Starting the Application

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API keys in settings tab

3. Open "Video Bán Hàng" tab

### Workflow

1. **Fill Project Info:**
   - Project name (auto-generated if empty)
   - Main idea (2-3 lines)
   - Product content/features

2. **Select Images:**
   - Click "📁 Chọn ảnh người mẫu" for model photos
   - Click "📁 Chọn ảnh sản phẩm" for product photos
   - Thumbnails appear below buttons

3. **Configure Settings:**
   - Script style (Viral/KOC/Story)
   - Image style (Cinematic/Modern/Anime/3D)
   - Models (Gemini/Whisk)
   - Duration, ratio, platform

4. **Generate Script:**
   - Click "📝 Viết kịch bản"
   - Wait for completion
   - Review 3 social media versions in tabs
   - Check scene cards

5. **Generate Images:**
   - Click "🎨 Tạo ảnh" (enabled after script)
   - Watch progress in log
   - Images appear in scene cards
   - Thumbnails appear in social tabs
   - Note: 2.5s delay between each image

6. **Generate Video:**
   - Click "🎬 Tạo video" (enabled after images)
   - Videos created using scene images
   - Download from project folder

---

## 📝 Notes

- All files saved to: `~/Downloads/{project_name}/`
- Scene images: `Ảnh xem trước/scene_{N}.png`
- Thumbnails: `Ảnh xem trước/thumbnail_v{N}.png`
- Videos: `Video/scene_{N}_copy_{M}.mp4`
- Logs: `nhat_ky_xu_ly.log`

- Gemini image API endpoint may need adjustment based on availability
- Whisk requires valid Google API keys
- Rate limiting is mandatory to avoid 429 errors
- Text overlay uses system fonts with fallback to default

---

## 🔮 Future Enhancements

Potential improvements for next version:

1. **Custom font upload** for thumbnail text
2. **Template selection** for social media layouts
3. **A/B testing** for multiple caption variations
4. **Direct social media posting** integration
5. **Video preview** before final generation
6. **Batch processing** multiple projects
7. **Analytics** for performance tracking

---

## 📄 License & Credits

This redesign implements the specification from the problem statement while maintaining compatibility with existing Video2Video functionality.

**Last Updated:** 2025-10-30
