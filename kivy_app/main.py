"""
BackTranslate - 回译训练 (Kivy Android App)
Entry point for the Kivy-based mobile version.
"""
import os
import sys
import json

# Ensure the project root is on sys.path so we can import backtranslate.*
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ---- 字体配置 (必须在 Kivy 初始化之前) ----
_font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
_font_path = os.path.join(_font_dir, 'msyh.ttc')
if not os.path.exists(_font_path):
    _font_path = os.path.join(_font_dir, 'NotoSansSC-Regular.otf')
if not os.path.exists(_font_path):
    _font_path = os.path.join(_font_dir, 'NotoSansSC.otf')
if not os.path.exists(_font_path):
    _font_path = os.path.join(_font_dir, 'wqy-microhei.ttc')
if os.path.exists(_font_path):
    from kivy.config import Config
    Config.set('kivy', 'default_font', [
        'ChineseFont',
        _font_path,
    ])

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import LabelBase

# Register Chinese font - override Roboto (Kivy default) with our font
if os.path.exists(_font_path):
    try:
        # Register as 'Roboto' to override Kivy's default font
        LabelBase.register(name='Roboto', fn_regular=_font_path)
        # Also register as 'ChineseFont' for explicit references
        LabelBase.register(name='ChineseFont', fn_regular=_font_path)
    except Exception as e:
        print(f'Font registration warning: {e}')

from backtranslate.database.connection import init_db
from backtranslate.config import load_config, save_config
from backtranslate.database.operations import (
    update_evaluation_status, get_subtitles_for_session,
    create_session, create_subtitles_batch,
)

from kivy_app.screens.home_screen import HomeScreen
from kivy_app.screens.learn_screen import LearnScreen
from kivy_app.screens.review_screen import ReviewScreen
from kivy_app.screens.favorites_screen import FavoritesScreen
from kivy_app.screens.expressions_screen import ExpressionsScreen
from kivy_app.screens.settings_screen import SettingsScreen
from kivy_app.worker import EvaluationWorker


class BackTranslateApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "BackTranslate"
        self.session_id = None
        self.worker = None

    def build(self):
        # Initialize database
        init_db()

        # Set up screen manager
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(LearnScreen(name="learn"))
        sm.add_widget(ReviewScreen(name="review"))
        sm.add_widget(FavoritesScreen(name="favorites"))
        sm.add_widget(ExpressionsScreen(name="expressions"))
        sm.add_widget(SettingsScreen(name="settings"))

        # Start AI worker
        self._start_worker()

        Window.bind(on_keyboard=self._on_key_back)

        return sm

    def _start_worker(self):
        cfg = load_config()
        self.worker = EvaluationWorker(
            base_url=cfg.get("base_url", ""),
            api_key=cfg.get("api_key", ""),
            model=cfg.get("model", ""),
            prompt_template=cfg.get("prompt_template", ""),
        )
        self.worker.on_done = self._on_eval_done
        self.worker.on_failed = self._on_eval_failed
        self.worker.start()

    def _on_eval_done(self, eval_id, result):
        """Called when AI evaluation completes."""
        try:
            update_evaluation_status(
                eval_id, "done",
                result["meaning_score"],
                result["grammar_score"],
                result["naturalness_score"],
                result["subtitle_style_score"],
                result["analysis"],
                json.dumps(result.get("suggested_expressions", [])),
            )
        except Exception:
            return

        # Refresh review page if it's visible
        review_screen = self.root.get_screen("review")
        if review_screen and review_screen.session_id:
            try:
                from backtranslate.database.connection import get_connection
                conn = get_connection()
                row = conn.execute(
                    "SELECT t.subtitle_id FROM translations t "
                    "JOIN evaluations e ON e.translation_id = t.id "
                    "WHERE e.id = ?", (eval_id,)
                ).fetchone()
                conn.close()
                if row:
                    review_screen.update_evaluation(row[0])
            except Exception:
                pass

    def _on_eval_failed(self, eval_id):
        try:
            update_evaluation_status(eval_id, "failed", error="批改失败")
        except Exception:
            return

        review_screen = self.root.get_screen("review")
        if review_screen and review_screen.session_id:
            try:
                from backtranslate.database.connection import get_connection
                conn = get_connection()
                row = conn.execute(
                    "SELECT t.subtitle_id FROM translations t "
                    "JOIN evaluations e ON e.translation_id = t.id "
                    "WHERE e.id = ?", (eval_id,)
                ).fetchone()
                conn.close()
                if row:
                    review_screen.update_evaluation(row[0])
            except Exception:
                pass

    def _on_key_back(self, window, key, scancode, codepoint, modifier):
        """Handle Android back button."""
        if key == 27:  # ESC / Back
            sm = self.root
            if sm.current != "home":
                sm.current = "home"
                return True  # Consume the event
        return False

    def on_stop(self):
        if self.worker:
            self.worker.stop()


if __name__ == "__main__":
    # Also add font fallback for Android
    if platform == 'android' and os.path.exists(_font_path):
        from kivy.core.text import LabelBase
        try:
            LabelBase.register(name='Roboto', fn_regular=_font_path)
        except Exception:
            pass
    BackTranslateApp().run()