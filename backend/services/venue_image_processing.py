"""Bounded decoding and metadata-free re-encoding for venue images."""

from __future__ import annotations

import warnings
import zlib
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageFile, ImageOps, features

MAX_IMAGE_AXIS = 8_192
MAX_IMAGE_PIXELS = 20_000_000

MIME_TO_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
FORMAT_TO_MIME = {value: key for key, value in MIME_TO_FORMAT.items()}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ImageContentRejectedError(ValueError):
    """Uploaded bytes do not satisfy the accepted image contract."""

    def __init__(self, category: str, message: str) -> None:
        self.category = category
        super().__init__(message)


class ImageProcessorNotReadyError(RuntimeError):
    """The installed Pillow build cannot support the configured formats."""


@dataclass(frozen=True)
class SanitizedVenueImage:
    body: bytes
    content_type: str
    width: int
    height: int


@lru_cache(maxsize=8)
def _validate_cached(allowed_types: tuple[str, ...]) -> None:
    Image.init()
    for content_type in allowed_types:
        image_format = MIME_TO_FORMAT.get(content_type)
        if image_format is None:
            raise ImageProcessorNotReadyError("An image format is not supported.")
        extension = ".jpg" if image_format == "JPEG" else f".{image_format.lower()}"
        if (
            image_format not in Image.OPEN
            or image_format not in Image.SAVE
            or Image.registered_extensions().get(extension) != image_format
        ):
            raise ImageProcessorNotReadyError("An image codec is unavailable.")
        if image_format == "WEBP" and not features.check("webp"):
            raise ImageProcessorNotReadyError("An image codec is unavailable.")


def validate_image_processor_readiness(allowed_types: frozenset[str]) -> None:
    """Fail closed unless every configured decoder/encoder is installed."""

    if not allowed_types:
        raise ImageProcessorNotReadyError("No image format is configured.")
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise ImageProcessorNotReadyError("Truncated-image support must be disabled.")
    _validate_cached(tuple(sorted(allowed_types)))


def _reject(category: str, message: str) -> None:
    raise ImageContentRejectedError(category, message)


def _validate_dimensions(
    width: int,
    height: int,
    *,
    max_axis: int,
    max_pixels: int,
) -> None:
    if width <= 0 or height <= 0 or width > max_axis or height > max_axis:
        _reject("resource_limit", "Image dimensions exceed the supported limit.")
    if width * height > max_pixels:
        _reject("resource_limit", "Image pixel count exceeds the supported limit.")


def _classify_approved_signature(source: bytes) -> str | None:
    if source.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if source.startswith(PNG_SIGNATURE):
        return "image/png"
    if len(source) >= 12 and source[:4] == b"RIFF" and source[8:12] == b"WEBP":
        return "image/webp"
    return None


def _validate_opened_image(
    image: Image.Image,
    *,
    expected_content_type: str,
    max_axis: int,
    max_pixels: int,
) -> None:
    detected_type = FORMAT_TO_MIME.get(str(image.format).upper())
    if detected_type != expected_content_type:
        _reject("corrupt_image", "Image format is inconsistent with its signature.")
    _validate_dimensions(
        *image.size,
        max_axis=max_axis,
        max_pixels=max_pixels,
    )


def _validate_single_frame(
    image: Image.Image,
    *,
    container_declares_animation: bool = False,
) -> None:
    if (
        container_declares_animation
        or getattr(image, "n_frames", 1) != 1
        or bool(getattr(image, "is_animated", False))
    ):
        _reject("multi_frame", "Animated or multi-frame images are not supported.")


def _verify_png_first_frame_container(source: bytes) -> bool:
    """Verify PNG structure and CRCs through the complete first frame only."""

    offset = len(PNG_SIGNATURE)
    saw_animation_control = False
    saw_image_data = False
    saw_image_end = False
    while offset < len(source):
        if len(source) - offset < 12:
            _reject("corrupt_image", "Image container is incomplete.")
        data_length = int.from_bytes(source[offset : offset + 4], "big")
        chunk_type = source[offset + 4 : offset + 8]

        # APNG frame data after the default/first frame must not affect the
        # already-established multi-frame classification. Do not inspect its
        # payload or CRC.
        if (
            saw_animation_control
            and saw_image_data
            and chunk_type in {b"fcTL", b"fdAT"}
        ):
            return True

        chunk_end = offset + 12 + data_length
        if chunk_end > len(source):
            _reject("corrupt_image", "Image container is incomplete.")
        chunk_data_end = offset + 8 + data_length
        expected_crc = int.from_bytes(source[chunk_data_end:chunk_end], "big")
        actual_crc = zlib.crc32(source[offset + 4 : chunk_data_end]) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            _reject("corrupt_image", "Image container checksum is invalid.")

        saw_animation_control = saw_animation_control or chunk_type == b"acTL"
        saw_image_data = saw_image_data or chunk_type == b"IDAT"
        offset = chunk_end
        if chunk_type == b"IEND":
            saw_image_end = True
            if offset != len(source):
                _reject("corrupt_image", "Image container has trailing data.")
            break

    if not saw_image_data or not saw_image_end or offset != len(source):
        _reject("corrupt_image", "Image container is incomplete.")
    return saw_animation_control


def _verify_webp_first_frame_container(source: bytes) -> bool:
    """Verify RIFF chunk bounds through the complete first WebP frame."""

    if len(source) < 12:
        _reject("corrupt_image", "Image container length is invalid.")
    declared_end = int.from_bytes(source[4:8], "little") + 8
    if declared_end < 12:
        _reject("corrupt_image", "Image container length is invalid.")
    offset = 12
    declares_animation = False
    while offset < len(source):
        if len(source) - offset < 8:
            _reject("corrupt_image", "Image container is incomplete.")
        chunk_type = source[offset : offset + 4]
        data_length = int.from_bytes(source[offset + 4 : offset + 8], "little")
        chunk_end = offset + 8 + data_length
        padded_end = chunk_end + (data_length & 1)
        if chunk_end > len(source) or padded_end > len(source):
            _reject("corrupt_image", "Image container is incomplete.")
        if chunk_type == b"VP8X" and data_length >= 1:
            declares_animation = declares_animation or bool(source[offset + 8] & 0x02)
        declares_animation = declares_animation or chunk_type in {b"ANIM", b"ANMF"}
        offset = padded_end
        if chunk_type == b"ANMF":
            if declared_end < offset:
                _reject("corrupt_image", "Image container length is invalid.")
            return True

    if offset != len(source) or declared_end != len(source):
        _reject("corrupt_image", "Image container is incomplete.")
    return declares_animation


def _verify_first_frame_container(source: bytes, *, content_type: str) -> bool:
    if content_type == "image/png":
        return _verify_png_first_frame_container(source)
    if content_type == "image/webp":
        return _verify_webp_first_frame_container(source)
    with Image.open(BytesIO(source), formats=(MIME_TO_FORMAT[content_type],)) as probe:
        probe.verify()
    return False


def _close_image(image: Image.Image | None) -> None:
    if image is None:
        return
    try:
        image.close()
    except Exception:  # noqa: BLE001,S110 - cleanup must not mask the primary result.
        pass


def _fresh_pixels(
    image: Image.Image,
    *,
    content_type: str,
    max_axis: int,
    max_pixels: int,
) -> Image.Image:
    oriented: Image.Image | None = None
    converted: Image.Image | None = None
    fresh: Image.Image | None = None
    try:
        try:
            oriented = ImageOps.exif_transpose(image)
            _validate_dimensions(
                *oriented.size,
                max_axis=max_axis,
                max_pixels=max_pixels,
            )
            has_transparency = oriented.mode in {"RGBA", "LA"} or (
                oriented.mode == "P" and "transparency" in oriented.info
            )
            output_mode = (
                "RGBA"
                if content_type in {"image/png", "image/webp"} and has_transparency
                else "RGB"
            )
            converted = oriented.convert(output_mode)
            fresh = Image.new(output_mode, converted.size)
            fresh.paste(converted)
        except ImageContentRejectedError:
            raise
        except (KeyError, OSError, SyntaxError, TypeError, ValueError) as exc:
            raise ImageContentRejectedError(
                "unsupported_content",
                "Decoded image pixels cannot be normalized safely.",
            ) from exc
        result = fresh
        fresh = None
        if result is None:
            _reject("unsupported_content", "Image pixels could not be normalized.")
        return result
    finally:
        _close_image(fresh)
        _close_image(converted)
        if oriented is not image:
            _close_image(oriented)


def _encode(image: Image.Image, *, content_type: str) -> bytes:
    output = BytesIO()
    if content_type == "image/jpeg":
        image.save(
            output,
            format="JPEG",
            quality=85,
            subsampling=2,
            progressive=False,
            optimize=False,
            exif=b"",
            icc_profile=None,
        )
    elif content_type == "image/png":
        image.save(output, format="PNG", compress_level=6, optimize=False)
    else:
        image.save(
            output,
            format="WEBP",
            quality=85,
            method=4,
            exif=b"",
            icc_profile=b"",
            xmp=b"",
        )
    return output.getvalue()


def _validate_encoded_output(
    encoded: bytes,
    *,
    content_type: str,
    max_axis: int,
    max_pixels: int,
) -> tuple[int, int]:
    image_format = MIME_TO_FORMAT[content_type]
    with Image.open(BytesIO(encoded), formats=(image_format,)) as probe:
        _validate_opened_image(
            probe,
            expected_content_type=content_type,
            max_axis=max_axis,
            max_pixels=max_pixels,
        )
        probe.verify()

    with Image.open(BytesIO(encoded), formats=(image_format,)) as decoded:
        _validate_opened_image(
            decoded,
            expected_content_type=content_type,
            max_axis=max_axis,
            max_pixels=max_pixels,
        )
        decoded.load()
        if getattr(decoded, "n_frames", 1) != 1 or bool(
            getattr(decoded, "is_animated", False)
        ):
            _reject("corrupt_image", "Sanitized image is not single-frame output.")
        controlled_output_info = {
            "image/jpeg": {"jfif", "jfif_version", "jfif_unit", "jfif_density"},
            "image/png": set(),
            "image/webp": {"loop", "background", "timestamp", "duration"},
        }
        if set(decoded.info) - controlled_output_info[content_type]:
            _reject("corrupt_image", "Sanitized image retained unsupported metadata.")
        return decoded.size


def sanitize_venue_image(
    source: bytes,
    *,
    declared_content_type: str,
    allowed_types: frozenset[str],
    max_bytes: int,
    max_axis: int = MAX_IMAGE_AXIS,
    max_pixels: int = MAX_IMAGE_PIXELS,
) -> SanitizedVenueImage:
    """Verify actual pixels and return a fresh deterministic encoding."""

    if not source or len(source) > max_bytes:
        _reject("resource_limit", "Image bytes exceed the supported limit.")
    validate_image_processor_readiness(allowed_types)
    declared = declared_content_type.strip().lower()
    if declared not in allowed_types:
        _reject("unsupported_content", "Image content is not supported.")
    detected = _classify_approved_signature(source)
    if detected is None:
        _reject("unsupported_content", "Image content is not supported.")
    if detected != declared:
        _reject("type_mismatch", "Image content does not match its declared type.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(
                BytesIO(source),
                formats=(MIME_TO_FORMAT[detected],),
            ) as source_probe:
                _validate_opened_image(
                    source_probe,
                    expected_content_type=detected,
                    max_axis=max_axis,
                    max_pixels=max_pixels,
                )
                container_declares_animation = _verify_first_frame_container(
                    source,
                    content_type=detected,
                )
            with Image.open(
                BytesIO(source),
                formats=(MIME_TO_FORMAT[detected],),
            ) as decoded:
                _validate_opened_image(
                    decoded,
                    expected_content_type=detected,
                    max_axis=max_axis,
                    max_pixels=max_pixels,
                )
                decoded.load()
                _validate_single_frame(
                    decoded,
                    container_declares_animation=container_declares_animation,
                )
                fresh = _fresh_pixels(
                    decoded,
                    content_type=detected,
                    max_axis=max_axis,
                    max_pixels=max_pixels,
                )
            try:
                try:
                    encoded = _encode(fresh, content_type=detected)
                except Exception as exc:
                    raise ImageContentRejectedError(
                        "corrupt_image",
                        "Sanitized image could not be encoded safely.",
                    ) from exc
            finally:
                _close_image(fresh)

        if not encoded or len(encoded) > max_bytes:
            _reject(
                "encoded_size_limit", "Sanitized image exceeds the supported limit."
            )

        width, height = _validate_encoded_output(
            encoded,
            content_type=detected,
            max_axis=max_axis,
            max_pixels=max_pixels,
        )
    except ImageContentRejectedError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageContentRejectedError(
            "resource_limit",
            "Image dimensions exceed the supported limit.",
        ) from exc
    except Exception as exc:
        raise ImageContentRejectedError(
            "corrupt_image",
            "Image bytes could not be decoded safely.",
        ) from exc
    return SanitizedVenueImage(
        body=encoded,
        content_type=detected,
        width=width,
        height=height,
    )
