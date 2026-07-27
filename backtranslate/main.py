"""BackTranslate 应用入口 — 服务编排"""

import sys
import json
from PySide6.QtWidgets import QApplication

from backtranslate.database.connection import init_db, get_connection
from backtranslate.ui.main_window import MainWindow
from backtranslate.ui.learn_page import LearnPage
from backtranslate.ui.review_page import ReviewPage
from backtranslate.ui.favorites_page import FavoritesPage
from backtranslate.ui.expressions_page import ExpressionsPage
from backtranslate.ui.settings_page import SettingsPage
from backtranslate.ai.worker import EvaluationWorker, EvaluationThread
from backtranslate.services import (
    ConfigService, SessionService, SubtitleService,
    TranslationService, EvaluationService, ExpressionService,
    FavoriteService, StatsService, SrtService, AiService,
)


class App:
    def __init__(self):
        # Services
        self._config_service = ConfigService()
        self._session_service = SessionService()
        self._subtitle_service = SubtitleService()
        self._translation_service = TranslationService()
        self._evaluation_service = EvaluationService()
        self._expression_service = ExpressionService()
        self._favorite_service = FavoriteService()
        self._stats_service = StatsService()
        self._srt_service = SrtService()
        self._ai_service = AiService()

        # Worker (config-free, all params passed per-task)
        self._worker = EvaluationWorker()
        self._worker_thread = EvaluationThread(self._worker)
        self._worker.evaluation_done.connect(self._on_eval_done)
        self._worker.evaluation_failed.connect(self._on_eval_failed)

        # Main window with service injection
        self._window = MainWindow(self._config_service)

        # Pages with service injection
        self._learn_page = LearnPage(
            config_service=self._config_service,
            srt_service=self._srt_service,
            session_service=self._session_service,
            subtitle_service=self._subtitle_service,
            translation_service=self._translation_service,
            evaluation_service=self._evaluation_service,
            stats_service=self._stats_service,
        )
        self._review_page = ReviewPage(
            subtitle_service=self._subtitle_service,
            translation_service=self._translation_service,
            evaluation_service=self._evaluation_service,
            expression_service=self._expression_service,
            favorite_service=self._favorite_service,
            config_service=self._config_service,
        )
        self._favorites_page = FavoritesPage(
            favorite_service=self._favorite_service,
        )
        self._expressions_page = ExpressionsPage(
            expression_service=self._expression_service,
        )
        self._settings_page = SettingsPage(
            config_service=self._config_service,
        )

        # Register pages with window
        self._window.set_learn_page(self._learn_page)
        self._window.set_review_page(self._review_page)
        self._window.set_favorites_page(self._favorites_page)
        self._window.set_expressions_page(self._expressions_page)
        self._window.set_settings_page(self._settings_page)

        # Connect signals
        self._connect_signals()

        # Start worker thread
        self._worker_thread.start()

    def _connect_signals(self):
        self._learn_page.translation_submitted.connect(
            self._on_translation_submitted)
        self._review_page.redo_submitted.connect(
            self._on_redo_submitted)
        self._review_page.retry_requested.connect(
            self._on_retry_requested)
        self._favorites_page.start_favorites_review.connect(
            self._on_start_favorites_review)
        self._window.import_at_path.connect(
            self._learn_page.open_import_at)

    def _find_subtitle_id_for_eval(self, eval_id):
        """Find subtitle_id for a given evaluation id."""
        conn = get_connection()
        row = conn.execute(
            "SELECT t.subtitle_id FROM translations t "
            "JOIN evaluations e ON e.translation_id = t.id "
            "WHERE e.id = ?", (eval_id,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _on_translation_submitted(self, eval_id, subtitle_id,
                                   user_input, official):
        if eval_id == -1:  # session ended
            session_id = self._learn_page.session_id
            if session_id:
                self._review_page.load_session(session_id, only_translated=True)
            self._learn_page.reset_to_start()
            self._window.navigate_to_review()
            return

        settings = self._config_service.load()
        subtitles = self._subtitle_service.get_by_session(
            self._learn_page.session_id)
        subtitle = next((s for s in subtitles if s.id == subtitle_id), None)
        context = ""
        if subtitle:
            context = self._ai_service.build_context(
                subtitles, subtitle.idx, settings.context_n)

        self._worker.add_task(
            eval_id, settings.prompt_template, context,
            user_input, official,
            settings.api_key, settings.base_url, settings.model,
        )

    def _on_redo_submitted(self, eval_id, subtitle_id, user_input, official):
        self._on_translation_submitted(eval_id, subtitle_id, user_input, official)

    def _on_retry_requested(self, eval_id, subtitle_id, user_input, official):
        self._on_translation_submitted(eval_id, subtitle_id, user_input, official)

    def _on_eval_done(self, eval_id, result):
        try:
            self._evaluation_service.update(
                eval_id, "done",
                meaning_score=result.get("meaning_score"),
                grammar_score=result.get("grammar_score"),
                naturalness_score=result.get("naturalness_score"),
                subtitle_style_score=result.get("subtitle_style_score"),
                analysis=result.get("analysis"),
                suggested=json.dumps(result.get("suggested_expressions", [])),
            )
        except Exception:
            return

        subtitle_id = self._find_subtitle_id_for_eval(eval_id)
        if subtitle_id and self._review_page.session_id:
            try:
                self._review_page.update_evaluation(subtitle_id)
            except Exception:
                pass

    def _on_eval_failed(self, eval_id, error_msg):
        try:
            self._evaluation_service.update(
                eval_id, "failed", error=error_msg or "批改失败")
        except Exception:
            return

        subtitle_id = self._find_subtitle_id_for_eval(eval_id)
        if subtitle_id and self._review_page.session_id:
            try:
                self._review_page.update_evaluation(subtitle_id)
            except Exception:
                pass

    def _on_start_favorites_review(self, subtitles):
        if not subtitles:
            return
        session = self._session_service.create("收藏复习", len(subtitles))
        new_subs = []
        for i, sub in enumerate(subtitles):
            new_subs.append({
                "idx": i + 1,
                "chinese": sub["chinese"],
                "english_official": sub["english_official"],
                "prev_chinese": sub.get("prev_chinese", ""),
                "prev_english": sub.get("prev_english", ""),
                "next_chinese": sub.get("next_chinese", ""),
                "next_english": sub.get("next_english", ""),
            })
        self._subtitle_service.save_batch(session.id, new_subs)
        db_subs = self._subtitle_service.get_by_session(session.id)
        dict_subs = [
            {"id": s.id, "idx": s.idx, "chinese": s.chinese,
             "english_official": s.english_official,
             "prev_chinese": s.prev_chinese, "prev_english": s.prev_english,
             "next_chinese": s.next_chinese, "next_english": s.next_english}
            for s in db_subs
        ]
        self._learn_page.load_favorites_review(session.id, dict_subs)
        self._window.navigate_to_learn()

    def show(self):
        self._window.show()


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    application = App()
    application.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
