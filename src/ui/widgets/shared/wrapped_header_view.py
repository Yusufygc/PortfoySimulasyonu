from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QHeaderView, QStyle, QStyleOptionHeader


class WrappedHeaderView(QHeaderView):
    """Table header that wraps long labels into two lines."""

    H_PADDING = 8
    V_PADDING = 6
    MIN_HEIGHT = 52
    HEADER_TEXT_COLOR = QColor("#020617")

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignCenter)
        self.setMinimumHeight(self.MIN_HEIGHT)
        font = self.font()
        font.setBold(True)
        self.setFont(font)

    def sectionSizeFromContents(self, logical_index: int) -> QSize:
        base = super().sectionSizeFromContents(logical_index)
        model = self.model()
        if model is None:
            return QSize(base.width(), max(base.height(), self.MIN_HEIGHT))

        text = str(model.headerData(logical_index, self.orientation(), Qt.DisplayRole) or "")
        available_width = max(
            self.sectionSize(logical_index) - (self.H_PADDING * 2),
            self.minimumSectionSize() - (self.H_PADDING * 2),
            1,
        )
        text_rect = self.fontMetrics().boundingRect(
            QRect(0, 0, available_width, self.MIN_HEIGHT * 2),
            Qt.AlignCenter | Qt.TextWordWrap,
            text,
        )
        height = max(base.height(), text_rect.height() + (self.V_PADDING * 2), self.MIN_HEIGHT)
        return QSize(max(base.width(), self.minimumSectionSize()), height)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        height = self.MIN_HEIGHT
        for logical_index in range(self.count()):
            height = max(height, self.sectionSizeFromContents(logical_index).height())
        return QSize(base.width(), height)

    def paintSection(self, painter: QPainter, rect, logical_index: int):
        if not rect.isValid():
            return

        painter.save()
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logical_index
        option.text = ""
        option.position = self._position_for_section(logical_index)
        option.selectedPosition = QStyleOptionHeader.NotAdjacent
        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logical_index:
            option.sortIndicator = (
                QStyleOptionHeader.SortDown
                if self.sortIndicatorOrder() == Qt.DescendingOrder
                else QStyleOptionHeader.SortUp
            )
        else:
            option.sortIndicator = QStyleOptionHeader.None_

        self.style().drawControl(QStyle.CE_HeaderSection, option, painter, self)

        text = str(self.model().headerData(logical_index, self.orientation(), Qt.DisplayRole) or "")
        text_rect = rect.adjusted(self.H_PADDING, self.V_PADDING, -self.H_PADDING, -self.V_PADDING)
        painter.setFont(self.font())
        painter.setPen(self.HEADER_TEXT_COLOR)
        painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, text)
        painter.restore()

    def _position_for_section(self, logical_index: int):
        if self.count() == 1:
            return QStyleOptionHeader.OnlyOneSection
        if logical_index == 0:
            return QStyleOptionHeader.Beginning
        if logical_index == self.count() - 1:
            return QStyleOptionHeader.End
        return QStyleOptionHeader.Middle
