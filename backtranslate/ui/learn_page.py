import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QFileDialog, QMessageBox,
    QDialog, QRadioButton, QGroupBox, QMenu, QSpinBox,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from backtranslate.models import AppSettings
from backtranslate.services import (
    ConfigService, SrtService, SessionService,
    SubtitleService, TranslationService, EvaluationService,
    StatsService,
)


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入字幕")
        self.resize(500, 250)
        self.chinese_path = ""
        self.english_path = ""

        layout = QVBoxLayout(self)

        # Chinese SRT
        layout.addWidget(QLabel("中文 SRT 文件:"))
        ch_layout = QHBoxLayout()
        self.ch_path_label = QLabel("未选择")
        self.ch_path_label.setStyleSheet("color: #999;")
        ch_layout.addWidget(self.ch_path_label)
        ch_btn = QPushButton("选择...")
        ch_btn.clicked.connect(self._select_chinese)
        ch_layout.addWidget(ch_btn)
        layout.addLayout(ch_layout)

        # English SRT
        layout.addWidget(QLabel("英文 SRT 文件:"))
        en_layout = QHBoxLayout()
        self.en_path_label = QLabel("未选择")
        self.en_path_label.setStyleSheet("color: #999;")
        en_layout.addWidget(self.en_path_label)
        en_btn = QPushButton("选择...")
        en_btn.clicked.connect(self._select_english)
        en_layout.addWidget(en_btn)
        layout.addLayout(en_layout)

        # Pairing strategy
        pair_group = QGroupBox("配对策略")
        pair_layout = QVBoxLayout(pair_group)
        self.by_timecode_rb = QRadioButton("按时间轴匹配")
        self.by_index_rb = QRadioButton("按序号匹配")
        self.by_index_rb.setChecked(True)
        pair_layout.addWidget(self.by_timecode_rb)
        pair_layout.addWidget(self.by_index_rb)
        layout.addWidget(pair_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        self.ok_btn = QPushButton("开始学习")
        self.ok_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 20px; "
            "border-radius: 4px; }"
        )
        self.ok_btn.clicked.connect(self._validate)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _select_chinese(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择中文 SRT", "", "SRT Files (*.srt)")
        if path:
            self.chinese_path = path
            self.ch_path_label.setText(path)
            self.ch_path_label.setStyleSheet("color: #333;")

    def _select_english(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择英文 SRT", "", "SRT Files (*.srt)")
        if path:
            self.english_path = path
            self.en_path_label.setText(path)
            self.en_path_label.setStyleSheet("color: #333;")

    def _validate(self):
        if not self.chinese_path or not self.english_path:
            QMessageBox.warning(self, "提示", "请选择中文和英文 SRT 文件。")
            return
        self.accept()


class LearnPage(QWidget):
    session_created = Signal(int, int)   # session_id, total count
    translation_submitted = Signal(int, int, str, str)  # eval_id, subtitle_id, user_input, official

    def __init__(self,
                 config_service: ConfigService = None,
                 srt_service: SrtService = None,
                 session_service: SessionService = None,
                 subtitle_service: SubtitleService = None,
                 translation_service: TranslationService = None,
                 evaluation_service: EvaluationService = None,
                 stats_service: StatsService = None):
        super().__init__()
        self._config_service = config_service or ConfigService()
        self._srt_service = srt_service or SrtService()
        self._session_service = session_service or SessionService()
        self._subtitle_service = subtitle_service or SubtitleService()
        self._translation_service = translation_service or TranslationService()
        self._evaluation_service = evaluation_service or EvaluationService()
        self._stats_service = stats_service or StatsService()
        self.session_id = None
        self.subtitles = []
        self.current_idx = 0
        self.total_count = 0
        self.completed_count = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Top bar
        top = QHBoxLayout()
        self.title_label = QLabel("回译训练")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(self.title_label)
        top.addStretch()

        self.import_btn = QPushButton("导入字幕")
        self.import_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #357abd; }"
        )
        self.import_btn.clicked.connect(self._show_import_dialog)
        top.addWidget(self.import_btn)

        # History button
        self.history_btn = QPushButton("历史 ▾")
        self.history_btn.setStyleSheet(
            "QPushButton { color: #666; border: 1px solid #ccc; "
            "padding: 8px 14px; border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #eee; }"
        )
        self.history_btn.clicked.connect(self._show_history_menu)
        top.addWidget(self.history_btn)

        self.end_btn = QPushButton("结束学习")
        self.end_btn.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #c0392b; }"
        )
        self.end_btn.clicked.connect(self._end_session)
        self.end_btn.setVisible(False)
        top.addWidget(self.end_btn)

        layout.addLayout(top)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #666;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Translation area
        self.translation_area = QWidget()
        self.translation_area.setVisible(False)
        ta_layout = QVBoxLayout(self.translation_area)
        ta_layout.setContentsMargins(0, 12, 0, 0)

        # Jump navigation
        jump_row = QHBoxLayout()
        jump_row.addWidget(QLabel("跳转到第"))
        self.jump_spin = QSpinBox()
        self.jump_spin.setMinimum(1)
        self.jump_spin.setMaximum(1)
        self.jump_spin.setFixedWidth(70)
        self.jump_spin.setStyleSheet("font-size: 13px; padding: 4px;")
        jump_row.addWidget(self.jump_spin)
        self.jump_total_label = QLabel("/ 1 句")
        self.jump_total_label.setStyleSheet("color: #666; font-size: 13px;")
        jump_row.addWidget(self.jump_total_label)
        jump_btn = QPushButton("跳转")
        jump_btn.setFixedSize(56, 30)
        jump_btn.setStyleSheet(
            "QPushButton { color: #4a90d9; border: 1px solid #4a90d9; "
            "border-radius: 3px; font-size: 12px; }"
            "QPushButton:hover { background: #e8f0fe; }"
        )
        jump_btn.clicked.connect(self._jump_to_sentence)
        jump_row.addWidget(jump_btn)
        jump_row.addStretch()
        ta_layout.addLayout(jump_row)

        self.chinese_label = QLabel("")
        font = QFont()
        font.setPointSize(18)
        self.chinese_label.setFont(font)
        self.chinese_label.setAlignment(Qt.AlignLeft)
        self.chinese_label.setMinimumHeight(80)
        self.chinese_label.setWordWrap(True)
        ta_layout.addWidget(self.chinese_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入英文翻译，按 Enter 提交...")
        self.input_field.setMinimumHeight(44)
        input_font = QFont()
        input_font.setPointSize(14)
        self.input_field.setFont(input_font)
        self.input_field.returnPressed.connect(self._submit_translation)
        ta_layout.addWidget(self.input_field)

        # Buttons below input
        btn_row = QHBoxLayout()
        skip_btn = QPushButton("跳过")
        skip_btn.setFixedSize(80, 36)
        skip_btn.setStyleSheet(
            "QPushButton { color: #888; border: 1px solid #ccc; "
            "border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #eee; }"
        )
        skip_btn.clicked.connect(self._skip_sentence)
        btn_row.addWidget(skip_btn)
        next_btn = QPushButton("下一句")
        next_btn.setFixedSize(80, 36)
        next_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; "
            "border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #357abd; }"
        )
        next_btn.clicked.connect(self._submit_translation)
        btn_row.addWidget(next_btn)
        btn_row.addStretch()
        ta_layout.addLayout(btn_row)

        # Stats bar (below buttons)
        stats_bar = QHBoxLayout()
        self.stats_widget = QWidget()
        self.stats_widget.setStyleSheet(
            "background: #f0f7ff; border: 1px solid #d0e4f7; border-radius: 8px; padding: 8px;"
        )
        stats_layout = QHBoxLayout(self.stats_widget)
        stats_layout.setContentsMargins(16, 10, 16, 10)
        stats_layout.setSpacing(24)

        self.streak_label = QLabel("🔥 连续 0 天")
        self.streak_label.setStyleSheet("font-size: 16px; color: #e67e22; font-weight: bold;")
        stats_layout.addWidget(self.streak_label)

        self.today_label = QLabel("今日 0 句")
        self.today_label.setStyleSheet("font-size: 16px; color: #4a90d9; font-weight: bold;")
        stats_layout.addWidget(self.today_label)

        self.total_label = QLabel("总计 0 句")
        self.total_label.setStyleSheet("font-size: 16px; color: #27ae60; font-weight: bold;")
        stats_layout.addWidget(self.total_label)

        stats_layout.addStretch()

        self.encourage_label = QLabel("")
        self.encourage_label.setStyleSheet("font-size: 15px; color: #8e44ad; font-style: italic;")
        stats_layout.addWidget(self.encourage_label, 1)

        stats_bar.addWidget(self.stats_widget)
        ta_layout.addLayout(stats_bar)

        layout.addWidget(self.translation_area)

        # Empty state
        self.empty_label = QLabel("点击\"导入字幕\"开始学习")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-size: 16px;")
        layout.addWidget(self.empty_label)

        layout.addStretch()

        # Initialize stats
        self._update_stats()

    def _show_import_dialog(self):
        dlg = ImportDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._import_srt(dlg.chinese_path, dlg.english_path, dlg.by_timecode_rb.isChecked())

    def open_import_at(self, start_path: str) -> None:
        """Open file dialogs starting at the given directory."""
        # Pre-fill paths from the given directory
        ch_path, _ = QFileDialog.getOpenFileName(
            self, "选择中文 SRT", start_path, "SRT Files (*.srt)"
        )
        if not ch_path:
            return
        en_path, _ = QFileDialog.getOpenFileName(
            self, "选择英文 SRT", start_path, "SRT Files (*.srt)"
        )
        if not en_path:
            return

        dlg = ImportDialog(self)
        dlg.chinese_path = ch_path
        dlg.english_path = en_path
        dlg.ch_path_label.setText(ch_path)
        dlg.ch_path_label.setStyleSheet("color: #333;")
        dlg.en_path_label.setText(en_path)
        dlg.en_path_label.setStyleSheet("color: #333;")
        if dlg.exec() == QDialog.Accepted:
            self._import_srt(dlg.chinese_path, dlg.english_path, dlg.by_timecode_rb.isChecked())

    def _show_history_menu(self):
        menu = QMenu(self)
        cfg = self._config_service.load()
        recent = cfg.get("recent_pairs", []) or []

        for pair in recent:
            ch_path = pair.get("ch_path", "")
            en_path = pair.get("en_path", "")
            label = pair.get("name", os.path.basename(ch_path))
            use_timecode = pair.get("use_timecode", False)

            # Only show if both files still exist
            if not os.path.exists(ch_path) or not os.path.exists(en_path):
                continue

            strategy = "时间轴" if use_timecode else "序号"
            action_text = f"{label}  ({strategy})"
            action = menu.addAction(action_text)
            action.triggered.connect(
                lambda checked, cp=ch_path, ep=en_path, ut=use_timecode:
                    self._import_srt(cp, ep, ut)
            )

        if menu.actions():
            menu.addSeparator()

        menu.addAction("清除历史").triggered.connect(self._clear_history)
        menu.exec(self.history_btn.mapToGlobal(self.history_btn.rect().bottomLeft()))

    def _save_recent_pair(self, ch_path, en_path, use_timecode):
        cfg = self._config_service.load()
        recent = list(cfg.get("recent_pairs", []) or [])
        # Remove duplicate
        recent = [p for p in recent if not (p.get("ch_path") == ch_path and p.get("en_path") == en_path)]
        recent.insert(0, {
            "name": os.path.splitext(os.path.basename(ch_path))[0],
            "ch_path": ch_path,
            "en_path": en_path,
            "use_timecode": use_timecode,
        })
        # Keep max 8
        cfg["recent_pairs"] = recent[:8]
        self._config_service.save(AppSettings(**cfg))

    def _clear_history(self):
        cfg = self._config_service.load()
        cfg["recent_pairs"] = []
        self._config_service.save(AppSettings(**cfg))

    def _import_srt(self, ch_path, en_path, use_timecode):
        try:
            with open(ch_path, "r", encoding="utf-8") as f:
                ch_subs = self._srt_service.parse(f.read())
            with open(en_path, "r", encoding="utf-8") as f:
                en_subs = self._srt_service.parse(f.read())
        except (OSError, UnicodeDecodeError) as e:
            QMessageBox.critical(self, "文件错误", f"无法读取字幕文件:\n{e}")
            return

        if use_timecode:
            pairs = self._srt_service.pair_by_timecode(ch_subs, en_subs)
        else:
            pairs = self._srt_service.pair_by_index(ch_subs, en_subs)

        if not pairs:
            QMessageBox.warning(self, "配对失败", "没有找到可配对的中英字幕。")
            return

        if len(ch_subs) != len(en_subs):
            QMessageBox.warning(
                self, "句数不一致",
                f"中文 {len(ch_subs)} 句，英文 {len(en_subs)} 句\n"
                f"已配对 {len(pairs)} 句，建议检查字幕文件或尝试「按时间轴匹配」。"
            )

        # Save to recent history
        self._save_recent_pair(ch_path, en_path, use_timecode)

        name = os.path.splitext(os.path.basename(ch_path))[0]

        self._session_service.clear_all()

        self.session_id = self._session_service.create(name, len(pairs)).id
        self.total_count = len(pairs)
        self.completed_count = 0
        self.current_idx = 0

        self.subtitles = []
        for i, (ch, en) in enumerate(pairs):
            prev_ch = pairs[i - 1][0]["text"] if i > 0 else ""
            prev_en = pairs[i - 1][1]["text"] if i > 0 else ""
            next_ch = pairs[i + 1][0]["text"] if i < len(pairs) - 1 else ""
            next_en = pairs[i + 1][1]["text"] if i < len(pairs) - 1 else ""

            self.subtitles.append({
                "idx": i + 1,
                "chinese": ch["text"],
                "english_official": en["text"],
                "prev_chinese": prev_ch,
                "prev_english": prev_en,
                "next_chinese": next_ch,
                "next_english": next_en,
            })

        self._subtitle_service.save_batch(self.session_id, self.subtitles)
        self.session_created.emit(self.session_id, self.total_count)

        self._start_translation_ui()

    def _start_translation_ui(self):
        self.import_btn.setVisible(False)
        self.empty_label.setVisible(False)
        self.translation_area.setVisible(True)
        self.end_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(self.total_count)
        self.progress_label.setVisible(True)
        self.jump_spin.setMaximum(self.total_count)
        self.jump_spin.setValue(1)
        self.jump_total_label.setText(f"/ {self.total_count} 句")
        self._update_stats()
        self._show_current_sentence()

    def _show_current_sentence(self):
        if self.current_idx >= self.total_count:
            self._end_session()
            return
        sub = self.subtitles[self.current_idx]
        self.chinese_label.setText(sub["chinese"])
        self.progress_bar.setValue(self.completed_count)
        self.progress_label.setText(f"第 {self.current_idx + 1}/{self.total_count} 句")
        self.jump_spin.setValue(self.current_idx + 1)
        self.input_field.clear()
        self.input_field.setFocus()

    def _submit_translation(self):
        text = self.input_field.text().strip()
        if not text:
            return

        # 统一从 DB 读取，确保发给 AI 的官方字幕与复盘页显示一致
        subs_row = self._get_subtitle_row(self.current_idx + 1)
        if subs_row is None:
            return

        translation = self._translation_service.create(subs_row.id, text, 1)
        eval_id = self._evaluation_service.create(translation.id)

        self.completed_count += 1
        self.current_idx += 1

        # Record stats
        self._stats_service.record_sentence_completed()
        self._update_stats()

        # Show encouragement
        self._show_encouragement()

        if self.session_id:
            self._session_service.update_progress(self.session_id, self.completed_count)

        self.translation_submitted.emit(
            eval_id, subs_row.id, text, subs_row.english_official
        )

        self._show_current_sentence()

    def _skip_sentence(self):
        """Skip current sentence without translating."""
        self.completed_count += 1
        self.current_idx += 1
        self._stats_service.record_sentence_completed()
        self._update_stats()
        if self.session_id:
            self._session_service.update_progress(self.session_id, self.completed_count)
        self._show_current_sentence()

    def _jump_to_sentence(self):
        """Jump to the sentence number selected in the spin box."""
        target = self.jump_spin.value() - 1  # convert to 0-based index
        if target < 0 or target >= self.total_count:
            return
        self.current_idx = target
        self._show_current_sentence()

    def _get_subtitle_row(self, idx):
        subs = self._subtitle_service.get_by_session(self.session_id)
        for s in subs:
            if s.idx == idx:
                return s
        return None

    def _update_stats(self):
        stats = self._stats_service.get_all()
        self.streak_label.setText(f"🔥 连续 {stats['streak']} 天")
        self.today_label.setText(f"今日 {stats['today']} 句")
        self.total_label.setText(f"总计 {stats['total']} 句")

    def _show_encouragement(self):
        import random
        from PySide6.QtCore import QTimer
        messages = [
            "💪 坚持就是胜利！",
            "🌟 每一句都在进步！",
            "🎯 离目标又近了一步！",
            "✨ 今天的努力是明天的底气！",
            "📈 积少成多，你正在变强！",
            "🔥 保持这个节奏！",
            "👏 很棒，继续加油！",
            "🚀 每一天都在超越昨天的自己！",
            "💎 坚持练习，英语会越来越好！",
            "🌈 你在做一件很酷的事！",
            "⭐ 不积跬步，无以至千里！",
            "🎉 又完成一句，离大师更近了！",
            "📚 每一句翻译都是经验的积累！",
            "🏆 坚持下去，你就是冠军！",
            "🌱 今天的努力是明天的收获！",
        ]
        msg = random.choice(messages)
        self.encourage_label.setText(msg)
        # Auto-clear after 5 seconds
        QTimer.singleShot(5000, lambda: self.encourage_label.clear()
                          if self.encourage_label.text() == msg else None)

    def _end_session(self):
        self.input_field.setEnabled(False)
        self._on_session_finished()
        self.translation_submitted.emit(-1, -1, "", "")  # sentinel for "session ended"

    def _on_session_finished(self):
        """Show session summary dialog."""
        stats = self._stats_service.get_all()
        msg = (
            f"📊 学习小结\n\n"
            f"本次完成：{self.completed_count} 句\n"
            f"今日累计：{stats['today']} 句\n"
            f"连续打卡：{stats['streak']} 天\n"
            f"历史总计：{stats['total']} 句\n"
        )
        if stats['streak'] >= 3:
            msg += f"\n🔥 连续 {stats['streak']} 天打卡，太棒了！"
        elif stats['streak'] >= 1:
            msg += "\n👏 今天也打卡成功，明天继续！"
        else:
            msg += "\n💪 明天继续加油！"

        QMessageBox.information(self, "学习小结", msg)

    def reset_to_start(self):
        self.session_id = None
        self.subtitles = []
        self.current_idx = 0
        self.total_count = 0
        self.completed_count = 0
        self.import_btn.setVisible(True)
        self.empty_label.setVisible(True)
        self.translation_area.setVisible(False)
        self.end_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.input_field.setEnabled(True)
        self.input_field.clear()
        self.encourage_label.clear()

    def load_favorites_review(self, session_id, subtitles):
        self.session_id = session_id
        self.subtitles = subtitles
        self.total_count = len(subtitles)
        self.completed_count = 0
        self.current_idx = 0
        self._start_translation_ui()
