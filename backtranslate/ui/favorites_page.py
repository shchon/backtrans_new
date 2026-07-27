from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QMessageBox,
)
from PySide6.QtCore import Signal, Qt

from backtranslate.services import SubtitleService, FavoriteService


class FavoritesPage(QWidget):
    start_favorites_review = Signal(list)

    def __init__(self, subtitle_service=None, favorite_service=None):
        super().__init__()
        self._subtitle_service = subtitle_service or SubtitleService()
        self._favorite_service = favorite_service or FavoriteService()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("收藏夹")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Top bar
        top = QHBoxLayout()
        review_btn = QPushButton("复习收藏")
        review_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #357abd; }"
        )
        review_btn.clicked.connect(self._start_review)
        top.addWidget(review_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #c0392b; }"
        )
        clear_btn.clicked.connect(self._clear_all_favorites)
        top.addWidget(clear_btn)

        top.addStretch()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #666;")
        top.addWidget(self.count_label)
        layout.addLayout(top)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        # Empty state
        self.empty_label = QLabel("暂无收藏句子")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-size: 16px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        favorites = self._favorite_service.list_all()
        self.count_label.setText(f"共 {len(favorites)} 句")

        if not favorites:
            self.empty_label.setVisible(True)
            return
        self.empty_label.setVisible(False)

        for i, fav in enumerate(favorites):
            row = self._build_row(i + 1, fav)
            self.list_layout.addWidget(row)

    def _build_row(self, display_idx, fav):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { border: 1px solid #ddd; border-radius: 6px; margin: 4px 0; padding: 8px; }"
        )
        row_layout = QHBoxLayout(frame)
        row_layout.setContentsMargins(8, 6, 8, 6)

        idx_label = QLabel(f"#{display_idx}")
        idx_label.setStyleSheet("color: #999; font-size: 12px;")
        row_layout.addWidget(idx_label)

        ch_label = QLabel(fav["chinese"])
        ch_label.setStyleSheet("font-size: 14px;")
        ch_label.setWordWrap(True)
        row_layout.addWidget(ch_label, 1)

        # English toggle
        en_btn = QPushButton("查看英文 ▸")
        en_btn.setStyleSheet(
            "color: #4a90d9; border: none; font-size: 12px; padding: 2px 6px;"
        )
        en_label = QLabel(fav["english_official"])
        en_label.setStyleSheet(
            "color: #666; font-size: 13px; font-style: italic; "
            "padding: 4px 8px; background: #fafafa; border-radius: 3px;"
        )
        en_label.setWordWrap(True)
        en_label.setVisible(False)
        en_btn.clicked.connect(
            lambda checked, btn=en_btn, lbl=en_label: lbl.setVisible(not lbl.isVisible())
        )
        row_layout.addWidget(en_btn)
        row_layout.addWidget(en_label)

        # Delete button
        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setStyleSheet(
            "QPushButton { color: #e74c3c; border: none; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { color: #c0392b; }"
        )
        subtitle_id = fav["id"]
        del_btn.clicked.connect(
            lambda checked, sid=subtitle_id: self._delete_favorite(sid)
        )
        row_layout.addWidget(del_btn)

        return frame

    def _delete_favorite(self, subtitle_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要从收藏夹中删除此句子吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._favorite_service.remove(subtitle_id)
            self._refresh()

    def _clear_all_favorites(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空收藏夹中所有句子吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._favorite_service.clear_all()
            self._refresh()

    def _start_review(self):
        favorites = self._favorite_service.list_all()
        if not favorites:
            return
        self.start_favorites_review.emit(favorites)
