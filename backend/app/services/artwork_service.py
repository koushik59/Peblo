"""
Artwork validation service.

Validates uploaded images against the reference specification:
- File type (JPEG, PNG, WebP)
- File size (max 200 KB)
- Dimensions (within min/max width range)
- Aspect ratio (within tolerance)

Returns human-readable error messages suitable for content editors.
"""
import io
import json
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

# Load reference spec
def _find_file(filename: str) -> Path:
    candidates = [
        Path(filename),
        Path("/" + filename),
        Path("/app") / filename,
        Path(__file__).parent.parent.parent / filename,
        Path(__file__).parent.parent.parent.parent / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(filename)

REFERENCE_PATH = _find_file("reference.json")
_reference = None


def get_reference() -> dict:
    global _reference
    if _reference is None:
        if REFERENCE_PATH.exists():
            with open(REFERENCE_PATH) as f:
                _reference = json.load(f)
        else:
            # Fallback defaults matching challenge spec
            _reference = {
                "artwork_specs": {
                    "poster": {
                        "width": 600, "height": 900, "aspect_ratio": "2:3",
                        "aspect_tolerance": 0.05, "min_width": 400, "max_width": 1200,
                        "max_file_size_kb": 200,
                        "allowed_formats": ["image/jpeg", "image/png", "image/webp"]
                    },
                    "banner": {
                        "width": 1280, "height": 720, "aspect_ratio": "16:9",
                        "aspect_tolerance": 0.05, "min_width": 960, "max_width": 1920,
                        "max_file_size_kb": 200,
                        "allowed_formats": ["image/jpeg", "image/png", "image/webp"]
                    },
                    "thumbnail": {
                        "width": 640, "height": 360, "aspect_ratio": "16:9",
                        "aspect_tolerance": 0.05, "min_width": 320, "max_width": 1280,
                        "max_file_size_kb": 200,
                        "allowed_formats": ["image/jpeg", "image/png", "image/webp"]
                    },
                }
            }
    return _reference


def parse_aspect_ratio(ratio_str: str) -> float:
    """Parse '16:9' to a float ratio."""
    parts = ratio_str.split(":")
    return float(parts[0]) / float(parts[1])


def validate_artwork(
    file_data: bytes,
    content_type: str,
    artwork_type: str,
    filename: str = "uploaded file",
) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
    """
    Validate an artwork file against the reference specification.

    Returns:
        (is_valid, error_message, (width, height))
        If invalid, error_message contains a human-readable explanation.
    """
    ref = get_reference()
    specs = ref["artwork_specs"]

    if artwork_type not in specs:
        return False, f"Unknown artwork type '{artwork_type}'. Valid types are: poster, banner, thumbnail.", None

    spec = specs[artwork_type]
    allowed_formats = spec.get("allowed_formats", ["image/jpeg", "image/png", "image/webp"])
    max_size_kb = spec.get("max_file_size_kb", 200)
    target_w = spec["width"]
    target_h = spec["height"]
    aspect_str = spec["aspect_ratio"]
    tolerance = spec.get("aspect_tolerance", 0.05)
    min_w = spec.get("min_width", 320)
    max_w = spec.get("max_width", 1920)

    # 1. File type
    if content_type not in allowed_formats:
        format_names = [f.split("/")[1].upper() for f in allowed_formats]
        return (
            False,
            f"'{filename}' is a {content_type.split('/')[1].upper()} file, but {artwork_type}s "
            f"must be one of: {', '.join(format_names)}. Please upload an image in a supported format.",
            None,
        )

    # 2. File size
    file_size_kb = len(file_data) / 1024
    if file_size_kb > max_size_kb:
        return (
            False,
            f"'{filename}' is {file_size_kb:.1f} KB, but the maximum allowed size for {artwork_type}s "
            f"is {max_size_kb} KB. Please compress or resize the image.",
            None,
        )

    # 3. Open image and check dimensions
    try:
        img = Image.open(io.BytesIO(file_data))
        width, height = img.size
    except Exception:
        return False, f"'{filename}' could not be opened as an image. Please upload a valid image file.", None

    # 4. Dimension range
    if width < min_w:
        return (
            False,
            f"This {artwork_type} is {width}×{height}, but the minimum width is {min_w}px. "
            f"Please upload a larger image (recommended: {target_w}×{target_h}).",
            (width, height),
        )
    if width > max_w:
        return (
            False,
            f"This {artwork_type} is {width}×{height}, but the maximum width is {max_w}px. "
            f"Please upload a smaller image (recommended: {target_w}×{target_h}).",
            (width, height),
        )

    # 5. Aspect ratio
    target_ratio = parse_aspect_ratio(aspect_str)
    actual_ratio = width / height
    relative_diff = abs(actual_ratio - target_ratio) / target_ratio
    if relative_diff > tolerance:
        return (
            False,
            f"This {artwork_type} is {width}×{height} (ratio {actual_ratio:.2f}), "
            f"but {artwork_type}s must use a {aspect_str} aspect ratio (ratio {target_ratio:.2f}). "
            f"Please upload an image closer to {target_w}×{target_h}.",
            (width, height),
        )

    return True, None, (width, height)
