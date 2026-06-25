"""
Camera Utilities
Capture geotagged landscape photos and burn labels onto them.
"""
import os
import io
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

PHOTO_DIR = Path(os.path.expanduser('~')) / '.cropsurvey' / 'photos'
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


def take_photo(index: int = 1) -> Optional[str]:
    """
    Use Plyer Camera to capture a photo.
    Returns the saved file path or None on failure.
    Photos are forced to landscape orientation.
    """
    filename = PHOTO_DIR / f"photo_{index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    try:
        from plyer import camera
        camera.take_picture(
            filename=str(filename),
            on_complete=lambda path: logger.info(f"Photo captured: {path}")
        )
        return str(filename)
    except Exception as e:
        logger.error(f"Camera error: {e}")
        return None


def add_geotag_overlay(
    image_path: str,
    latitude: float,
    longitude: float,
    date_time: str,
    crop_name: str,
    save_path: Optional[str] = None
) -> Optional[str]:
    """
    Burn location, date-time, and crop name as a text overlay onto the photo.
    Ensures landscape orientation (rotates if needed).
    Returns the path of the labelled image.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ExifTags
        import PIL

        img = Image.open(image_path)

        # ── Force landscape ──────────────────────────────────────────────────
        try:
            for tag, val in img._getexif().items():
                if ExifTags.TAGS.get(tag) == 'Orientation':
                    if val == 6:
                        img = img.rotate(-90, expand=True)
                    elif val == 8:
                        img = img.rotate(90, expand=True)
                    break
        except Exception:
            pass

        if img.height > img.width:
            img = img.rotate(90, expand=True)

        draw = ImageDraw.Draw(img)
        label_lines = [
            f"Lat: {latitude:.6f}  Lon: {longitude:.6f}",
            f"Date: {date_time}",
            f"Crop: {crop_name}",
        ]

        # Try to load a monospace font; fall back to default
        font = None
        try:
            font_size = max(24, img.width // 40)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                                       font_size)
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                pass

        margin   = 10
        line_h   = 30 if font is None else font_size + 6
        box_h    = len(label_lines) * line_h + margin * 2
        box_top  = img.height - box_h - margin

        # Semi-transparent black background for readability
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ov_draw  = ImageDraw.Draw(overlay)
        ov_draw.rectangle(
            [(margin, box_top), (img.width - margin, img.height - margin)],
            fill=(0, 0, 0, 160)
        )
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

        for i, line in enumerate(label_lines):
            y = box_top + margin + i * line_h
            draw.text((margin * 2, y), line, fill=(255, 255, 255), font=font)

        out_path = save_path or image_path.replace('.jpg', '_labelled.jpg')
        img.save(out_path, 'JPEG', quality=90)
        logger.info(f"Geotagged photo saved: {out_path}")
        return out_path

    except ImportError:
        logger.warning("Pillow not installed; photo labels skipped")
        return image_path
    except Exception as e:
        logger.error(f"Photo overlay error: {e}")
        return image_path


def image_to_b64(path: str) -> Optional[str]:
    """Read an image file and return its base64-encoded content."""
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Could not encode image {path}: {e}")
        return None
