from __future__ import annotations

import zlib
from io import BytesIO

import pytest
from PIL import Image, ImageFile, PngImagePlugin

from backend.services import venue_image_processing
from backend.services.venue_image_processing import (
    ImageContentRejectedError,
    ImageProcessorNotReadyError,
    sanitize_venue_image,
    validate_image_processor_readiness,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance("WS06-02"),
]


def _image_bytes(
    image_format: str,
    *,
    mode: str = "RGB",
    size: tuple[int, int] = (7, 5),
    metadata: bool = False,
) -> bytes:
    image = Image.new(mode, size, (20, 40, 60, 120) if mode == "RGBA" else (20, 40, 60))
    output = BytesIO()
    kwargs: dict[str, object] = {}
    if image_format == "PNG" and metadata:
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Comment", "must disappear")
        kwargs["pnginfo"] = pnginfo
    image.save(output, format=image_format, **kwargs)
    image.close()
    return output.getvalue()


def _animated_png_with_corrupt_later_frame() -> bytes:
    frames = [Image.new("RGB", (4, 4), color) for color in ("red", "blue")]
    output = BytesIO()
    frames[0].save(output, format="PNG", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()
    source = bytearray(output.getvalue())
    later_frame_data = source.index(b"fdAT") + len(b"fdAT")
    source[later_frame_data] ^= 1
    return bytes(source)


def _animated_png_with_corrupt_first_frame() -> bytes:
    frames = [Image.new("RGB", (4, 4), color) for color in ("red", "blue")]
    output = BytesIO()
    frames[0].save(output, format="PNG", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()
    source = bytearray(output.getvalue())
    chunk_type_index = source.index(b"IDAT")
    data_length = int.from_bytes(source[chunk_type_index - 4 : chunk_type_index], "big")
    crc_index = chunk_type_index + len(b"IDAT") + data_length
    source[crc_index] ^= 1
    return bytes(source)


def _single_frame_apng_bytes() -> bytes:
    frames = [Image.new("RGB", (4, 4), color) for color in ("red", "blue")]
    output = BytesIO()
    frames[0].save(output, format="PNG", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()

    source = output.getvalue()
    rebuilt = bytearray(source[:8])
    offset = 8
    frame_control_count = 0
    while offset < len(source):
        data_length = int.from_bytes(source[offset : offset + 4], "big")
        chunk_end = offset + 12 + data_length
        chunk_type = source[offset + 4 : offset + 8]
        chunk_data = source[offset + 8 : offset + 8 + data_length]
        if chunk_type == b"acTL":
            chunk_data = (1).to_bytes(4, "big") + chunk_data[4:]
        elif chunk_type == b"fcTL":
            frame_control_count += 1
            if frame_control_count > 1:
                offset = chunk_end
                continue
        elif chunk_type == b"fdAT":
            offset = chunk_end
            continue
        rebuilt.extend(len(chunk_data).to_bytes(4, "big"))
        rebuilt.extend(chunk_type)
        rebuilt.extend(chunk_data)
        rebuilt.extend(
            (zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF).to_bytes(4, "big")
        )
        offset = chunk_end
    return bytes(rebuilt)


def _single_frame_animated_webp_bytes() -> bytes:
    frames = [Image.new("RGB", (4, 4), color) for color in ("red", "blue")]
    output = BytesIO()
    frames[0].save(output, format="WEBP", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()

    source = output.getvalue()
    offset = 12
    first_frame_end = None
    while offset < len(source):
        data_length = int.from_bytes(source[offset + 4 : offset + 8], "little")
        padded_end = offset + 8 + data_length + (data_length & 1)
        if source[offset : offset + 4] == b"ANMF":
            first_frame_end = padded_end
            break
        offset = padded_end
    assert first_frame_end is not None
    rebuilt = bytearray(source[:first_frame_end])
    rebuilt[4:8] = (len(rebuilt) - 8).to_bytes(4, "little")
    return bytes(rebuilt)


def _corrupt_real_image(source: bytes, image_format: str) -> bytes:
    corrupted = bytearray(source)
    if image_format == "PNG":
        chunk_type_index = corrupted.index(b"IDAT")
        data_length = int.from_bytes(
            corrupted[chunk_type_index - 4 : chunk_type_index], "big"
        )
        crc_index = chunk_type_index + len(b"IDAT") + data_length
        corrupted[crc_index] ^= 1
    else:
        # Keep the canonical RIFF/WEBP signature while making the declared
        # container length contradict the actual provider bytes.
        declared_length = int.from_bytes(corrupted[4:8], "little")
        corrupted[4:8] = (declared_length + 1).to_bytes(4, "little")
    return bytes(corrupted)


def _corrupt_real_jpeg_or_webp_payload(source: bytes, image_format: str) -> bytes:
    corrupted = bytearray(source)
    if image_format == "JPEG":
        scan_marker = corrupted.index(b"\xff\xda")
        scan_header_length = int.from_bytes(
            corrupted[scan_marker + 2 : scan_marker + 4],
            "big",
        )
        scan_data = scan_marker + 2 + scan_header_length
        corrupted[scan_data : scan_data + 4] = b"\xff\xc4\xff\xc4"
    else:
        frame_payload = corrupted.index(b"VP8 ") + 8
        corrupted[frame_payload + 3 : frame_payload + 6] = b"\x00\x00\x00"
    return bytes(corrupted)


@pytest.mark.parametrize(
    ("content_type", "image_format", "mode"),
    [
        ("image/jpeg", "JPEG", "RGB"),
        ("image/png", "PNG", "RGBA"),
        ("image/webp", "WEBP", "RGBA"),
    ],
)
def test_sanitizer_reencodes_approved_single_frame_images_deterministically(
    content_type: str,
    image_format: str,
    mode: str,
) -> None:
    allowed = frozenset({content_type})
    source = _image_bytes(image_format, mode=mode, metadata=True)

    first = sanitize_venue_image(
        source,
        declared_content_type=content_type,
        allowed_types=allowed,
        max_bytes=1_000_000,
    )
    second = sanitize_venue_image(
        source,
        declared_content_type=content_type,
        allowed_types=allowed,
        max_bytes=1_000_000,
    )

    assert first.body == second.body
    assert first.content_type == content_type
    assert (first.width, first.height) == (7, 5)
    with Image.open(BytesIO(first.body)) as output:
        output.load()
        assert not {"exif", "icc_profile", "xmp", "comment"}.intersection(output.info)


def test_sanitizer_rejects_declared_type_mismatch_and_resource_limits() -> None:
    source = _image_bytes("PNG")
    with pytest.raises(ImageContentRejectedError, match="declared") as mismatch:
        sanitize_venue_image(
            source,
            declared_content_type="image/jpeg",
            allowed_types=frozenset({"image/jpeg", "image/png"}),
            max_bytes=1_000_000,
        )
    assert mismatch.value.category == "type_mismatch"

    with pytest.raises(ImageContentRejectedError) as limited:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
            max_axis=4,
        )
    assert limited.value.category == "resource_limit"


def test_sanitizer_rejects_unrecognized_and_animated_inputs() -> None:
    with pytest.raises(ImageContentRejectedError) as unsupported:
        sanitize_venue_image(
            b"not-an-image",
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1024,
        )
    assert unsupported.value.category == "unsupported_content"

    frames = [Image.new("RGB", (2, 2), color) for color in ("red", "blue")]
    output = BytesIO()
    frames[0].save(output, format="WEBP", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()
    with pytest.raises(ImageContentRejectedError) as animated:
        sanitize_venue_image(
            output.getvalue(),
            declared_content_type="image/webp",
            allowed_types=frozenset({"image/webp"}),
            max_bytes=1024 * 1024,
        )
    assert animated.value.category == "multi_frame"


@pytest.mark.parametrize(
    ("source", "content_type"),
    [
        (_single_frame_apng_bytes(), "image/png"),
        (_single_frame_animated_webp_bytes(), "image/webp"),
    ],
)
def test_sanitizer_rejects_single_frame_containers_that_declare_animation(
    source: bytes,
    content_type: str,
) -> None:
    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type=content_type,
            allowed_types=frozenset({content_type}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "multi_frame"


def test_sanitizer_classifies_corrupt_later_frame_as_multi_frame() -> None:
    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            _animated_png_with_corrupt_later_frame(),
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "multi_frame"


def test_sanitizer_classifies_corrupt_first_frame_as_corrupt_image() -> None:
    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            _animated_png_with_corrupt_first_frame(),
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "corrupt_image"


def test_sanitizer_applies_orientation_and_removes_source_metadata() -> None:
    source_image = Image.new("RGB", (2, 3), "navy")
    exif = Image.Exif()
    exif[274] = 6
    source_buffer = BytesIO()
    source_image.save(
        source_buffer,
        format="JPEG",
        exif=exif,
        icc_profile=b"synthetic-icc-profile",
        comment=b"must disappear",
    )
    source_image.close()

    sanitized = sanitize_venue_image(
        source_buffer.getvalue(),
        declared_content_type="image/jpeg",
        allowed_types=frozenset({"image/jpeg"}),
        max_bytes=1_000_000,
    )

    assert (sanitized.width, sanitized.height) == (3, 2)
    with Image.open(BytesIO(sanitized.body)) as output:
        output.load()
        assert not {"exif", "icc_profile", "xmp", "comment"}.intersection(output.info)


def test_sanitizer_removes_supported_webp_metadata() -> None:
    source_image = Image.new("RGB", (7, 5), "navy")
    exif = Image.Exif()
    exif[305] = "uploader-supplied"
    source_buffer = BytesIO()
    source_image.save(
        source_buffer,
        format="WEBP",
        exif=exif,
        icc_profile=b"synthetic-icc-profile",
        xmp=b"<x:xmpmeta>uploader-supplied</x:xmpmeta>",
    )
    source_image.close()
    source = source_buffer.getvalue()
    with Image.open(BytesIO(source)) as source_probe:
        source_probe.load()
        assert {"exif", "icc_profile", "xmp"}.issubset(source_probe.info)

    sanitized = sanitize_venue_image(
        source,
        declared_content_type="image/webp",
        allowed_types=frozenset({"image/webp"}),
        max_bytes=1_000_000,
    )

    with Image.open(BytesIO(sanitized.body)) as output:
        output.load()
        assert not {"exif", "icc_profile", "xmp"}.intersection(output.info)


def test_sanitizer_preserves_supported_transparency_without_source_metadata() -> None:
    source = _image_bytes("PNG", mode="RGBA", metadata=True)

    sanitized = sanitize_venue_image(
        source,
        declared_content_type="image/png",
        allowed_types=frozenset({"image/png"}),
        max_bytes=1_000_000,
    )

    with Image.open(BytesIO(sanitized.body)) as output:
        output.load()
        assert output.mode == "RGBA"
        assert output.getchannel("A").getextrema() == (120, 120)
        assert "comment" not in output.info


@pytest.mark.parametrize("image_format", ["GIF", "BMP", "TIFF", "ICO", "PPM"])
def test_sanitizer_rejects_unsupported_bytes_disguised_as_an_approved_type(
    image_format: str,
) -> None:
    source = _image_bytes(image_format)

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "unsupported_content"


@pytest.mark.parametrize(
    ("source_format", "source_type", "declared_type"),
    [
        ("JPEG", "image/jpeg", "image/png"),
        ("PNG", "image/png", "image/webp"),
        ("WEBP", "image/webp", "image/jpeg"),
    ],
)
def test_approved_signature_mismatch_rejects_before_decoder_even_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    source_format: str,
    source_type: str,
    declared_type: str,
) -> None:
    del source_type
    monkeypatch.setattr(
        Image,
        "open",
        lambda *args, **kwargs: pytest.fail("mismatched signature reached decoder"),
    )

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            _image_bytes(source_format),
            declared_content_type=declared_type,
            allowed_types=frozenset({declared_type}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "type_mismatch"


@pytest.mark.parametrize(
    ("source", "content_type"),
    [
        (b"\xff\xd8\xffbroken-jpeg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\nbroken-png", "image/png"),
        (b"RIFF\x08\x00\x00\x00WEBPbroken", "image/webp"),
    ],
)
def test_matching_approved_signature_with_invalid_container_is_corrupt(
    source: bytes,
    content_type: str,
) -> None:
    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type=content_type,
            allowed_types=frozenset({content_type}),
            max_bytes=1_000_000,
        )
    assert rejected.value.category == "corrupt_image"


def test_sanitizer_rejects_truncated_input() -> None:
    source = _image_bytes("JPEG")

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source[:-24],
            declared_content_type="image/jpeg",
            allowed_types=frozenset({"image/jpeg"}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "corrupt_image"


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_sanitizer_rejects_real_truncated_png_and_webp(
    image_format: str,
    content_type: str,
) -> None:
    source = _image_bytes(image_format)

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source[:-12],
            declared_content_type=content_type,
            allowed_types=frozenset({content_type}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "corrupt_image"


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_sanitizer_rejects_real_corrupt_png_and_webp(
    image_format: str,
    content_type: str,
) -> None:
    source = _corrupt_real_image(_image_bytes(image_format), image_format)

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type=content_type,
            allowed_types=frozenset({content_type}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "corrupt_image"


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [("JPEG", "image/jpeg"), ("WEBP", "image/webp")],
)
def test_sanitizer_rejects_real_internal_jpeg_and_webp_corruption(
    image_format: str,
    content_type: str,
) -> None:
    source = _corrupt_real_jpeg_or_webp_payload(
        _image_bytes(image_format, size=(32, 32)),
        image_format,
    )

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type=content_type,
            allowed_types=frozenset({content_type}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "corrupt_image"


def test_normalization_failure_is_unsupported_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("PNG")
    monkeypatch.setattr(
        Image.Image,
        "convert",
        lambda self, mode: (_ for _ in ()).throw(OSError("unsupported mode")),
    )

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
        )
    assert rejected.value.category == "unsupported_content"


def test_resource_bounds_precede_multi_frame_classification() -> None:
    frames = [Image.new("RGB", (6, 5), color) for color in ("red", "blue")]
    output = BytesIO()
    frames[0].save(output, format="WEBP", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            output.getvalue(),
            declared_content_type="image/webp",
            allowed_types=frozenset({"image/webp"}),
            max_bytes=1_000_000,
            max_axis=5,
        )
    assert rejected.value.category == "resource_limit"


def test_sanitizer_enforces_exact_byte_axis_and_pixel_boundaries() -> None:
    source = _image_bytes("PNG", size=(4, 3))
    allowed = frozenset({"image/png"})

    accepted = sanitize_venue_image(
        source,
        declared_content_type="image/png",
        allowed_types=allowed,
        max_bytes=len(source),
        max_axis=4,
        max_pixels=12,
    )
    assert (accepted.width, accepted.height) == (4, 3)

    just_below = sanitize_venue_image(
        source,
        declared_content_type="image/png",
        allowed_types=allowed,
        max_bytes=len(source) + 1,
        max_axis=5,
        max_pixels=13,
    )
    assert (just_below.width, just_below.height) == (4, 3)

    for overrides in (
        {"max_bytes": len(source) - 1, "max_axis": 4, "max_pixels": 12},
        {"max_bytes": len(source), "max_axis": 3, "max_pixels": 12},
        {"max_bytes": len(source), "max_axis": 4, "max_pixels": 11},
    ):
        with pytest.raises(ImageContentRejectedError) as rejected:
            sanitize_venue_image(
                source,
                declared_content_type="image/png",
                allowed_types=allowed,
                **overrides,
            )
        assert rejected.value.category == "resource_limit"


@pytest.mark.parametrize("size", [(3, 2), (3, 3)])
def test_sanitizer_converts_pillow_decompression_limits_to_safe_rejection(
    monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int],
) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 4)

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            _image_bytes("PNG", size=size),
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
            max_pixels=100,
        )

    assert rejected.value.category == "resource_limit"


def test_sanitizer_rejects_oversized_or_invalid_reencoded_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("PNG")
    monkeypatch.setattr(
        venue_image_processing,
        "_encode",
        lambda image, *, content_type: b"",
    )
    with pytest.raises(ImageContentRejectedError) as empty:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=len(source),
        )
    assert empty.value.category == "encoded_size_limit"

    monkeypatch.setattr(
        venue_image_processing,
        "_encode",
        lambda image, *, content_type: source + b"too-large",
    )
    with pytest.raises(ImageContentRejectedError) as oversized:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=len(source),
        )
    assert oversized.value.category == "encoded_size_limit"

    monkeypatch.setattr(
        venue_image_processing,
        "_encode",
        lambda image, *, content_type: b"not-an-image",
    )
    with pytest.raises(ImageContentRejectedError) as invalid:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
        )
    assert invalid.value.category == "corrupt_image"


def test_sanitizer_rejects_metadata_reintroduced_by_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("PNG")
    encoded_with_metadata = _image_bytes("PNG", metadata=True)
    monkeypatch.setattr(
        venue_image_processing,
        "_encode",
        lambda image, *, content_type: encoded_with_metadata,
    )

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
        )

    assert rejected.value.category == "corrupt_image"


def test_sanitizer_rejects_output_that_exceeds_dimension_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("PNG", size=(4, 3))
    oversized_output = _image_bytes("PNG", size=(5, 3))
    monkeypatch.setattr(
        venue_image_processing,
        "_encode",
        lambda image, *, content_type: oversized_output,
    )

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type="image/png",
            allowed_types=frozenset({"image/png"}),
            max_bytes=1_000_000,
            max_axis=4,
        )
    assert rejected.value.category == "resource_limit"


def test_sanitizer_classifies_multi_frame_encoder_output_as_corrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("WEBP")
    frames = [Image.new("RGB", (3, 2), color) for color in ("red", "blue")]
    encoded = BytesIO()
    frames[0].save(encoded, format="WEBP", save_all=True, append_images=frames[1:])
    for frame in frames:
        frame.close()
    monkeypatch.setattr(
        venue_image_processing,
        "_encode",
        lambda image, *, content_type: encoded.getvalue(),
    )

    with pytest.raises(ImageContentRejectedError) as rejected:
        sanitize_venue_image(
            source,
            declared_content_type="image/webp",
            allowed_types=frozenset({"image/webp"}),
            max_bytes=1_000_000,
        )
    assert rejected.value.category == "corrupt_image"


def test_sanitizer_closes_every_opened_image_on_success_and_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_open = Image.open
    closed: list[bool] = []

    class TrackedImage:
        def __init__(self, *args, **kwargs) -> None:
            self.image = real_open(*args, **kwargs)

        def __enter__(self):
            return self.image

        def __exit__(self, exc_type, exc, traceback) -> None:
            self.image.close()
            closed.append(self.image.fp is None)

    monkeypatch.setattr(Image, "open", TrackedImage)
    source = _image_bytes("PNG")

    sanitize_venue_image(
        source,
        declared_content_type="image/png",
        allowed_types=frozenset({"image/png"}),
        max_bytes=1_000_000,
    )
    assert closed == [True, True, True, True]

    closed.clear()
    with pytest.raises(ImageContentRejectedError):
        sanitize_venue_image(
            source,
            declared_content_type="image/jpeg",
            allowed_types=frozenset({"image/jpeg", "image/png"}),
            max_bytes=1_000_000,
        )
    assert closed == []


def test_readiness_supports_the_approved_codec_subset() -> None:
    validate_image_processor_readiness(
        frozenset({"image/jpeg", "image/png", "image/webp"})
    )


def test_readiness_fails_closed_when_truncated_image_support_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ImageFile, "LOAD_TRUNCATED_IMAGES", True)

    with pytest.raises(ImageProcessorNotReadyError, match="must be disabled"):
        validate_image_processor_readiness(frozenset({"image/jpeg"}))


@pytest.mark.parametrize("registry_name", ["OPEN", "SAVE"])
def test_readiness_requires_each_configured_decoder_and_encoder(
    monkeypatch: pytest.MonkeyPatch,
    registry_name: str,
) -> None:
    Image.init()
    registry = dict(getattr(Image, registry_name))
    registry.pop("PNG")
    monkeypatch.setattr(Image, registry_name, registry)
    venue_image_processing._validate_cached.cache_clear()

    with pytest.raises(ImageProcessorNotReadyError, match="codec is unavailable"):
        validate_image_processor_readiness(frozenset({"image/png"}))

    venue_image_processing._validate_cached.cache_clear()
