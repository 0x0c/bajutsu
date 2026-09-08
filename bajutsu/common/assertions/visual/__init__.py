"""Visual-assertion image preprocessing.

The coordinate math, cropping, masking, and Pillow file I/O a `visual` assertion needs before it
hands off to `bajutsu.common.evidence.visual`'s pixel-compare engine. Frames are in element points; the screenshot
is in device pixels, so everything here resolves selectors and scales frames into pixel space.
"""

from ._functions import _eval_visual as _eval_visual
from ._functions import _frame_to_px as _frame_to_px
from ._functions import _prepare_visual_comparison as _prepare_visual_comparison
from ._functions import _resolve_baselines as _resolve_baselines
from ._functions import _resolve_mask as _resolve_mask
from ._functions import _resolve_masks as _resolve_masks
from ._functions import _shift as _shift
from ._functions import _visual_scale as _visual_scale
from ._prepared import _Prepared as _Prepared
from .visual_context import VisualContext
from .visual_evidence import VisualEvidence

__all__ = ["VisualContext", "VisualEvidence"]
