from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..style.spacing import Spacing


class Panel(QFrame):
    """Reusable rounded panel shell with consistent spacing."""

    def __init__(
        self,
        title: str | None = None,
        parent: QWidget | None = None,
        *,
        subtitle: str | None = None,
        eyebrow: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panel")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        self.layout.setSpacing(Spacing.MD)

        self.header = QWidget(self)
        self.header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, Spacing.MD)
        header_layout.setSpacing(Spacing.MD)

        self.header_text = QWidget(self.header)
        header_text_layout = QVBoxLayout(self.header_text)
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(Spacing.XXS)

        self.eyebrow_label = QLabel(self.header_text)
        self.eyebrow_label.setObjectName("eyebrowLabel")
        self.eyebrow_label.setVisible(False)

        self.title_label = QLabel(self.header_text)
        self.title_label.setObjectName("panelTitle")
        self.title_label.setVisible(bool(title))

        self.subtitle_label = QLabel(self.header_text)
        self.subtitle_label.setObjectName("panelSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))

        header_text_layout.addWidget(self.eyebrow_label)
        header_text_layout.addWidget(self.title_label)
        header_text_layout.addWidget(self.subtitle_label)

        self.tools = QWidget(self.header)
        self.tools.setObjectName("panelTools")
        self.tools_layout = QHBoxLayout(self.tools)
        self.tools_layout.setContentsMargins(0, 0, 0, 0)
        self.tools_layout.setSpacing(Spacing.SM)

        header_layout.addWidget(self.header_text, 1)
        header_layout.addWidget(self.tools)

        self.body = QWidget(self)
        self.body.setObjectName("panelBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(Spacing.MD)

        self.layout.addWidget(self.header)
        self.layout.addWidget(self.body, 1)

        self.set_header(title=title, subtitle=subtitle, eyebrow=eyebrow)

    def set_header(
        self,
        *,
        title: str | None = None,
        subtitle: str | None = None,
        eyebrow: str | None = None,
    ) -> None:
        self.title_label.setText(title or "")
        self.title_label.setVisible(bool(title))
        self.subtitle_label.setText(subtitle or "")
        self.subtitle_label.setVisible(bool(subtitle))
        self.eyebrow_label.setText(eyebrow or "")
        self.eyebrow_label.setVisible(bool(eyebrow))
