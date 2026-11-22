import warnings

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_FILE_SIZES = {
    "IMAGE": 10 * 1024 * 1024,
    "VIDEO": 100 * 1024 * 1024,
    "DOCUMENT": 20 * 1024 * 1024,
}

MAX_IMAGE_PIXELS = 40_000_000

ALLOWED_IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}

PDF_SIGNATURE = b"%PDF-"

IMAGE_SIGNATURES = (
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
)


def _sanitise_filename(filename):
    """Return a safe filename for display and audit metadata."""

    filename = str(filename or "uploaded-file")
    filename = filename.replace("\\", "/")
    filename = filename.rsplit("/", 1)[-1]
    filename = "".join(
        character for character in filename if character.isprintable()
    ).strip()

    if not filename or len(filename) > 255:
        raise ValidationError({"file": "Invalid filename."})

    return filename


def _has_image_signature(header):
    """Identify supported image formats from their file signatures."""

    return any(header.startswith(signature) for signature in IMAGE_SIGNATURES) or (
        len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    )


def _verify_image(uploaded_file):
    """Verify image structure, format and dimensions."""

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            image = Image.open(uploaded_file)

            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError({"file": "Unsupported image format."})

            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValidationError(
                    {"file": "Image dimensions exceed the permitted limit."}
                )

            image.verify()

            return ALLOWED_IMAGE_FORMATS[image.format]

    except ValidationError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
    ) as exc:
        raise ValidationError({"file": "Invalid or unsafe image file."}) from exc
    finally:
        uploaded_file.seek(0)


def validate_content_media(uploaded_file):
    """
    Validate uploaded content using its actual file signature.

    Returns verified category, MIME type, extension, size,
    and a sanitised original filename.
    """

    if uploaded_file is None:
        raise ValidationError({"file": "A file is required."})

    file_size = getattr(uploaded_file, "size", 0)

    if not isinstance(file_size, int) or file_size <= 0:
        raise ValidationError({"file": "The uploaded file is empty or invalid."})

    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(16)
        uploaded_file.seek(0)
    except (OSError, ValueError) as exc:
        raise ValidationError({"file": "The uploaded file cannot be read."}) from exc

    if not header:
        raise ValidationError({"file": "The uploaded file is empty."})

    category = None
    mime_type = None
    extension = None

    # If the signature identifies an image, invalid image data
    # must be rejected rather than treated as another file type.
    if _has_image_signature(header):
        mime_type, extension = _verify_image(uploaded_file)
        category = "IMAGE"

    elif len(header) >= 8 and header[4:8] == b"ftyp":
        category = "VIDEO"
        mime_type = "video/mp4"
        extension = ".mp4"

    elif header.startswith(b"\x1a\x45\xdf\xa3"):
        category = "VIDEO"
        mime_type = "video/webm"
        extension = ".webm"

    elif header.startswith(PDF_SIGNATURE):
        category = "DOCUMENT"
        mime_type = "application/pdf"
        extension = ".pdf"

    if category is None:
        raise ValidationError({"file": "Unsupported or unrecognised file content."})

    if file_size > MAX_FILE_SIZES[category]:
        raise ValidationError(
            {"file": (f"{category.title()} files exceed " "the permitted size limit.")}
        )

    original_filename = _sanitise_filename(
        getattr(uploaded_file, "name", "uploaded-file")
    )

    uploaded_file.seek(0)

    return {
        "category": category,
        "mime_type": mime_type,
        "extension": extension,
        "file_size": file_size,
        "original_filename": original_filename,
    }
