from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QLineEdit, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt

from backtranslate.services import ExpressionService


class ExpressionsPage(QWidget):
    def __init__(self, expression_service=None):
        super().__init__()
        self._expression_service = expression_service or ExpressionService()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("表达库")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索表达...")
        self.search_input.textChanged.connect(self._filter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

    def _refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        expressions = self._expression_service.list_all()
        query = self.search_input.text().strip().lower()

        for expr in expressions:
            if query and query not in expr["phrase"].lower():
                continue

            frame = QFrame()
            frame.setStyleSheet(
                "QFrame { border: 1px solid #ddd; border-radius: 6px; "
                "margin: 4px 0; padding: 8px; }"
            )
            row = QHBoxLayout(frame)

            phrase_label = QLabel(expr["phrase"])
            phrase_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            row.addWidget(phrase_label)

            if expr.get("notes"):
                notes_label = QLabel(expr["notes"])
                notes_label.setStyleSheet("color: #666;")
                row.addWidget(notes_label)

            row.addStretch()

            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("color: #e74c3c; border: none;")
            delete_btn.clicked.connect(
                lambda checked, eid=expr["id"]: self._delete_expression(eid)
            )
            row.addWidget(delete_btn)

            self.list_layout.addWidget(frame)

        if self.list_layout.count() == 0:
            empty = QLabel("还没有收藏的表达")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #999; font-size: 16px; margin-top: 60px;")
            self.list_layout.addWidget(empty)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _filter(self):
        self._refresh()

    def _delete_expression(self, expression_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个表达吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._expression_service.delete(expression_id)
            self._refresh()
