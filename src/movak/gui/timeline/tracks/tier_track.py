from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QContextMenuEvent, QFont, QFontMetricsF, QKeyEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsObject, QInputDialog, QMenu, QStyle

from ....annotations.model import AnnotationTier, IntervalAnnotation, PointAnnotation
from ...controllers.annotation_editor_controller import AnnotationEditorController
from ...style.palette import Palette
from ..timeline_track import TimelineTrack

TIER_DEFAULT_HEIGHT = 84
TIER_ROW_TOP = 0.14
TIER_ROW_HEIGHT = 0.64
TIER_LINE_Y = 0.5
TIER_CAP_HEIGHT_RATIO = 0.56
TIER_LABEL_OFFSET_PX = 1.0
TIER_LABEL_PADDING_X_PX = 8.0
TIER_LABEL_PADDING_Y_PX = 3.0
TIER_LABEL_RADIUS_PX = 6.0
TIER_LABEL_FONT_SIZE_PX = 11
TIER_MIN_LABEL_WIDTH_PX = 22.0
TIER_BASE_LINE_WIDTH_PX = 1.4
TIER_HOVER_LINE_WIDTH_PX = 2.0
TIER_SELECTED_LINE_WIDTH_PX = 2.5
TIER_LABEL_BACKGROUND_ALPHA = 228
TIER_POINT_LINE_WIDTH_PX = 1.6
TIER_POINT_SELECTED_LINE_WIDTH_PX = 2.4
TIER_POINT_MARKER_RADIUS_PX = 4.5
TIER_INTERVAL_HANDLE_WIDTH_PX = 10.0
TIER_POINT_HIT_WIDTH_PX = 12.0
TIER_ACTIVE_BACKGROUND_ALPHA = 36
TIER_INACTIVE_BACKGROUND_ALPHA = 0
TIER_LANE_LINE_ALPHA = 70
TIER_MINIMUM_VISIBLE_SPAN_SECONDS = 1e-6


class IntervalAnnotationItem(QGraphicsObject):
    """Interactive interval annotation drawn as a light bracketed span."""

    def __init__(
        self,
        tier: AnnotationTier,
        annotation: IntervalAnnotation,
        controller: AnnotationEditorController,
        track: TierTrack,
        color: QColor,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.tier = tier
        self.annotation = annotation
        self.controller = controller
        self.track = track
        self.base_color = QColor(color)
        self._hovered = False
        self._drag_mode: str | None = None
        self._drag_offset_seconds = 0.0
        self._drag_changed = False

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.sync_geometry()

    def sync_geometry(self) -> None:
        """Update item geometry from the current annotation model."""

        self.prepareGeometryChange()
        self.width_seconds = max(
            self.annotation.end_time - self.annotation.start_time,
            TIER_MINIMUM_VISIBLE_SPAN_SECONDS,
        )
        self.setPos(self.annotation.start_time, TIER_ROW_TOP)

    def boundingRect(self) -> QRectF:
        return QRectF(0.0, 0.0, self.width_seconds, TIER_ROW_HEIGHT)

    def shape(self) -> QPainterPath:
        hit_path = QPainterPath()
        hit_path.addRect(self.boundingRect())
        return hit_path

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        is_selected = self.track.is_annotation_selected(self.annotation.id)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver) or self._hovered
        line_y = TIER_ROW_HEIGHT * TIER_LINE_Y
        cap_height = TIER_ROW_HEIGHT * TIER_CAP_HEIGHT_RATIO
        cap_top = line_y - (cap_height / 2.0)
        cap_bottom = line_y + (cap_height / 2.0)

        line_pen = QPen(self._line_color(is_hovered=is_hovered, is_selected=is_selected))
        line_pen.setCosmetic(True)
        line_pen.setWidthF(self._line_width_px(is_hovered=is_hovered, is_selected=is_selected))
        line_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(line_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(0.0, line_y), QPointF(self.width_seconds, line_y))
        painter.drawLine(QPointF(0.0, cap_top), QPointF(0.0, cap_bottom))
        painter.drawLine(QPointF(self.width_seconds, cap_top), QPointF(self.width_seconds, cap_bottom))

        self._paint_label(painter, line_y=line_y, is_hovered=is_hovered, is_selected=is_selected)
        painter.restore()

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        self.track.begin_item_interaction()
        self.track.activate_tier()
        self.controller.select_annotation(self.tier.id, self.annotation.id)
        self.track.setFocus(Qt.FocusReason.MouseFocusReason)

        current_time = self.track.scene_time(event.scenePos())
        handle_width_seconds = self.track.seconds_from_pixels(TIER_INTERVAL_HANDLE_WIDTH_PX)
        if event.pos().x() <= handle_width_seconds:
            self._drag_mode = "resize_left"
        elif event.pos().x() >= self.width_seconds - handle_width_seconds:
            self._drag_mode = "resize_right"
        else:
            self._drag_mode = "move"
            self._drag_offset_seconds = current_time - self.annotation.start_time
        self._drag_changed = False
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_mode is None:
            super().mouseMoveEvent(event)
            return

        current_time = self.track.scene_time(event.scenePos())
        if self._drag_mode == "resize_left":
            self.controller.resize_interval_start(self.tier.id, self.annotation.id, current_time, announce=False)
            self.track.set_shared_cursor_time(self.annotation.start_time)
        elif self._drag_mode == "resize_right":
            self.controller.resize_interval_end(self.tier.id, self.annotation.id, current_time, announce=False)
            self.track.set_shared_cursor_time(self.annotation.end_time)
        else:
            self.controller.move_interval(
                self.tier.id,
                self.annotation.id,
                current_time - self._drag_offset_seconds,
                announce=False,
            )
        self._drag_changed = True
        self.sync_geometry()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_mode is not None and self._drag_changed:
            self.controller.document_changed.emit()
        self._drag_mode = None
        self._drag_changed = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.track.edit_selected_annotation_label()
        event.accept()

    def _paint_label(self, painter: QPainter, *, line_y: float, is_hovered: bool, is_selected: bool) -> None:
        transform = painter.worldTransform()
        x_scale = abs(transform.m11())
        y_scale = max(abs(transform.m22()), 1e-6)
        if x_scale <= 0.0:
            return

        available_width_px = max(0.0, (self.width_seconds * x_scale) - (2.0 * TIER_LABEL_PADDING_X_PX) - 8.0)
        if available_width_px < TIER_MIN_LABEL_WIDTH_PX:
            return

        font = QFont()
        font.setPixelSize(TIER_LABEL_FONT_SIZE_PX)
        metrics = QFontMetricsF(font)
        elided_text = metrics.elidedText(
            self.annotation.text,
            Qt.TextElideMode.ElideRight,
            available_width_px,
        )
        if not elided_text:
            return

        text_width = metrics.horizontalAdvance(elided_text)
        text_height = metrics.height()
        patch_width = text_width + (2.0 * TIER_LABEL_PADDING_X_PX)
        patch_height = text_height + (2.0 * TIER_LABEL_PADDING_Y_PX)
        device_center = transform.map(QPointF(self.width_seconds / 2.0, line_y - (TIER_LABEL_OFFSET_PX / y_scale)))
        patch_rect = QRectF(
            device_center.x() - (patch_width / 2.0),
            device_center.y() - (patch_height / 2.0),
            patch_width,
            patch_height,
        )
        text_rect = QRectF(
            patch_rect.left() + TIER_LABEL_PADDING_X_PX,
            patch_rect.top() + TIER_LABEL_PADDING_Y_PX,
            text_width,
            text_height,
        )

        painter.save()
        painter.resetTransform()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._label_background(is_hovered=is_hovered, is_selected=is_selected))
        painter.drawRoundedRect(patch_rect, TIER_LABEL_RADIUS_PX, TIER_LABEL_RADIUS_PX)
        painter.setFont(font)
        painter.setPen(self._text_color(is_hovered=is_hovered, is_selected=is_selected))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elided_text)
        painter.restore()

    def _line_color(self, *, is_hovered: bool, is_selected: bool) -> QColor:
        color = QColor(self.base_color)
        if is_selected:
            return color.lighter(155)
        if is_hovered:
            return color.lighter(128)
        return color.lighter(115)

    def _label_background(self, *, is_hovered: bool, is_selected: bool) -> QColor:
        if is_selected:
            background = QColor(self.base_color).lighter(120)
            background.setAlpha(240)
            return background
        if is_hovered:
            background = QColor(Palette.SURFACE_ELEVATED)
            background.setAlpha(238)
            return background
        background = QColor(Palette.PANEL)
        background.setAlpha(TIER_LABEL_BACKGROUND_ALPHA)
        return background

    def _text_color(self, *, is_hovered: bool, is_selected: bool) -> QColor:
        if is_selected:
            return QColor(Palette.TEXT_ON_ACCENT)
        if is_hovered:
            return QColor(Palette.TEXT)
        return QColor(Palette.TEXT_MUTED).lighter(115)

    def _line_width_px(self, *, is_hovered: bool, is_selected: bool) -> float:
        if is_selected:
            return TIER_SELECTED_LINE_WIDTH_PX
        if is_hovered:
            return TIER_HOVER_LINE_WIDTH_PX
        return TIER_BASE_LINE_WIDTH_PX


class PointAnnotationItem(QGraphicsObject):
    """Interactive point annotation drawn as a vertical marker."""

    def __init__(
        self,
        tier: AnnotationTier,
        annotation: PointAnnotation,
        controller: AnnotationEditorController,
        track: TierTrack,
        color: QColor,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.tier = tier
        self.annotation = annotation
        self.controller = controller
        self.track = track
        self.base_color = QColor(color)
        self._hovered = False
        self._dragging = False

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.sync_geometry()

    def sync_geometry(self) -> None:
        self.prepareGeometryChange()
        self.hit_width_seconds = max(
            self.track.seconds_from_pixels(TIER_POINT_HIT_WIDTH_PX),
            TIER_MINIMUM_VISIBLE_SPAN_SECONDS,
        )
        self.setPos(self.annotation.time, TIER_ROW_TOP)

    def boundingRect(self) -> QRectF:
        return QRectF(-self.hit_width_seconds / 2.0, 0.0, self.hit_width_seconds, TIER_ROW_HEIGHT)

    def shape(self) -> QPainterPath:
        hit_path = QPainterPath()
        hit_path.addRect(self.boundingRect())
        return hit_path

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        is_selected = self.track.is_annotation_selected(self.annotation.id)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver) or self._hovered
        line_color = self._line_color(is_hovered=is_hovered, is_selected=is_selected)

        line_pen = QPen(line_color)
        line_pen.setCosmetic(True)
        line_pen.setWidthF(TIER_POINT_SELECTED_LINE_WIDTH_PX if is_selected else TIER_POINT_LINE_WIDTH_PX)
        painter.setPen(line_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(0.0, 0.08), QPointF(0.0, TIER_ROW_HEIGHT - 0.08))

        marker_pen = QPen(line_color)
        marker_pen.setCosmetic(True)
        marker_pen.setWidthF(1.2)
        painter.setPen(marker_pen)
        painter.setBrush(line_color)
        painter.drawEllipse(
            QPointF(0.0, TIER_ROW_HEIGHT * 0.28),
            self.track.seconds_from_pixels(TIER_POINT_MARKER_RADIUS_PX),
            TIER_ROW_HEIGHT * 0.10,
        )
        self._paint_label(painter, is_hovered=is_hovered, is_selected=is_selected)
        painter.restore()

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.track.begin_item_interaction()
        self.track.activate_tier()
        self.controller.select_annotation(self.tier.id, self.annotation.id)
        self.track.setFocus(Qt.FocusReason.MouseFocusReason)
        self._dragging = True
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            super().mouseMoveEvent(event)
            return
        self.controller.move_point(self.tier.id, self.annotation.id, self.track.scene_time(event.scenePos()), announce=False)
        self.sync_geometry()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self.controller.document_changed.emit()
        self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.track.edit_selected_annotation_label()
        event.accept()

    def _paint_label(self, painter: QPainter, *, is_hovered: bool, is_selected: bool) -> None:
        if not self.annotation.text:
            return

        transform = painter.worldTransform()
        y_scale = max(abs(transform.m22()), 1e-6)
        device_anchor = transform.map(QPointF(0.0, TIER_ROW_HEIGHT * 0.18))

        font = QFont()
        font.setPixelSize(TIER_LABEL_FONT_SIZE_PX)
        metrics = QFontMetricsF(font)
        text_width = metrics.horizontalAdvance(self.annotation.text)
        text_height = metrics.height()
        patch_width = text_width + (2.0 * TIER_LABEL_PADDING_X_PX)
        patch_height = text_height + (2.0 * TIER_LABEL_PADDING_Y_PX)
        patch_rect = QRectF(
            device_anchor.x() + 6.0,
            device_anchor.y() - patch_height - (TIER_LABEL_OFFSET_PX / y_scale),
            patch_width,
            patch_height,
        )
        text_rect = QRectF(
            patch_rect.left() + TIER_LABEL_PADDING_X_PX,
            patch_rect.top() + TIER_LABEL_PADDING_Y_PX,
            text_width,
            text_height,
        )

        painter.save()
        painter.resetTransform()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._label_background(is_hovered=is_hovered, is_selected=is_selected))
        painter.drawRoundedRect(patch_rect, TIER_LABEL_RADIUS_PX, TIER_LABEL_RADIUS_PX)
        painter.setFont(font)
        painter.setPen(QColor(Palette.TEXT_ON_ACCENT) if is_selected else QColor(Palette.TEXT))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.annotation.text)
        painter.restore()

    def _line_color(self, *, is_hovered: bool, is_selected: bool) -> QColor:
        color = QColor(self.base_color)
        if is_selected:
            return color.lighter(160)
        if is_hovered:
            return color.lighter(132)
        return color.lighter(118)

    def _label_background(self, *, is_hovered: bool, is_selected: bool) -> QColor:
        if is_selected:
            background = QColor(self.base_color).lighter(120)
            background.setAlpha(238)
            return background
        if is_hovered:
            background = QColor(Palette.SURFACE_ELEVATED)
            background.setAlpha(232)
            return background
        background = QColor(Palette.PANEL)
        background.setAlpha(TIER_LABEL_BACKGROUND_ALPHA)
        return background


class TierTrack(TimelineTrack):
    """Editable annotation tier aligned to the shared timeline axis."""

    def __init__(
        self,
        tier: AnnotationTier,
        controller: AnnotationEditorController,
        parent=None,
    ) -> None:
        super().__init__(tier.name, parent)
        self.tier = tier
        self.controller = controller
        self._items: list[object] = []
        self._suppress_next_scene_click = False

        self.plot_widget.setYRange(0.0, 1.0, padding=0.0)
        self.plot_widget.setLimits(yMin=0.0, yMax=1.0, minYRange=1.0, maxYRange=1.0)
        self.setMinimumHeight(TIER_DEFAULT_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.controller.document_changed.connect(self._rerender_from_controller)
        self.controller.selection_changed.connect(self._update_selection_state)
        self._apply_track_background()

    def set_time_bounds(self, total_duration: float) -> None:
        super().set_time_bounds(total_duration)
        self.controller.set_document_duration(total_duration)

    def render(self, start_time: float, end_time: float) -> None:
        self._clear_items()
        self._apply_track_background()
        self._add_lane_guides()

        item_color = self._tier_color()
        for annotation in self.tier.visible_annotations(start_time, end_time):
            if isinstance(annotation, IntervalAnnotation):
                item = IntervalAnnotationItem(self.tier, annotation, self.controller, self, item_color)
            else:
                item = PointAnnotationItem(self.tier, annotation, self.controller, self, item_color)
            self.plot_widget.addItem(item)
            self._items.append(item)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._handle_direct_label_edit(event):
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            self.controller.delete_selected_annotation()
            event.accept()
            return
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.edit_selected_annotation_label()
            event.accept()
            return
        if event.key() == Qt.Key.Key_I and self.tier.tier_type == "interval":
            self.activate_tier()
            self.controller.create_interval_at_time(self.tier.id, self.current_cursor_time())
            event.accept()
            return
        if event.key() == Qt.Key.Key_P and self.tier.tier_type == "point":
            self.activate_tier()
            self.controller.create_point(self.tier.id, self.current_cursor_time())
            event.accept()
            return
        if event.key() == Qt.Key.Key_S and self.tier.tier_type == "interval":
            self.controller.split_selected_interval_at_time(self.current_cursor_time())
            event.accept()
            return
        if event.key() == Qt.Key.Key_M and self.tier.tier_type == "interval":
            self.controller.merge_selected_interval_with_next()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        self.activate_tier()

        if self.tier.tier_type == "interval":
            create_action = menu.addAction("Create Interval at Cursor")
            split_action = menu.addAction("Split Selected Interval at Cursor")
            merge_action = menu.addAction("Merge Selected Interval with Next")
        else:
            create_action = menu.addAction("Create Point at Cursor")
            split_action = None
            merge_action = None
        edit_action = menu.addAction("Edit Selected Label")
        delete_action = menu.addAction("Delete Selected Annotation")

        chosen_action = menu.exec(event.globalPos())
        if chosen_action is None:
            return
        if chosen_action == create_action:
            if self.tier.tier_type == "interval":
                self.controller.create_interval_at_time(self.tier.id, self.current_cursor_time())
            else:
                self.controller.create_point(self.tier.id, self.current_cursor_time())
            return
        if split_action is not None and chosen_action == split_action:
            self.controller.split_selected_interval_at_time(self.current_cursor_time())
            return
        if merge_action is not None and chosen_action == merge_action:
            self.controller.merge_selected_interval_with_next()
            return
        if chosen_action == edit_action:
            self.edit_selected_annotation_label()
            return
        if chosen_action == delete_action:
            self.controller.delete_selected_annotation()

    def begin_item_interaction(self) -> None:
        """Prevent the next scene click from being treated as empty space."""

        self._suppress_next_scene_click = True

    def activate_tier(self) -> None:
        """Make this tier the current editing target."""

        self.controller.select_tier(self.tier.id)

    def is_annotation_selected(self, annotation_id: str) -> bool:
        """Return whether an annotation is currently selected in this tier."""

        return (
            self.controller.selection.tier_id == self.tier.id
            and self.controller.selection.annotation_id == annotation_id
        )

    def current_cursor_time(self) -> float:
        """Return the current shared playhead time."""

        if self.timeline_viewport is None:
            return 0.0
        return self.timeline_viewport.cursor_time

    def seconds_from_pixels(self, pixel_width: float) -> float:
        """Convert a pixel width into timeline seconds for hit geometry."""

        view_range = self.plot_widget.getViewBox().viewRange()[0]
        visible_duration = max(view_range[1] - view_range[0], TIER_MINIMUM_VISIBLE_SPAN_SECONDS)
        viewport_width = max(float(self.plot_widget.viewport().width()), 1.0)
        return visible_duration * (pixel_width / viewport_width)

    def scene_time(self, scene_pos: QPointF) -> float:
        """Map a scene position to timeline time in seconds."""

        return float(self.view_box.mapSceneToView(scene_pos).x())

    def set_shared_cursor_time(self, time_seconds: float) -> None:
        """Move the shared playhead so all tracks reflect an edit target."""

        if self.timeline_viewport is None:
            return
        self.timeline_viewport.set_cursor_time(time_seconds)

    def edit_selected_annotation_label(self) -> None:
        """Prompt for a new label for the selected annotation."""

        if self.controller.selection.tier_id != self.tier.id:
            return
        annotation = self.controller.selected_annotation()
        if annotation is None:
            return
        label_text, accepted = QInputDialog.getText(
            self,
            "Edit Annotation Label",
            f"{self.tier.name} label:",
            text=annotation.text,
        )
        if accepted:
            self.controller.relabel_selected_annotation(label_text)

    def _handle_direct_label_edit(self, event: QKeyEvent) -> bool:
        """Apply direct typing to the selected annotation label when possible."""

        if self.controller.selection.tier_id != self.tier.id:
            return False
        if self.controller.selection.annotation_id is None:
            return False

        modifiers = event.modifiers()
        if modifiers & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.MetaModifier
        ):
            return False

        if event.key() == Qt.Key.Key_Backspace:
            return self.controller.trim_selected_annotation_label()

        typed_text = event.text()
        if not typed_text:
            return False
        if any(character.isprintable() and not character.isspace() for character in typed_text):
            return self.controller.append_to_selected_annotation_label(typed_text)
        if typed_text == " ":
            return self.controller.append_to_selected_annotation_label(typed_text)
        return False

    def _handle_scene_click(self, event) -> None:
        if self._suppress_next_scene_click:
            self._suppress_next_scene_click = False
            return
        self.activate_tier()
        self.controller.clear_selection()
        super()._handle_scene_click(event)

    def _rerender_from_controller(self) -> None:
        self.render(self.visible_start_time, self.visible_end_time)

    def _update_selection_state(self, *_args) -> None:
        self._apply_track_background()
        for item in self._items:
            if hasattr(item, "update"):
                item.update()

    def _apply_track_background(self) -> None:
        background = QColor(Palette.PANEL)
        if self.controller.active_tier_id == self.tier.id:
            highlight = QColor(Palette.ACCENT)
            highlight.setAlpha(TIER_ACTIVE_BACKGROUND_ALPHA)
            background = highlight
        else:
            background.setAlpha(TIER_INACTIVE_BACKGROUND_ALPHA)
        self.view_box.setBackgroundColor(background)

    def _add_lane_guides(self) -> None:
        line_color = QColor(Palette.BORDER_STRONG)
        line_color.setAlpha(TIER_LANE_LINE_ALPHA)
        top_line = self.plot_widget.plot(
            [self.visible_start_time, self.visible_end_time],
            [TIER_ROW_TOP, TIER_ROW_TOP],
            pen=QPen(line_color, 1.0),
        )
        bottom_line = self.plot_widget.plot(
            [self.visible_start_time, self.visible_end_time],
            [TIER_ROW_TOP + TIER_ROW_HEIGHT, TIER_ROW_TOP + TIER_ROW_HEIGHT],
            pen=QPen(line_color, 1.0),
        )
        top_line.setZValue(-10)
        bottom_line.setZValue(-10)
        self._items.extend([top_line, bottom_line])

    def _clear_items(self) -> None:
        for item in self._items:
            self.plot_widget.removeItem(item)
        self._items.clear()

    def _tier_color(self) -> QColor:
        if self.tier.tier_type == "point":
            return QColor(Palette.ACCENT)
        if self.tier.name.lower().startswith("word"):
            return QColor(Palette.ACCENT_STRONG)
        return QColor(Palette.ACCENT_VIOLET_SOFT)


def build_tracks(
    tiers: Iterable[AnnotationTier],
    controller: AnnotationEditorController,
    parent=None,
) -> list[TierTrack]:
    """Return one editable track widget per annotation tier."""

    return [TierTrack(tier=tier, controller=controller, parent=parent) for tier in tiers]
