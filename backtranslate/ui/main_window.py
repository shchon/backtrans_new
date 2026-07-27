import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QFrame, QLabel,
    QScrollArea, QFileDialog, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from backtranslate.services import ConfigService


NAV_STYLE = """
QPushButton {
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    color: #333;
}
QPushButton:hover {
    background: #e8e8e8;
}
QPushButton[active="true"] {
    background: #d0e0ff;
    font-weight: bold;
}
"""


class MainWindow(QMainWindow):
    import_at_path = Signal(str)  # emitted when a favorite dir is clicked

    def __init__(self, config_service=None):
        super().__init__()
        self._config_service = config_service or ConfigService()
        self.setWindowTitle("BackTranslate - 回译训练")
        self.resize(1100, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background: #f5f5f5;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        self.nav_buttons = []
        nav_items = ["学习", "复盘", "收藏夹", "表达库", "设置"]

        for name in nav_items:
            btn = QPushButton(name)
            btn.setStyleSheet(NAV_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self._on_nav(n))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((name, btn))

        # Favorite directories section
        dir_header = QHBoxLayout()
        dir_label = QLabel("常用目录")
        dir_label.setStyleSheet("font-size: 12px; color: #888; font-weight: bold; padding: 8px 4px 4px 4px;")
        dir_header.addWidget(dir_label)
        dir_header.addStretch()
        add_btn = QPushButton("+")
        add_btn.setFixedSize(22, 22)
        add_btn.setStyleSheet(
            "QPushButton { color: #888; border: 1px solid #ccc; border-radius: 3px; font-size: 14px; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )
        add_btn.clicked.connect(self._add_favorite_dir)
        dir_header.addWidget(add_btn)
        sidebar_layout.addLayout(dir_header)

        # Scrollable dir list
        self.dir_scroll = QScrollArea()
        self.dir_scroll.setWidgetResizable(True)
        self.dir_scroll.setFixedHeight(120)
        self.dir_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.dir_container = QWidget()
        self.dir_layout = QVBoxLayout(self.dir_container)
        self.dir_layout.setContentsMargins(0, 0, 0, 0)
        self.dir_layout.setSpacing(1)
        self.dir_layout.setAlignment(Qt.AlignTop)
        self.dir_scroll.setWidget(self.dir_container)
        sidebar_layout.addWidget(self.dir_scroll)

        sidebar_layout.addStretch()
        layout.addWidget(sidebar)

        self._refresh_dir_list()

        # Content area
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.learn_page = None
        self.review_page = None
        self.favorites_page = None
        self.expressions_page = None
        self.settings_page = None

        self._update_nav("学习")

    def _refresh_dir_list(self) -> None:
        while self.dir_layout.count():
            item = self.dir_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cfg = self._config_service.load()
        dirs = cfg.favorite_dirs

        for d in dirs:
            if not os.path.isdir(d):
                continue
            row = QHBoxLayout()
            row.setContentsMargins(4, 0, 4, 0)

            name = os.path.basename(d) or d
            btn = QPushButton(name)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 4px 6px; border: none; "
                "border-radius: 3px; font-size: 12px; color: #555; }"
                "QPushButton:hover { background: #e0e0e0; color: #4a90d9; }"
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(d)
            btn.clicked.connect(lambda checked, path=d: self.import_at_path.emit(path))
            row.addWidget(btn, 1)

            x_btn = QPushButton("×")
            x_btn.setFixedSize(18, 18)
            x_btn.setStyleSheet(
                "QPushButton { color: #aaa; border: none; font-size: 14px; }"
                "QPushButton:hover { color: #e74c3c; }"
            )
            x_btn.clicked.connect(lambda checked, path=d: self._remove_favorite_dir(path))
            row.addWidget(x_btn)

            self.dir_layout.addLayout(row)

    def _add_favorite_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "添加常用目录")
        if not path:
            return
        cfg = self._config_service.load()
        dirs = list(cfg.favorite_dirs)
        if path in dirs:
            return
        dirs.insert(0, path)
        cfg.favorite_dirs = dirs[:10]
        self._config_service.save(cfg)
        self._refresh_dir_list()

    def _remove_favorite_dir(self, path: str) -> None:
        cfg = self._config_service.load()
        dirs = list(cfg.favorite_dirs)
        if path in dirs:
            dirs.remove(path)
        cfg.favorite_dirs = dirs
        self._config_service.save(cfg)
        self._refresh_dir_list()

    def _on_nav(self, name: str) -> None:
        self._update_nav(name)
        if name == "学习" and self.learn_page:
            self.stack.setCurrentWidget(self.learn_page)
        elif name == "复盘" and self.review_page:
            self.stack.setCurrentWidget(self.review_page)
        elif name == "收藏夹" and self.favorites_page:
            self.stack.setCurrentWidget(self.favorites_page)
        elif name == "表达库" and self.expressions_page:
            self.stack.setCurrentWidget(self.expressions_page)
        elif name == "设置" and self.settings_page:
            self.stack.setCurrentWidget(self.settings_page)

    def _update_nav(self, active_name: str) -> None:
        for name, btn in self.nav_buttons:
            btn.setProperty("active", name == active_name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_learn_page(self, widget: QWidget) -> None:
        self.learn_page = widget
        self.stack.addWidget(widget)

    def set_review_page(self, widget: QWidget) -> None:
        self.review_page = widget
        self.stack.addWidget(widget)

    def set_expressions_page(self, widget: QWidget) -> None:
        self.expressions_page = widget
        self.stack.addWidget(widget)

    def set_settings_page(self, widget: QWidget) -> None:
        self.settings_page = widget
        self.stack.addWidget(widget)

    def set_favorites_page(self, widget: QWidget) -> None:
        self.favorites_page = widget
        self.stack.addWidget(widget)

    def navigate_to_review(self) -> None:
        self._on_nav("复盘")

    def navigate_to_learn(self) -> None:
        self._on_nav("学习")
