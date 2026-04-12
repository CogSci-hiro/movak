from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from ...annotations.model import (
    AnnotationDocument,
    AnnotationItem,
    AnnotationTier,
    IntervalAnnotation,
    PointAnnotation,
)

DEFAULT_NEW_INTERVAL_DURATION_SECONDS = 0.35


@dataclass(slots=True)
class AnnotationSelection:
    """Current annotation editor selection."""

    tier_id: str | None = None
    annotation_id: str | None = None


class AnnotationEditorController(QObject):
    """Own annotation selection state and first-pass editing operations."""

    document_changed = pyqtSignal()
    selection_changed = pyqtSignal(object)

    def __init__(self, document: AnnotationDocument, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.document = document
        self.selection = AnnotationSelection()

    @property
    def active_tier_id(self) -> str | None:
        """Return the currently active tier identifier."""

        return self.selection.tier_id

    def set_document_duration(self, duration_seconds: float) -> None:
        """Update the document duration used for clamping edits."""

        self.document.duration_seconds = max(float(duration_seconds), 0.0)

    def select_tier(self, tier_id: str) -> None:
        """Activate a tier without selecting an annotation."""

        self.selection = AnnotationSelection(tier_id=tier_id, annotation_id=None)
        self.selection_changed.emit(self.selection)

    def select_annotation(self, tier_id: str, annotation_id: str) -> None:
        """Select an annotation and activate its tier."""

        self.selection = AnnotationSelection(tier_id=tier_id, annotation_id=annotation_id)
        self.selection_changed.emit(self.selection)

    def clear_selection(self) -> None:
        """Clear the active annotation selection."""

        tier_id = self.selection.tier_id
        self.selection = AnnotationSelection(tier_id=tier_id, annotation_id=None)
        self.selection_changed.emit(self.selection)

    def selected_tier(self) -> AnnotationTier | None:
        """Return the active tier when present."""

        if self.selection.tier_id is None:
            return None
        try:
            return self.document.get_tier(self.selection.tier_id)
        except KeyError:
            return None

    def selected_annotation(self) -> AnnotationItem | None:
        """Return the selected annotation when present."""

        if self.selection.tier_id is None or self.selection.annotation_id is None:
            return None
        return self.document.find_annotation(self.selection.tier_id, self.selection.annotation_id)

    def create_interval(self, tier_id: str, start_time: float, end_time: float, text: str = "") -> IntervalAnnotation | None:
        """Create an interval in an interval tier."""

        tier = self.document.get_tier(tier_id)
        if tier.tier_type != "interval":
            return None

        left_limit, right_limit = self._available_interval_gap(tier, start_time, end_time)
        if right_limit < left_limit:
            return None

        annotation = IntervalAnnotation(
            start_time=max(left_limit, min(start_time, right_limit)),
            end_time=max(left_limit, min(end_time, right_limit)),
            text=text,
        )
        if annotation.end_time < annotation.start_time:
            return None
        tier.add_annotation(annotation)
        self.select_annotation(tier_id, annotation.id)
        self.document_changed.emit()
        return annotation

    def create_interval_at_time(
        self,
        tier_id: str,
        cursor_time: float,
        duration_seconds: float = DEFAULT_NEW_INTERVAL_DURATION_SECONDS,
    ) -> IntervalAnnotation | None:
        """Create a short interval centered on the requested time."""

        half_duration = max(duration_seconds, 0.0) / 2.0
        return self.create_interval(
            tier_id,
            cursor_time - half_duration,
            cursor_time + half_duration,
        )

    def create_point(self, tier_id: str, time_seconds: float, text: str = "") -> PointAnnotation | None:
        """Create a point in a point tier."""

        tier = self.document.get_tier(tier_id)
        if tier.tier_type != "point":
            return None

        annotation = PointAnnotation(
            time=_clamp(time_seconds, 0.0, self.document.duration_seconds),
            text=text,
        )
        tier.add_annotation(annotation)
        self.select_annotation(tier_id, annotation.id)
        self.document_changed.emit()
        return annotation

    def delete_selected_annotation(self) -> bool:
        """Delete the current annotation selection."""

        tier = self.selected_tier()
        annotation = self.selected_annotation()
        if tier is None or annotation is None:
            return False

        tier.remove_annotation(annotation.id)
        self.clear_selection()
        self.document_changed.emit()
        return True

    def relabel_selected_annotation(self, text: str) -> bool:
        """Update the label for the selected annotation."""

        annotation = self.selected_annotation()
        if annotation is None:
            return False

        annotation.text = text
        self.document_changed.emit()
        return True

    def append_to_selected_annotation_label(self, text: str) -> bool:
        """Append text to the selected annotation label."""

        if not text:
            return False
        annotation = self.selected_annotation()
        if annotation is None:
            return False
        annotation.text = f"{annotation.text}{text}"
        self.document_changed.emit()
        return True

    def trim_selected_annotation_label(self) -> bool:
        """Remove the last character from the selected annotation label."""

        annotation = self.selected_annotation()
        if annotation is None:
            return False
        annotation.text = annotation.text[:-1]
        self.document_changed.emit()
        return True

    def move_interval(self, tier_id: str, annotation_id: str, new_start_time: float, *, announce: bool = True) -> bool:
        """Move an interval while preserving duration and tier ordering constraints."""

        tier = self.document.get_tier(tier_id)
        annotation = tier.find_annotation(annotation_id)
        if tier.tier_type != "interval" or not isinstance(annotation, IntervalAnnotation):
            return False

        previous_annotation, next_annotation = tier.neighbor_annotations(annotation_id)
        interval_duration = annotation.duration
        minimum_start = previous_annotation.end_time if isinstance(previous_annotation, IntervalAnnotation) else 0.0
        maximum_end = next_annotation.start_time if isinstance(next_annotation, IntervalAnnotation) else self.document.duration_seconds
        maximum_start = max(minimum_start, maximum_end - interval_duration)
        annotation.start_time = _clamp(new_start_time, minimum_start, maximum_start)
        annotation.end_time = annotation.start_time + interval_duration
        tier.sort_annotations()
        if announce:
            self.document_changed.emit()
        return True

    def resize_interval_start(self, tier_id: str, annotation_id: str, new_start_time: float, *, announce: bool = True) -> bool:
        """Resize the start boundary of an interval."""

        tier = self.document.get_tier(tier_id)
        annotation = tier.find_annotation(annotation_id)
        if tier.tier_type != "interval" or not isinstance(annotation, IntervalAnnotation):
            return False

        previous_annotation, _next_annotation = tier.neighbor_annotations(annotation_id)
        minimum_start = previous_annotation.end_time if isinstance(previous_annotation, IntervalAnnotation) else 0.0
        annotation.start_time = _clamp(new_start_time, minimum_start, annotation.end_time)
        tier.sort_annotations()
        if announce:
            self.document_changed.emit()
        return True

    def resize_interval_end(self, tier_id: str, annotation_id: str, new_end_time: float, *, announce: bool = True) -> bool:
        """Resize the end boundary of an interval."""

        tier = self.document.get_tier(tier_id)
        annotation = tier.find_annotation(annotation_id)
        if tier.tier_type != "interval" or not isinstance(annotation, IntervalAnnotation):
            return False

        _previous_annotation, next_annotation = tier.neighbor_annotations(annotation_id)
        maximum_end = next_annotation.start_time if isinstance(next_annotation, IntervalAnnotation) else self.document.duration_seconds
        annotation.end_time = _clamp(new_end_time, annotation.start_time, maximum_end)
        tier.sort_annotations()
        if announce:
            self.document_changed.emit()
        return True

    def move_point(self, tier_id: str, annotation_id: str, new_time: float, *, announce: bool = True) -> bool:
        """Move a point annotation horizontally."""

        tier = self.document.get_tier(tier_id)
        annotation = tier.find_annotation(annotation_id)
        if tier.tier_type != "point" or not isinstance(annotation, PointAnnotation):
            return False

        annotation.time = _clamp(new_time, 0.0, self.document.duration_seconds)
        tier.sort_annotations()
        if announce:
            self.document_changed.emit()
        return True

    def split_selected_interval_at_time(self, time_seconds: float) -> IntervalAnnotation | None:
        """Split the selected interval at a cursor time."""

        tier = self.selected_tier()
        annotation = self.selected_annotation()
        if tier is None or tier.tier_type != "interval" or not isinstance(annotation, IntervalAnnotation):
            return None
        if not (annotation.start_time < time_seconds < annotation.end_time):
            return None

        right_interval = IntervalAnnotation(
            start_time=time_seconds,
            end_time=annotation.end_time,
            text="",
        )
        annotation.end_time = time_seconds
        tier.add_annotation(right_interval)
        self.select_annotation(tier.id, right_interval.id)
        self.document_changed.emit()
        return right_interval

    def merge_selected_interval_with_next(self) -> IntervalAnnotation | None:
        """Merge the selected interval with the next interval in the same tier."""

        tier = self.selected_tier()
        annotation = self.selected_annotation()
        if tier is None or tier.tier_type != "interval" or not isinstance(annotation, IntervalAnnotation):
            return None

        _previous_annotation, next_annotation = tier.neighbor_annotations(annotation.id)
        if not isinstance(next_annotation, IntervalAnnotation):
            return None

        annotation.end_time = next_annotation.end_time
        annotation.text = _merge_labels(annotation.text, next_annotation.text)
        tier.remove_annotation(next_annotation.id)
        tier.sort_annotations()
        self.document_changed.emit()
        return annotation

    def _available_interval_gap(self, tier: AnnotationTier, start_time: float, end_time: float) -> tuple[float, float]:
        """Return the available non-overlapping interval gap near a requested span."""

        requested_start = _clamp(min(start_time, end_time), 0.0, self.document.duration_seconds)
        requested_end = _clamp(max(start_time, end_time), 0.0, self.document.duration_seconds)
        requested_center = (requested_start + requested_end) / 2.0
        previous_end = 0.0
        next_start = self.document.duration_seconds

        for annotation in tier.annotations:
            if not isinstance(annotation, IntervalAnnotation):
                continue
            if annotation.end_time <= requested_center:
                previous_end = max(previous_end, annotation.end_time)
                continue
            if annotation.start_time >= requested_center:
                next_start = min(next_start, annotation.start_time)
                break

        return previous_end, next_start


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _merge_labels(left_text: str, right_text: str) -> str:
    if not left_text:
        return right_text
    if not right_text:
        return left_text
    return f"{left_text} {right_text}".strip()
