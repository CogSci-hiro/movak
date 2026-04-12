"""Editable annotation document models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

AnnotationTierType = Literal["interval", "point"]


def _annotation_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class IntervalAnnotation:
    """Editable interval annotation.

    Parameters
    ----------
    start_time
        Annotation onset in seconds.
    end_time
        Annotation offset in seconds.
    text
        Display label.
    id
        Stable annotation identifier.
    """

    start_time: float
    end_time: float
    text: str = ""
    id: str = field(default_factory=_annotation_id)

    def __post_init__(self) -> None:
        self.start_time = float(self.start_time)
        self.end_time = float(self.end_time)
        if self.start_time < 0.0:
            raise ValueError("Interval start_time must be non-negative.")
        if self.end_time < self.start_time:
            raise ValueError("Interval end_time must be greater than or equal to start_time.")

    @property
    def duration(self) -> float:
        """Return the annotation duration in seconds."""

        return self.end_time - self.start_time


@dataclass(slots=True)
class PointAnnotation:
    """Editable point annotation.

    Parameters
    ----------
    time
        Time position in seconds.
    text
        Display label.
    id
        Stable annotation identifier.
    """

    time: float
    text: str = ""
    id: str = field(default_factory=_annotation_id)

    def __post_init__(self) -> None:
        self.time = float(self.time)
        if self.time < 0.0:
            raise ValueError("Point time must be non-negative.")


AnnotationItem = IntervalAnnotation | PointAnnotation


@dataclass(slots=True)
class AnnotationTier:
    """Ordered annotation tier.

    Parameters
    ----------
    name
        Human-readable tier label.
    tier_type
        Tier kind, either ``"interval"`` or ``"point"``.
    annotations
        Tier annotations sorted by time.
    id
        Stable tier identifier.
    """

    name: str
    tier_type: AnnotationTierType
    annotations: list[AnnotationItem] = field(default_factory=list)
    id: str = field(default_factory=_annotation_id)

    def __post_init__(self) -> None:
        self._validate_annotations()
        self.sort_annotations()

    def sort_annotations(self) -> None:
        """Sort annotations in timeline order."""

        if self.tier_type == "interval":
            self.annotations.sort(key=lambda item: (item.start_time, item.end_time, item.id))  # type: ignore[attr-defined]
            return
        self.annotations.sort(key=lambda item: (item.time, item.id))  # type: ignore[attr-defined]

    def add_annotation(self, annotation: AnnotationItem) -> None:
        """Insert an annotation into the tier."""

        self._validate_annotation(annotation)
        self.annotations.append(annotation)
        self.sort_annotations()

    def remove_annotation(self, annotation_id: str) -> AnnotationItem:
        """Remove and return an annotation by identifier."""

        for index, annotation in enumerate(self.annotations):
            if annotation.id == annotation_id:
                return self.annotations.pop(index)
        raise KeyError(f"Annotation '{annotation_id}' does not exist in tier '{self.name}'.")

    def find_annotation(self, annotation_id: str) -> AnnotationItem | None:
        """Return an annotation by identifier when present."""

        for annotation in self.annotations:
            if annotation.id == annotation_id:
                return annotation
        return None

    def annotation_index(self, annotation_id: str) -> int:
        """Return the index of an annotation by identifier."""

        for index, annotation in enumerate(self.annotations):
            if annotation.id == annotation_id:
                return index
        raise KeyError(f"Annotation '{annotation_id}' does not exist in tier '{self.name}'.")

    def neighbor_annotations(self, annotation_id: str) -> tuple[AnnotationItem | None, AnnotationItem | None]:
        """Return the previous and next annotations around an item."""

        index = self.annotation_index(annotation_id)
        previous_annotation = self.annotations[index - 1] if index > 0 else None
        next_annotation = self.annotations[index + 1] if index + 1 < len(self.annotations) else None
        return previous_annotation, next_annotation

    def visible_annotations(self, start_time: float, end_time: float) -> list[AnnotationItem]:
        """Return annotations overlapping the visible time range."""

        if self.tier_type == "interval":
            return [
                annotation
                for annotation in self.annotations
                if isinstance(annotation, IntervalAnnotation)
                and annotation.start_time < end_time
                and start_time < annotation.end_time
            ]
        return [
            annotation
            for annotation in self.annotations
            if isinstance(annotation, PointAnnotation)
            and start_time <= annotation.time <= end_time
        ]

    def _validate_annotations(self) -> None:
        for annotation in self.annotations:
            self._validate_annotation(annotation)

    def _validate_annotation(self, annotation: AnnotationItem) -> None:
        if self.tier_type == "interval" and not isinstance(annotation, IntervalAnnotation):
            raise TypeError("Interval tiers can only contain IntervalAnnotation items.")
        if self.tier_type == "point" and not isinstance(annotation, PointAnnotation):
            raise TypeError("Point tiers can only contain PointAnnotation items.")


@dataclass(slots=True)
class AnnotationDocument:
    """Top-level editable annotation document.

    Parameters
    ----------
    tiers
        Ordered tiers shown in the editor.
    duration_seconds
        Timeline duration used for clamping edits.
    """

    tiers: list[AnnotationTier] = field(default_factory=list)
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        self.duration_seconds = max(float(self.duration_seconds), 0.0)

    def get_tier(self, tier_id: str) -> AnnotationTier:
        """Return a tier by identifier."""

        for tier in self.tiers:
            if tier.id == tier_id:
                return tier
        raise KeyError(f"Tier '{tier_id}' does not exist.")

    def add_tier(self, tier: AnnotationTier) -> None:
        """Append a tier to the document."""

        self.tiers.append(tier)

    def find_annotation(self, tier_id: str, annotation_id: str) -> AnnotationItem | None:
        """Return an annotation from a specific tier when present."""

        return self.get_tier(tier_id).find_annotation(annotation_id)


def build_demo_annotation_document(duration_seconds: float = 12.0) -> AnnotationDocument:
    """Return a small demo annotation document for the first editor pass."""

    return AnnotationDocument(
        duration_seconds=duration_seconds,
        tiers=[
            AnnotationTier(
                name="Words",
                tier_type="interval",
                annotations=[
                    IntervalAnnotation(0.25, 1.65, "hello"),
                    IntervalAnnotation(1.80, 3.05, "world"),
                    IntervalAnnotation(3.30, 4.85, "today"),
                ],
            ),
            AnnotationTier(
                name="Phonemes",
                tier_type="interval",
                annotations=[
                    IntervalAnnotation(0.25, 0.55, "h"),
                    IntervalAnnotation(0.55, 0.92, "e"),
                    IntervalAnnotation(0.92, 1.22, "l"),
                    IntervalAnnotation(1.22, 1.65, "o"),
                    IntervalAnnotation(1.80, 2.12, "w"),
                    IntervalAnnotation(2.12, 2.46, "ɜ"),
                    IntervalAnnotation(2.46, 2.80, "l"),
                    IntervalAnnotation(2.80, 3.05, "d"),
                ],
            ),
            AnnotationTier(
                name="Events",
                tier_type="point",
                annotations=[
                    PointAnnotation(0.52, "burst"),
                    PointAnnotation(2.08, "accent"),
                    PointAnnotation(4.10, "release"),
                ],
            ),
        ],
    )
