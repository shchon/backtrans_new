from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPlainTextEdit, QPushButton,
    QLabel, QGroupBox, QMessageBox,
)
from PySide6.QtCore import QThread, Signal
import requests
import json
from backtranslate.models import AppSettings
from backtranslate.services import ConfigService
from backtranslate.defaults import (
    DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_PROMPT_TEMPLATE,
)


class _TestWorker(QThread):
    finished = Signal(bool, str)  # success, message

    def __init__(self, base_url: str, api_key: str, model: str):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def run(self) -> None:
        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Say 'OK' and nothing else."}],
            "max_tokens": 10,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                model_used = data.get("model", self.model)
                self.finished.emit(True, f"连接成功\n模型: {model_used}")
            else:
                detail = ""
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text[:200]
                self.finished.emit(False, f"API 返回错误 ({resp.status_code})\n{detail}")
        except requests.RequestException as e:
            self.finished.emit(False, f"连接失败\n{str(e)[:200]}")


class SettingsPage(QWidget):
    def __init__(self, config_service=None):
        super().__init__()
        self._config_service = config_service or ConfigService()
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # AI Config group
        ai_group = QGroupBox("AI 配置")
        ai_form = QFormLayout(ai_group)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText(
            f"如 {DEFAULT_BASE_URL} 或直接填入完整 /chat/completions 地址"
        )
        ai_form.addRow("Base URL:", self.base_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入 API Key")
        ai_form.addRow("API Key:", self.api_key_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(DEFAULT_MODEL)
        ai_form.addRow("Model:", self.model_input)

        self.context_n_input = QSpinBox()
        self.context_n_input.setRange(0, 5)
        self.context_n_input.setValue(1)
        ai_form.addRow("上下文字数:", self.context_n_input)

        # Test button
        test_layout = QHBoxLayout()
        test_layout.addStretch()
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setStyleSheet(
            "QPushButton { color: #4a90d9; border: 1px solid #4a90d9; "
            "padding: 6px 16px; border-radius: 4px; }"
            "QPushButton:hover { background: #e8f0fe; }"
            "QPushButton:disabled { color: #999; border-color: #ccc; }"
        )
        self.test_btn.clicked.connect(self._test_connection)
        test_layout.addWidget(self.test_btn)
        ai_form.addRow("", test_layout)

        layout.addWidget(ai_group)

        # Display group
        display_group = QGroupBox("显示")
        display_form = QFormLayout(display_group)

        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(10, 24)
        self.font_size_input.setValue(14)
        self.font_size_input.setSuffix(" pt")
        display_form.addRow("复盘字体大小:", self.font_size_input)

        layout.addWidget(display_group)

        # Prompt group
        prompt_group = QGroupBox("Prompt 模板")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_help = QLabel(
            "可用变量: {context}（上下文字幕）、{user_input}（你的翻译）、{official}（官方字幕）"
        )
        prompt_help.setStyleSheet("color: #666; font-size: 12px;")
        prompt_layout.addWidget(prompt_help)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMinimumHeight(250)
        prompt_layout.addWidget(self.prompt_edit)

        layout.addWidget(prompt_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton("恢复默认 Prompt")
        reset_btn.clicked.connect(self._reset_prompt)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 24px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #357abd; }"
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _test_connection(self):
        base_url = self.base_url_input.text().strip() or DEFAULT_BASE_URL
        api_key = self.api_key_input.text().strip()
        model = self.model_input.text().strip() or DEFAULT_MODEL

        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key。")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")

        self._tester = _TestWorker(base_url, api_key, model)
        self._tester.finished.connect(self._on_test_finished)
        self._tester.start()

    def _on_test_finished(self, success: bool, message: str):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        if success:
            QMessageBox.information(self, "连接成功", message)
        else:
            QMessageBox.warning(self, "连接失败", message)

    def _load_config(self):
        settings = self._config_service.load()
        self.base_url_input.setText(settings.base_url)
        self.api_key_input.setText(settings.api_key)
        self.model_input.setText(settings.model)
        self.context_n_input.setValue(settings.context_n)
        self.font_size_input.setValue(settings.font_size)
        self.prompt_edit.setPlainText(settings.prompt_template)

    def _reset_prompt(self):
        self.prompt_edit.setPlainText(DEFAULT_PROMPT_TEMPLATE)

    def _save(self):
        settings = AppSettings(
            base_url=self.base_url_input.text().strip() or DEFAULT_BASE_URL,
            api_key=self.api_key_input.text().strip(),
            model=self.model_input.text().strip() or DEFAULT_MODEL,
            context_n=self.context_n_input.value(),
            font_size=self.font_size_input.value(),
            prompt_template=self.prompt_edit.toPlainText() or DEFAULT_PROMPT_TEMPLATE,
        )
        self._config_service.save(settings)
        QMessageBox.information(self, "保存成功", "设置已保存。")
