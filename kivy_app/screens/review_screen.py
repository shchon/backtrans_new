"""
Review screen - view AI evaluation results for each translation.
"""
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty

from backtranslate.database.operations import (
    get_subtitles_for_session, get_latest_translation,
    get_evaluation_for_translation, create_translation,
    create_evaluation, add_expression, get_all_translations_for_subtitle,
    is_favorite, add_favorite, remove_favorite,
)
from backtranslate.database.connection import get_connection

Builder.load_string("""
<ReviewScreen>:
    BoxLayout:
        orientation: 'vertical'
        spacing: 0

        # Top bar
        BoxLayout:
            size_hint_y: None
            height: 56
            padding: [8, 0]
            canvas.before:
                Color:
                    rgba: 0.29, 0.56, 0.85, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '‹ 返回'
                size_hint_x: None
                width: 60
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                font_size: '16sp'
                on_press: root.go_home()
            Label:
                text: '复盘'
                font_size: '18sp'
                bold: True
                color: 1, 1, 1, 1
            Widget:
                size_hint_x: None
                width: 60

        # Summary
        Label:
            id: summary_label
            text: '暂无数据'
            font_size: '14sp'
            color: 0.5, 0.5, 0.5, 1
            size_hint_y: None
            height: 36
            padding: [16, 8]

        # Scrollable list of review items
        ScrollView:
            id: scroll_view
            BoxLayout:
                id: list_layout
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [12, 8]
                spacing: 8
""")


class ReviewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_id = None
        self.subtitle_rows = []
        self.detail_widgets = {}

    def on_enter(self):
        """Refresh when screen is shown."""
        if self.session_id:
            # Reload from DB
            self.load_session(self.session_id, self.only_translated)

    def load_session(self, session_id, only_translated=False):
        self.session_id = session_id
        self.only_translated = only_translated
        self.subtitle_rows = get_subtitles_for_session(session_id)
        self._refresh_list()

    def update_evaluation(self, subtitle_id):
        """Called when a new evaluation result arrives."""
        self._refresh_list()

    def _refresh_list(self):
        layout = self.ids.list_layout
        layout.clear_widgets()
        self.detail_widgets.clear()

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from kivy.uix.textinput import TextInput
        from kivy.uix.widget import Widget

        completed = 0
        visible_count = 0

        for sub in self.subtitle_rows:
            if self.only_translated and self._get_latest_translation_id(sub["id"]) is None:
                continue

            visible_count += 1
            eval_data = self._get_latest_eval(sub["id"])
            if eval_data and eval_data["status"] == "done":
                completed += 1

            # Build a card for this subtitle
            card = BoxLayout(
                orientation='vertical',
                size_hint_y=1,
                height=200,
                padding=12,
                spacing=4,
            )
            card.subtitle_idx = sub["idx"]
            card.subtitle_id = sub["id"]

            # Draw card background
            from kivy.graphics import Color, RoundedRectangle, Line
            with card.canvas.before:
                Color(rgba=(0.98, 0.98, 0.98, 1))
                RoundedRectangle(pos=card.pos, size=card.size, radius=[8, 8, 8, 8])
                Color(rgba=(0.9, 0.9, 0.9, 1))
                Line(rounded_rectangle=(card.x, card.y, card.width, card.height, 8))

            # Bind to update background on resize
            def update_bg(instance, value):
                instance.canvas.before.clear()
                with instance.canvas.before:
                    Color(rgba=(0.98, 0.98, 0.98, 1))
                    RoundedRectangle(pos=instance.pos, size=instance.size, radius=[8, 8, 8, 8])
                    Color(rgba=(0.9, 0.9, 0.9, 1))
                    Line(rounded_rectangle=(instance.x, instance.y, instance.width, instance.height, 8))
            card.bind(pos=update_bg, size=update_bg)

            # Header row: idx + chinese + score
            header = BoxLayout(size_hint_y=None, height=30, spacing=8)
            idx_label = Label(
                text=f"#{sub['idx']}",
                font_size='13sp',
                color=(0.4, 0.4, 0.4, 1),
                size_hint_x=None,
                width=36,
            )
            header.add_widget(idx_label)

            ch_label = Label(
                text=sub['chinese'],
                font_size='15sp',
                color=(0.9, 0.9, 0.9, 1),
                halign='left',
                text_size=(self.width - 200, None),
            )
            ch_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (self.width - 200, None)))
            header.add_widget(ch_label)

            # Score or status
            if eval_data is None or eval_data["status"] == "pending":
                status_label = Label(
                    text='⏳ 等待批改',
                    font_size='12sp',
                    color=(0.5, 0.5, 0.5, 1),
                    size_hint_x=None,
                    width=80,
                )
            elif eval_data["status"] == "processing":
                status_label = Label(
                    text='🔄 批改中',
                    font_size='12sp',
                    color=(0.95, 0.61, 0.07, 1),
                    size_hint_x=None,
                    width=80,
                )
            elif eval_data["status"] == "failed":
                status_label = Label(
                    text='❌ 批改失败',
                    font_size='12sp',
                    color=(0.91, 0.3, 0.24, 1),
                    size_hint_x=None,
                    width=80,
                )
            elif eval_data["status"] == "done":
                avg = (
                    eval_data["meaning_score"] + eval_data["grammar_score"]
                    + eval_data["naturalness_score"] + eval_data["subtitle_style_score"]
                ) / 4
                color = (0.15, 0.68, 0.38, 1) if avg >= 80 else (0.95, 0.61, 0.07, 1) if avg >= 60 else (0.91, 0.3, 0.24, 1)
                status_label = Label(
                    text=f'综合 {avg:.0f}',
                    font_size='13sp',
                    bold=True,
                    color=color,
                    size_hint_x=None,
                    width=80,
                )
            else:
                status_label = Label(size_hint_x=None, width=80)

            header.add_widget(status_label)

            # Favorite button - prominent star
            is_fav = is_favorite(sub['id'])
            fav_btn = Button(
                text='★' if is_fav else '☆',
                font_size='26sp',
                size_hint_x=None,
                width=48,
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=(1.0, 0.84, 0.0, 1) if is_fav else (0.6, 0.6, 0.6, 1),
            )
            # Draw a circle background behind the star
            from kivy.graphics import Color, Ellipse
            with fav_btn.canvas.after:
                if is_fav:
                    Color(rgba=(0.15, 0.12, 0.0, 0.6))
                    Ellipse(pos=(fav_btn.x + 2, fav_btn.y + 2),
                            size=(fav_btn.width - 4, fav_btn.height - 4))

            def update_fav_circle(instance, value):
                instance.canvas.after.clear()
                if instance.text == '★':
                    with instance.canvas.after:
                        from kivy.graphics import Color, Ellipse
                        Color(rgba=(0.15, 0.12, 0.0, 0.6))
                        Ellipse(pos=(instance.x + 2, instance.y + 2),
                                size=(instance.width - 4, instance.height - 4))
            fav_btn.bind(pos=update_fav_circle, size=update_fav_circle)

            fav_btn.subtitle_id = sub['id']
            fav_btn.is_fav = is_fav
            fav_btn.bind(on_press=self._on_fav_toggle)
            header.add_widget(fav_btn)

            card.add_widget(header)

            # User's translation (if any)
            user_trans = get_latest_translation(sub["id"])
            if user_trans:
                user_label = Label(
                    text=f'你的翻译: {user_trans}',
                    font_size='13sp',
                    color=(0.29, 0.56, 0.85, 1),
                    italic=True,
                    size_hint_y=None,
                    height=24,
                    text_size=(self.width - 40, None),
                    halign='left',
                )
                card.add_widget(user_label)

            # Scores row (if done)
            if eval_data and eval_data["status"] == "done":
                scores_row = BoxLayout(size_hint_y=None, height=28, spacing=6)
                for name, key in [("意思", "meaning_score"), ("语法", "grammar_score"),
                                  ("自然度", "naturalness_score"), ("字幕风格", "subtitle_style_score")]:
                    score = eval_data[key]
                    color = (0.15, 0.68, 0.38, 1) if score >= 80 else (0.95, 0.61, 0.07, 1) if score >= 60 else (0.91, 0.3, 0.24, 1)
                    chip = Label(
                        text=f'{name} {score}',
                        font_size='11sp',
                        color=color,
                        size_hint_x=None,
                        width=70,
                    )
                    scores_row.add_widget(chip)
                scores_row.add_widget(Widget())
                card.add_widget(scores_row)

            # Expand button
            expand_btn = Button(
                text='查看详情 ▸',
                font_size='12sp',
                color=(0.29, 0.56, 0.85, 1),
                size_hint_y=None,
                height=30,
                background_normal='',
                background_color=(0, 0, 0, 0),
            )
            expand_btn.eval_data = eval_data
            expand_btn.sub = sub
            expand_btn.bind(on_press=self._show_detail_popup)
            card.add_widget(expand_btn)

            layout.add_widget(card)

        # Update summary
        total = len(self.subtitle_rows)
        if self.only_translated:
            self.ids.summary_label.text = f"已翻译 {visible_count} 句，已批改 {completed} 句（共 {total} 句）"
        else:
            self.ids.summary_label.text = f"共 {total} 句，已批改 {completed} 句"

        if layout.children:
            layout.height = len(layout.children) * 220
        else:
            layout.add_widget(Label(
                text='暂无数据',
                font_size='16sp',
                color=(0.5, 0.5, 0.5, 1),
                size_hint_y=None,
                height=200,
            ))
            layout.height = 200

    def _on_fav_toggle(self, btn):
        sid = btn.subtitle_id
        if is_favorite(sid):
            remove_favorite(sid)
            btn.text = '☆'
            btn.color = (0.6, 0.6, 0.6, 1)
            btn.canvas.after.clear()
        else:
            add_favorite(sid)
            btn.text = '★'
            btn.color = (1.0, 0.84, 0.0, 1)
            # Draw circle background
            from kivy.graphics import Color, Ellipse
            btn.canvas.after.clear()
            with btn.canvas.after:
                Color(rgba=(0.15, 0.12, 0.0, 0.6))
                Ellipse(pos=(btn.x + 2, btn.y + 2),
                        size=(btn.width - 4, btn.height - 4))

    def _show_detail_popup(self, btn):
        """Show detail popup with analysis, official subtitle, redo, etc."""
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from kivy.uix.textinput import TextInput
        from kivy.uix.scrollview import ScrollView

        sub = btn.sub
        eval_data = btn.eval_data

        content = BoxLayout(orientation='vertical', spacing=8, padding=12)
        content.bind(minimum_height=content.setter('height'))

        scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True, scroll_type=['content', 'bars'])
        scroll.add_widget(content)

        popup = Popup(
            title=f'#{sub["idx"]} 详情',
            content=scroll,
            size_hint=(0.9, 0.85),
            auto_dismiss=True,
        )

        # Popup background color
        popup.background_color = (0.12, 0.12, 0.15, 1)

        # Chinese sentence
        content.add_widget(Label(
            text=sub['chinese'],
            font_size='18sp',
            bold=True,
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=60,
            text_size=(380, None),
            halign='left',
        ))

        # User translation
        user_trans = get_latest_translation(sub["id"])
        if user_trans:
            content.add_widget(Label(
                text=f'你的翻译: {user_trans}',
                font_size='14sp',
                color=(0.29, 0.56, 0.85, 1),
                italic=True,
                size_hint_y=None,
                height=30,
            ))

        # Analysis
        if eval_data and eval_data["status"] == "done" and eval_data.get("analysis_text"):
            analysis_label = Label(
                text=eval_data["analysis_text"],
                font_name='ChineseFont',
                font_size='14sp',
                color=(0.8, 0.8, 0.8, 1),
                size_hint_y=None,
                height=80,
                text_size=(380, None),
                halign='left',
                valign='top',
            )
            analysis_label.bind(
                texture_size=lambda inst, val: setattr(inst, 'height', max(60, val[1]))
            )
            content.add_widget(analysis_label)

        # Official subtitle
        official_btn = Button(
            text='查看官方字幕 ▸',
            font_size='13sp',
            color=(0.29, 0.56, 0.85, 1),
            size_hint_y=None,
            height=36,
            background_normal='',
            background_color=(0, 0, 0, 0),
        )
        official_label = Label(
            text=sub['english_official'],
            font_name='ChineseFont',
            font_size='14sp',
            color=(0.7, 0.7, 0.7, 1),
            italic=True,
            size_hint_y=None,
            height=30,
            text_size=(380, None),
        )
        official_label.opacity = 0
        official_label.disabled = True

        def toggle_official(btn):
            official_label.opacity = 1 - official_label.opacity
            official_label.disabled = not official_label.disabled
            btn.text = '隐藏官方字幕 ▾' if official_label.opacity else '查看官方字幕 ▸'

        official_btn.bind(on_press=toggle_official)
        content.add_widget(official_btn)
        content.add_widget(official_label)

        # Redo input
        redo_input = TextInput(
            hint_text='重新翻译...',
            font_size='15sp',
            size_hint_y=None,
            height=40,
            multiline=False,
        )
        redo_btn = Button(
            text='提交重新翻译',
            font_size='14sp',
            size_hint_y=None,
            height=40,
            background_normal='',
            background_color=(0.29, 0.56, 0.85, 1),
            color=(1, 1, 1, 1),
        )

        def submit_redo(btn):
            text = redo_input.text.strip()
            if not text:
                return
            tid = self._get_latest_translation_id(sub["id"])
            version = 1
            if tid:
                conn = get_connection()
                row = conn.execute(
                    "SELECT MAX(version) FROM translations WHERE subtitle_id = ?",
                    (sub["id"],),
                ).fetchone()
                conn.close()
                version = (row[0] or 0) + 1

            translate_id = create_translation(sub["id"], text, version)
            eval_id = create_evaluation(translate_id)

            from kivy.app import App
            app = App.get_running_app()
            if app and app.worker:
                context = self._build_context(sub)
                app.worker.add_task(eval_id, 0, text, sub["english_official"], context)

            redo_input.text = ""
            popup.dismiss()

        redo_btn.bind(on_press=submit_redo)
        content.add_widget(redo_input)
        content.add_widget(redo_btn)

        # Close button
        close_btn = Button(
            text='关闭',
            font_name='ChineseFont',
            font_size='15sp',
            size_hint_y=None,
            height=44,
            background_normal='',
            background_color=(0.85, 0.85, 0.85, 1),
            color=(0.7, 0.7, 0.7, 1),
        )
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(close_btn)

        popup.open()

    def _build_context(self, sub):
        from backtranslate.config import load_config
        cfg = load_config()
        n = cfg.get("context_n", 1)
        if n == 0:
            return ""
        parts = []
        for s in self.subtitle_rows:
            idx = s["idx"]
            if idx < sub["idx"] and idx >= sub["idx"] - n:
                parts.append(f"前一句: {s['chinese']}")
            elif idx > sub["idx"] and idx <= sub["idx"] + n:
                parts.append(f"后一句: {s['chinese']}")
        if parts:
            return "上下文（仅供参考，不参与评分）:\n" + "\n".join(parts)
        return ""

    def _get_latest_eval(self, subtitle_id):
        tid = self._get_latest_translation_id(subtitle_id)
        if tid is None:
            return None
        return get_evaluation_for_translation(tid)

    def _get_latest_translation_id(self, subtitle_id):
        conn = get_connection()
        row = conn.execute(
            "SELECT id FROM translations WHERE subtitle_id = ? ORDER BY version DESC LIMIT 1",
            (subtitle_id,),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def go_home(self):
        self.manager.current = "home"