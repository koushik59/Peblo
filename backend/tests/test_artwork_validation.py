"""
Tests for artwork validation service.

Tests the highest-risk validation logic:
- File type validation
- File size validation (200 KB limit)
- Dimension range validation
- Aspect ratio validation
- Human-readable error messages
"""
import io
import pytest
from PIL import Image
from app.services.artwork_service import validate_artwork


def _make_jpeg(width: int, height: int, quality: int = 60) -> bytes:
    """Generate a test JPEG image."""
    img = Image.new("RGB", (width, height), (100, 100, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_png(width: int, height: int) -> bytes:
    """Generate a test PNG image."""
    img = Image.new("RGB", (width, height), (100, 100, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestArtworkValidation:
    """Test artwork validation against reference spec."""

    # --- Valid images ---

    def test_valid_poster(self):
        data = _make_jpeg(600, 900)
        valid, error, dims = validate_artwork(data, "image/jpeg", "poster", "test.jpg")
        assert valid is True
        assert error is None
        assert dims == (600, 900)

    def test_valid_banner(self):
        data = _make_jpeg(1280, 720)
        valid, error, dims = validate_artwork(data, "image/jpeg", "banner", "test.jpg")
        assert valid is True
        assert error is None
        assert dims == (1280, 720)

    def test_valid_thumbnail(self):
        data = _make_jpeg(640, 360)
        valid, error, dims = validate_artwork(data, "image/jpeg", "thumbnail", "test.jpg")
        assert valid is True
        assert error is None
        assert dims == (640, 360)

    def test_valid_png_poster(self):
        data = _make_png(600, 900)
        valid, error, dims = validate_artwork(data, "image/png", "poster", "test.png")
        assert valid is True

    # --- Invalid file type ---

    def test_invalid_file_type_gif(self):
        data = _make_jpeg(600, 900)
        valid, error, dims = validate_artwork(data, "image/gif", "poster", "test.gif")
        assert valid is False
        assert "GIF" in error
        assert "supported format" in error.lower()

    def test_invalid_file_type_svg(self):
        data = b"<svg></svg>"
        valid, error, dims = validate_artwork(data, "image/svg+xml", "banner", "test.svg")
        assert valid is False

    # --- File size ---

    def test_file_too_large(self):
        # Create a large image by generating a big JPEG
        img = Image.new("RGB", (1280, 720), (100, 100, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=100)
        # Pad to exceed 200 KB
        large_data = buf.getvalue() + b"\x00" * (210 * 1024)
        valid, error, dims = validate_artwork(large_data, "image/jpeg", "banner", "large.jpg")
        assert valid is False
        assert "200 KB" in error or "200" in error

    # --- Dimensions ---

    def test_poster_too_small(self):
        data = _make_jpeg(200, 300)  # Below min_width of 400
        valid, error, dims = validate_artwork(data, "image/jpeg", "poster", "tiny.jpg")
        assert valid is False
        assert "minimum width" in error.lower() or "400" in error

    def test_banner_too_large_dimensions(self):
        data = _make_jpeg(2560, 1440)  # Above max_width of 1920
        valid, error, dims = validate_artwork(data, "image/jpeg", "banner", "huge.jpg")
        assert valid is False
        assert "maximum width" in error.lower() or "1920" in error

    def test_thumbnail_too_small(self):
        data = _make_jpeg(160, 90)  # Below min_width of 320
        valid, error, dims = validate_artwork(data, "image/jpeg", "thumbnail", "tiny_thumb.jpg")
        assert valid is False
        assert "minimum width" in error.lower()

    # --- Aspect ratio ---

    def test_poster_wrong_aspect_ratio_square(self):
        data = _make_jpeg(600, 600)  # 1:1 instead of 2:3
        valid, error, dims = validate_artwork(data, "image/jpeg", "poster", "square.jpg")
        assert valid is False
        assert "2:3" in error
        assert "600" in error and "600" in error

    def test_banner_wrong_aspect_ratio_square(self):
        data = _make_jpeg(1280, 1280)  # 1:1 instead of 16:9
        valid, error, dims = validate_artwork(data, "image/jpeg", "banner", "square_banner.jpg")
        assert valid is False
        assert "16:9" in error

    def test_poster_wrong_aspect_ratio_landscape(self):
        data = _make_jpeg(900, 600)  # Landscape instead of portrait
        valid, error, dims = validate_artwork(data, "image/jpeg", "poster", "landscape.jpg")
        assert valid is False
        assert "2:3" in error

    # --- Edge cases ---

    def test_unknown_artwork_type(self):
        data = _make_jpeg(600, 900)
        valid, error, dims = validate_artwork(data, "image/jpeg", "icon", "test.jpg")
        assert valid is False
        assert "Unknown artwork type" in error

    def test_corrupted_image(self):
        data = b"not an image at all"
        valid, error, dims = validate_artwork(data, "image/jpeg", "poster", "bad.jpg")
        assert valid is False
        assert "could not be opened" in error.lower()

    def test_empty_file(self):
        valid, error, dims = validate_artwork(b"", "image/jpeg", "poster", "empty.jpg")
        assert valid is False

    # --- Human-readable errors ---

    def test_error_messages_are_readable(self):
        """Verify error messages are suitable for non-technical editors."""
        data = _make_jpeg(1200, 1200)
        valid, error, dims = validate_artwork(data, "image/jpeg", "banner", "wrong.jpg")
        assert valid is False
        # Should mention actual dimensions
        assert "1200" in error
        # Should mention expected aspect ratio
        assert "16:9" in error
        # Should suggest correct size
        assert "1280" in error

    def test_poster_within_tolerance(self):
        """A poster slightly off the exact 2:3 ratio but within tolerance should pass."""
        # 2:3 ratio = 0.6667. With 5% tolerance, 0.633 to 0.700 should pass.
        # 600x910 = 0.659 -> within tolerance
        data = _make_jpeg(600, 910)
        valid, error, dims = validate_artwork(data, "image/jpeg", "poster", "close.jpg")
        assert valid is True

    def test_banner_within_tolerance(self):
        """A banner slightly off the exact 16:9 ratio but within tolerance should pass."""
        # 16:9 = 1.7778. With 5% tolerance, 1.689 to 1.867 should pass.
        # 1280x700 = 1.828 -> within tolerance
        data = _make_jpeg(1280, 700)
        valid, error, dims = validate_artwork(data, "image/jpeg", "banner", "close.jpg")
        assert valid is True
