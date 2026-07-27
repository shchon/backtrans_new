import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QLineEdit, QMessageBox,
    QTextBrowser,
)
from PySide6.QtCore import Signal, Qt
from backtranslate.services import (
    SubtitleService, TranslationService, EvaluationService,
    ExpressionService, FavoriteService, ConfigService,
)


class ReviewPage(QWidget):
    redo_submitted = Signal(int, int, str, str)  # eval_id, subtitle_id, input, official
    retry_requested = Signal(int, int, str, str)  # eval_id, subtitle_id, user_input, official

    def __init__(self,
                 subtitle_service=None,
                 translation_service=None,
                 evaluation_service=None,
                 expression_service=None,
                 favorite_service=None,
                 config_service=None):
        super().__init__()
        self._subtitle_service = subtitle_service or SubtitleService()
        self._translation_service = translation_service or TranslationService()
        self._evaluation_service = evaluation_service or EvaluationService()
        self._expression_service = expression_service or ExpressionService()
        self._favorite_service = favorite_service or FavoriteService()
        self._config_service = config_service or ConfigService()
        self.session_id = None
        self.only_translated = False
        self.subtitle_rows = []
        self.detail_widgets = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("复盘")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(self.count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

    def load_session(self, session_id, only_translated=False):
        self.session_id = session_id
        self.only_translated = only_translated
        self.subtitle_rows = self._subtitle_service.get_by_session(session_id)
        self._refresh_list()

    def update_evaluation(self, subtitle_id):
        """Called when a new evaluation result arrives for a specific subtitle."""
        sub = self._subtitle_by_id(subtitle_id)
        if sub is None:
            return
        if str(subtitle_id) in self.detail_widgets:
            old_widget = self.detail_widgets[str(subtitle_id)]
            pos = self.list_layout.indexOf(old_widget)
            if pos >= 0:
                self.list_layout.takeAt(pos)
            old_widget.deleteLater()
        new_widget = self._build_row_widget(sub)
        # Insert at correct position to maintain idx order
        insert_pos = self.list_layout.count()
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            w = item.widget() if item else None
            if w and hasattr(w, "subtitle_idx") and w.subtitle_idx > sub.idx:
                insert_pos = i
                break
        self.list_layout.insertWidget(insert_pos, new_widget)
        self.detail_widgets[str(subtitle_id)] = new_widget

    def _refresh_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.detail_widgets.clear()

        completed = 0
        visible_count = 0
        for sub in self.subtitle_rows:
            if self.only_translated and self._get_latest_translation_id(sub.id) is None:
                continue
            visible_count += 1
            eval_data = self._get_latest_eval(sub.id)
            if eval_data and eval_data.status == "done":
                completed += 1
            row_widget = self._build_row_widget(sub)
            self.list_layout.addWidget(row_widget)
            self.detail_widgets[str(sub.id)] = row_widget

        total = len(self.subtitle_rows)
        if self.only_translated:
            self.count_label.setText(f"已翻译 {visible_count} 句，已批改 {completed} 句（共 {total} 句）")
        else:
            self.count_label.setText(f"共 {total} 句，已批改 {completed} 句")

    def _get_latest_eval(self, subtitle_id):
        tid = self._get_latest_translation_id(subtitle_id)
        if tid is None:
            return None
        return self._evaluation_service.get_by_translation(tid)

    def _get_latest_translation_id(self, subtitle_id):
        translations = self._translation_service.get_by_subtitle(subtitle_id)
        return translations[-1].id if translations else None

    def _get_latest_user_input(self, subtitle_id):
        """Get the latest user translation text for a subtitle."""
        translations = self._translation_service.get_by_subtitle(subtitle_id)
        return translations[-1].user_input if translations else None

    def _subtitle_by_id(self, sub_id):
        for s in self.subtitle_rows:
            if s.id == sub_id:
                return s
        return None

    def _build_row_widget(self, sub):
        frame = QFrame()
        frame.subtitle_idx = sub.idx
        frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 6px; margin: 4px 0; }")
        main_layout = QVBoxLayout(frame)

        # Summary row
        summary = QHBoxLayout()
        summary.addWidget(QLabel(f"#{sub.idx}"))
        ch_label = QLabel(sub.chinese)
        ch_label.setStyleSheet("font-size: 14px;")
        summary.addWidget(ch_label, 1)

        eval_data = self._get_latest_eval(sub.id)
        self._add_score_summary(summary, eval_data, sub)
        main_layout.addLayout(summary)

        # Detail area
        detail = QWidget()
        self._build_detail_content(detail, sub, eval_data)
        main_layout.addWidget(detail)

        return frame

    def _add_score_summary(self, layout, eval_data, sub):
        # Favorite star button
        fav_btn = QPushButton()
        fav_btn.setFixedSize(28, 28)
        fav_btn.setCursor(Qt.PointingHandCursor)
        subtitle_id = sub.id
        self._set_fav_star(fav_btn, self._favorite_service.is_favorited(subtitle_id))
        fav_btn.clicked.connect(
            lambda checked, sid=subtitle_id, btn=fav_btn: self._on_fav_toggle(sid, btn)
        )
        layout.addWidget(fav_btn)

        if eval_data is None or eval_data.status == "pending":
            lbl = QLabel("⏳ 等待批改")
            lbl.setStyleSheet("color: #888;")
            layout.addWidget(lbl)
        elif eval_data.status == "processing":
            lbl = QLabel("\U0001f504 批改中")
            lbl.setStyleSheet("color: #f39c12;")
            layout.addWidget(lbl)
        elif eval_data.status == "failed":
            lbl = QLabel("❌ 批改失败")
            lbl.setStyleSheet("color: #e74c3c;")
            layout.addWidget(lbl)
            retry_btn = QPushButton("重试")
            retry_btn.setStyleSheet(
                "color: #e74c3c; border: 1px solid #e74c3c; border-radius: 3px; padding: 2px 8px;"
            )
            retry_btn.clicked.connect(lambda checked, s=sub, e=eval_data: self._retry_eval(s, e))
            layout.addWidget(retry_btn)
        elif eval_data.status == "done":
            avg = (
                eval_data.meaning_score + eval_data.grammar_score
                + eval_data.naturalness_score + eval_data.subtitle_style_score
            ) / 4
            color = "#27ae60" if avg >= 80 else "#f39c12" if avg >= 60 else "#e74c3c"
            lbl = QLabel(f"综合 {avg:.0f}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            layout.addWidget(lbl)

    def _set_fav_star(self, btn, is_fav):
        if is_fav:
            btn.setText("★")
            btn.setStyleSheet("color: #f1c40f; border: none; font-size: 16px;")
        else:
            btn.setText("☆")
            btn.setStyleSheet("color: #bbb; border: none; font-size: 16px;")

    def _on_fav_toggle(self, subtitle_id, btn):
        if self._favorite_service.is_favorited(subtitle_id):
            self._favorite_service.remove(subtitle_id)
            self._set_fav_star(btn, False)
        else:
            self._favorite_service.add(subtitle_id)
            self._set_fav_star(btn, True)

    def _font_size(self) -> int:
        return self._config_service.load().font_size

    def _build_detail_content(self, parent, sub, eval_data):
        parent_layout = QVBoxLayout(parent)
        font_size = self._font_size()

        # User's translation
        user_trans = self._get_latest_user_input(sub.id)
        if user_trans:
            user_label = QLabel(f"你的翻译: {user_trans}")
            user_label.setStyleSheet(
                f"font-size: {font_size}px; color: #4a90d9; font-style: italic; "
                "margin-bottom: 12px; padding: 8px; background: #f0f5ff; border-radius: 4px;"
            )
            user_label.setWordWrap(True)
            parent_layout.addWidget(user_label)

        # AI scores
        if eval_data and eval_data.status == "done":
            scores_layout = QHBoxLayout()
            for name, key in [("意思", "meaning_score"), ("语法", "grammar_score"),
                              ("自然度", "naturalness_score"), ("字幕风格", "subtitle_style_score")]:
                score = getattr(eval_data, key)
                color = "#27ae60" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"
                chip = QLabel(f"{name} {score}")
                chip.setStyleSheet(
                    f"font-size: {font_size - 2}px; color: {color}; "
                    f"padding: 4px 10px; border: 1px solid {color}; "
                    "border-radius: 10px;"
                )
                scores_layout.addWidget(chip)
            scores_layout.addStretch()
            parent_layout.addLayout(scores_layout)

            # AI analysis with good formatting
            analysis_browser = QTextBrowser()
            analysis_browser.setOpenExternalLinks(True)
            analysis_browser.setStyleSheet(
                f"font-size: {font_size}px; color: #333; "
                "border: none; background: transparent; "
                "margin-top: 8px; line-height: 1.6;"
            )
            analysis_browser.setMinimumHeight(120)
            # Convert plain text to HTML for line breaks and formatting
            html = eval_data.analysis_text or ""
            html = html.replace("\n", "<br>")
            html = f"<div style='line-height:1.6;'>{html}</div>"
            analysis_browser.setHtml(html)
            parent_layout.addWidget(analysis_browser)

        # Official subtitle (hidden by default)
        official_btn = QPushButton("查看官方字幕 ▸")
        official_btn.setStyleSheet(
            f"color: #4a90d9; border: none; font-size: {font_size - 1}px; "
            "text-align: left; margin-top: 8px;"
        )
        official_label = QLabel(sub.english_official)
        official_label.setStyleSheet(
            f"font-size: {font_size}px; color: #666; "
            "padding: 8px; background: #fafafa; border-radius: 4px;"
        )
        official_label.setWordWrap(True)
        official_label.setVisible(False)
        parent_layout.addWidget(official_btn)
        parent_layout.addWidget(official_label)
        official_btn.clicked.connect(
            lambda: official_label.setVisible(not official_label.isVisible())
        )

        # Redo
        redo_layout = QHBoxLayout()
        redo_input = QLineEdit()
        redo_input.setPlaceholderText("重新翻译...")
        redo_btn = QPushButton("提交")
        redo_btn.clicked.connect(lambda: self._submit_redo(sub, redo_input))
        redo_layout.addWidget(redo_input, 1)
        redo_layout.addWidget(redo_btn)
        parent_layout.addLayout(redo_layout)

        # Version history
        versions = self._translation_service.get_by_subtitle(sub.id)
        if len(versions) > 1:
            ver_label = QLabel(f"共 {len(versions)} 个版本:")
            ver_label.setStyleSheet("color: #666; font-size: 12px;")
            parent_layout.addWidget(ver_label)
            for v in versions:
                parent_layout.addWidget(QLabel(f"  v{v.version}: {v.user_input}"))

        # Collect expression
        if eval_data and eval_data.suggested_expressions:
            suggested = eval_data.suggested_expressions
            if isinstance(suggested, str):
                suggested = json.loads(suggested) if suggested else []
            for expr in suggested:
                collect_btn = QPushButton(f"收藏: {expr}")
                collect_btn.clicked.connect(
                    lambda checked, e=expr, s=sub.id: self._collect(e, s)
                )
                parent_layout.addWidget(collect_btn)

        # Manual collect
        manual_layout = QHBoxLayout()
        manual_input = QLineEdit()
        manual_input.setPlaceholderText("手动添加表达...")
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(lambda: self._collect(manual_input.text(), sub.id))
        manual_layout.addWidget(manual_input, 1)
        manual_layout.addWidget(add_btn)
        parent_layout.addLayout(manual_layout)

    def _retry_eval(self, sub, eval_data):
        translation = self._get_latest_user_input(sub.id)
        if translation:
            self._evaluation_service.update(eval_data.id, "pending")
            self.retry_requested.emit(
                eval_data.id, sub.id, translation, sub.english_official
            )

    def _submit_redo(self, sub, input_widget):
        text = input_widget.text().strip()
        if not text:
            return
        tid = self._get_latest_translation_id(sub.id)
        version = 1
        if tid:
            translations = self._translation_service.get_by_subtitle(sub.id)
            version = max(t.version for t in translations) + 1

        translation = self._translation_service.create(sub.id, text, version)
        eval_id = self._evaluation_service.create(translation.id)
        self.redo_submitted.emit(eval_id, sub.id, text, sub.english_official)
        input_widget.clear()
        QMessageBox.information(self, "已提交", "重新翻译已提交 AI 批改。")

    def _collect(self, phrase, subtitle_id):
        if phrase and phrase.strip():
            self._expression_service.add(phrase.strip(), subtitle_id)
            QMessageBox.information(self, "已收藏", f"已收藏: {phrase}")
