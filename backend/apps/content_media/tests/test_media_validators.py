from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from apps.content_media.validators import (
    MAX_FILE_SIZES,
    validate_content_media,
)


class ContentMediaValidatorTests(SimpleTestCase):
    """Test content media validation and file identification."""

    def create_image(self, image_format="JPEG", name="image.jpg"):
        buffer = BytesIO()
        Image.new("RGB", (20, 20), color="white").save(
            buffer,
            format=image_format,
        )

        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type="application/octet-stream",
        )

    def test_valid_jpeg_is_identified_correctly(self):
        uploaded_file = self.create_image("JPEG")

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["category"], "IMAGE")
        self.assertEqual(result["mime_type"], "image/jpeg")
        self.assertEqual(result["extension"], ".jpg")

    def test_valid_png_is_identified_correctly(self):
        uploaded_file = self.create_image("PNG", "image.png")

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["category"], "IMAGE")
        self.assertEqual(result["mime_type"], "image/png")
        self.assertEqual(result["extension"], ".png")

    def test_valid_webp_is_identified_correctly(self):
        uploaded_file = self.create_image("WEBP", "image.webp")

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["category"], "IMAGE")
        self.assertEqual(result["mime_type"], "image/webp")
        self.assertEqual(result["extension"], ".webp")

    def test_valid_mp4_signature_is_identified(self):
        uploaded_file = SimpleUploadedFile(
            "video.mp4",
            b"\x00\x00\x00\x18ftypisom" + b"\x00" * 20,
        )

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["category"], "VIDEO")
        self.assertEqual(result["mime_type"], "video/mp4")

    def test_valid_webm_signature_is_identified(self):
        uploaded_file = SimpleUploadedFile(
            "video.webm",
            b"\x1a\x45\xdf\xa3" + b"\x00" * 20,
        )

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["category"], "VIDEO")
        self.assertEqual(result["mime_type"], "video/webm")

    def test_valid_pdf_signature_is_identified(self):
        uploaded_file = SimpleUploadedFile(
            "document.pdf",
            b"%PDF-1.7\n" + b"sample document content",
        )

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["category"], "DOCUMENT")
        self.assertEqual(result["mime_type"], "application/pdf")
        self.assertEqual(result["extension"], ".pdf")

    def test_empty_file_is_rejected(self):
        uploaded_file = SimpleUploadedFile("empty.pdf", b"")

        with self.assertRaises(ValidationError):
            validate_content_media(uploaded_file)

    def test_missing_file_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_content_media(None)

    def test_unknown_file_signature_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "unknown.bin",
            b"This is not a supported file.",
        )

        with self.assertRaises(ValidationError):
            validate_content_media(uploaded_file)

    def test_invalid_image_content_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "fake.jpg",
            b"\xff\xd8\xff" + b"invalid image content",
        )

        with self.assertRaises(ValidationError):
            validate_content_media(uploaded_file)

    def test_filename_path_is_sanitised(self):
        uploaded_file = self.create_image(
            "JPEG",
            "../../private/image.jpg",
        )

        result = validate_content_media(uploaded_file)

        self.assertEqual(result["original_filename"], "image.jpg")

    def test_file_pointer_is_reset_after_validation(self):
        uploaded_file = self.create_image()

        validate_content_media(uploaded_file)

        self.assertEqual(uploaded_file.tell(), 0)

    def test_image_size_limit_is_ten_megabytes(self):
        self.assertEqual(
            MAX_FILE_SIZES["IMAGE"],
            10 * 1024 * 1024,
        )

    def test_video_size_limit_is_one_hundred_megabytes(self):
        self.assertEqual(
            MAX_FILE_SIZES["VIDEO"],
            100 * 1024 * 1024,
        )

    def test_document_size_limit_is_twenty_megabytes(self):
        self.assertEqual(
            MAX_FILE_SIZES["DOCUMENT"],
            20 * 1024 * 1024,
        )

    def test_oversized_pdf_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "large.pdf",
            b"%PDF-" + b"\x00" * (MAX_FILE_SIZES["DOCUMENT"] + 1),
        )

        with self.assertRaises(ValidationError):
            validate_content_media(uploaded_file)

    def test_oversized_video_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "large.mp4",
            b"\x00\x00\x00\x18ftyp" + b"\x00" * (MAX_FILE_SIZES["VIDEO"] + 1),
        )

        with self.assertRaises(ValidationError):
            validate_content_media(uploaded_file)

    def test_image_exceeding_pixel_limit_is_rejected(self):
        buffer = BytesIO()

        Image.new("RGB", (7000, 6000)).save(
            buffer,
            format="JPEG",
        )

        uploaded_file = SimpleUploadedFile(
            "oversized-image.jpg",
            buffer.getvalue(),
        )

        with self.assertRaises(ValidationError):
            validate_content_media(uploaded_file)
