"""Black out the identity block before a page image leaves the machine.

Master spec §2.5 puts the anonymisation boundary before the evaluator. Sending
a page to a hosted model moves that boundary earlier: the identity has to be
gone before the bytes leave the process, not before the evaluator reads the
text. This is that boundary applied to pixels.

THE REGION IS EXAM-SPECIFIC AND A HUMAN MUST SET IT
---------------------------------------------------
Answer books differ. A default that happens to fit one board's layout will
silently miss the header on another, and the failure is invisible -- the image
looks masked, the name is two centimetres lower. So:

  * there is NO default region;
  * `mask_identity_region` raises when asked to mask without one;
  * the configured region for an exam must be verified by a human against a
    real page of that exam before any script is sent.

`MaskRegion` is in fractions of page width and height, so it survives a change
of DPI. Absolute pixels would silently mask the wrong area the first time
someone rasterised at a different resolution.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from AI.ocr.rasterize import PageImage, sha256_bytes

logger = logging.getLogger("GradeMIND.IdentityMask")

MASK_VERSION = "identity-mask/1.0.0"


class IdentityMaskError(RuntimeError):
    """The identity region could not be masked.

    Raised rather than sending an unmasked page. Failing to mask is a data
    protection incident; failing to extract is an inconvenience.
    """


@dataclass(frozen=True)
class MaskRegion:
    """A rectangle in page fractions: 0.0-1.0 of width and height."""

    x0: float
    y0: float
    x1: float
    y1: float
    label: str = "identity block"

    def __post_init__(self) -> None:
        for name, value in (("x0", self.x0), ("y0", self.y0), ("x1", self.x1), ("y1", self.y1)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"MaskRegion.{name}={value} must be a fraction of the page "
                    "(0.0-1.0), not pixels: a pixel region silently masks the "
                    "wrong area at a different DPI"
                )
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError(f"MaskRegion is empty or inverted: {self}")

    def to_pixels(self, width: int, height: int) -> Tuple[int, int, int, int]:
        return (
            int(self.x0 * width),
            int(self.y0 * height),
            int(self.x1 * width),
            int(self.y1 * height),
        )


def mask_identity_region(
    page: PageImage,
    region: Optional[MaskRegion],
    *,
    require_region: bool = True,
) -> PageImage:
    """Return a copy of the page with `region` filled solid black.

    Args:
        require_region: when True (the default), a missing region raises. Set
            it False ONLY for a page class that genuinely carries no identity
            -- and record why at the call site.
    """
    if region is None:
        if require_region:
            raise IdentityMaskError(
                f"page {page.page_number}: no identity mask region configured "
                "for this exam. Refusing to send an unmasked page to a "
                "third-party model. Configure and human-verify the region "
                "against a real page of this exam first."
            )
        logger.warning(
            "IDENTITY_MASK_STAGE no_region page=%s; sending unmasked by explicit "
            "opt-out", page.page_number,
        )
        return page

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover - Pillow is a declared dep
        raise IdentityMaskError(f"Pillow is required to mask identity: {exc}") from exc

    try:
        image = Image.open(io.BytesIO(page.image_bytes))
        image.load()
    except Exception as exc:
        raise IdentityMaskError(
            f"page {page.page_number}: cannot open image to mask it: {exc}"
        ) from exc

    box = region.to_pixels(image.width, image.height)
    draw = ImageDraw.Draw(image)
    # Solid fill, not blur: blurred text is often still recoverable, and
    # "probably unreadable" is not a standard to hold student identity to.
    draw.rectangle(box, fill=(0, 0, 0) if image.mode == "RGB" else 0)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    masked_bytes = buffer.getvalue()

    logger.info(
        "IDENTITY_MASK_STAGE applied page=%s region=%s box=%s",
        page.page_number, region.label, box,
    )

    return PageImage(
        page_number=page.page_number,
        image_bytes=masked_bytes,
        width=page.width,
        height=page.height,
        dpi=page.dpi,
        source_sha256=page.source_sha256,
        # The hash changes, and it must: the masked image is a different
        # artefact and must not collide with the unmasked one in the cache.
        page_sha256=sha256_bytes(masked_bytes),
        rasterize_version=page.rasterize_version,
    )
