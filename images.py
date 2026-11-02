"""Safe handling of uploaded item photos."""
import io
import os
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SIDE = 1200  # pixels


class ImageError(ValueError):
    """Raised with a user-friendly message when an upload is rejected."""


def save_item_image(file_storage, folder, max_bytes):
    """Validate an uploaded photo, re-encode it as a JPEG and return the new file name.

    Re-encoding with Pillow means the stored file is always a real image: a script renamed
    to .jpg fails to open, and EXIF metadata (such as GPS position) is dropped.
    """
    original_name = file_storage.filename or ""
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ImageError("Photo must be a JPG, PNG or WEBP image.")

    data = file_storage.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ImageError("Photo must be 3 MB or smaller.")

    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()                       # checks the file is not corrupt
        image = Image.open(io.BytesIO(data))  # verify() closes the file, so reopen
        if image.format not in ALLOWED_FORMATS:
            raise ImageError("Photo must be a JPG, PNG or WEBP image.")
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ImageError("The uploaded file is not a valid image.")

    image.thumbnail((MAX_SIDE, MAX_SIDE))
    os.makedirs(folder, exist_ok=True)
    filename = uuid.uuid4().hex + ".jpg"      # random name: never trust the client's name
    image.save(os.path.join(folder, filename), "JPEG", quality=85, optimize=True)
    return filename


def delete_image(folder, filename):
    """Remove a stored photo (ignores missing files and path tricks)."""
    if not filename:
        return
    path = os.path.join(folder, os.path.basename(filename))
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
