"""One reserved unit of frontier work, handed to a worker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .action import Action


@dataclass
class _Work:
    """One reserved unit of frontier work, handed from `_select_next_work` to a worker.

    The popped `action`, the screen `src_fp` it came from and the `src_path` to replay to reach it,
    and whether the worker must reset+replay first (`replay_needed`) or is already standing on
    `src_fp`. Not frozen: `src_path` is a mutable list (it feeds `_replay`, typed `list[Action]`),
    so `frozen=True` would be only a shallow, misleading guarantee. It is created and consumed
    within the coordinator, never hashed or shared, so plain mutability is fine (BE-0092).
    """

    src_fp: str
    action: Action
    src_path: list[Action]
    replay_needed: bool
