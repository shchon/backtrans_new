"""
Learn screen - the main translation training interface.
"""
import os
import threading

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty, BooleanProperty

from backtranslate.database.connection import init_db
from backtranslate.database.operations import (
    create_session, create_subtitles_batch, create_translation,
    create_evaluation, update_session_completed, clear_session_data,
    get_subtitles_for_session, record_sentence_completed, get_all_stats,
)
from backtranslate.config import load_config, save_config
from backtranslate.srt.parser import parse_srt
from backtranslate.srt.pairing import pair_by_index, pair_by_timecode

Builder.load_string("""
<LearnScreen>:
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
                text: '< 返回'
                size_hint_x: None
                width: 60
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                font_name: 'ChineseFont'
                font_size: '16sp'
                on_press: root.go_home()
            Label:
                text: '回译训练'
                font_name: 'ChineseFont'
                font_size: '18sp'
                bold: True
                color: 1, 1, 1, 1
            Widget:
                size_hint_x: None
                width: 60

        # Content area
        BoxLayout:
            orientation: 'vertical'
            padding: [16, 12]
            spacing: 12

            # Import area (shown when no session)
            BoxLayout:
                id: import_area
                orientation: 'vertical'
                spacing: 16
                size_hint_y: None
                height: 200

                Label:
                    text: '点击下方按钮导入中英字幕文件'
                    font_name: 'ChineseFont'
                    font_size: '16sp'
                    color: 0.7, 0.7, 0.7, 1
                    halign: 'center'

                Button:
                    text: '导入字幕文件'
                    size_hint_y: None
                    height: 52
                    background_normal: ''
                    background_color: 0.29, 0.56, 0.85, 1
                    color: 1, 1, 1, 1
                    font_name: 'ChineseFont'
                    font_size: '16sp'
                    bold: True
                    on_press: root.import_srt()

                # Recent sessions
                Label:
                    id: recent_label
                    text: ''
                    font_name: 'ChineseFont'
                    font_size: '13sp'
                    color: 0.6, 0.6, 0.6, 1
                    halign: 'center'
                    size_hint_y: None
                    height: 20

            # Translation area (shown during session)
            BoxLayout:
                id: translation_area
                orientation: 'vertical'
                spacing: 10

                # Progress info
                BoxLayout:
                    size_hint_y: None
                    height: 24
                    spacing: 8
                    Label:
                        text: '第 ' + str(root.current_idx) + '/' + str(root.total_count) + ' 句'
                        font_name: 'ChineseFont'
                        font_size: '14sp'
                        color: 0.8, 0.8, 0.8, 1
                        size_hint_x: None
                        width: 140
                    ProgressBar:
                        id: progress_bar
                        max: root.total_count
                        value: root.completed_count
                        size_hint_x: 1

                # Chinese sentence
                Label:
                    id: chinese_label
                    text: ''
                    font_name: 'ChineseFont'
                    font_size: '22sp'
                    color: 0.9, 0.9, 0.9, 1
                    size_hint_y: None
                    height: 160
                    text_size: self.width, None
                    halign: 'left'
                    valign: 'top'

                # Input field
                TextInput:
                    id: input_field
                    hint_text: '输入英文翻译...'
                    font_name: 'ChineseFont'
                    font_size: '18sp'
                    size_hint_y: None
                    height: 48
                    multiline: False
                    background_color: 0.2, 0.2, 0.2, 1
                    foreground_color: 0.9, 0.9, 0.9, 1
                    padding: [12, 12]
                    on_text_validate: root.submit_translation()

                # Action buttons
                BoxLayout:
                    size_hint_y: None
                    height: 48
                    spacing: 12
                    Button:
                        text: '跳过'
                        font_name: 'ChineseFont'
                        font_size: '15sp'
                        background_normal: ''
                        background_color: 0.85, 0.85, 0.85, 1
                        color: 0.3, 0.3, 0.3, 1
                        on_press: root.skip_sentence()
                    Button:
                        text: '提交'
                        font_name: 'ChineseFont'
                        font_size: '15sp'
                        bold: True
                        background_normal: ''
                        background_color: 0.29, 0.56, 0.85, 1
                        color: 1, 1, 1, 1
                        on_press: root.submit_translation()

                # Stats bar
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: 80
                    padding: [12, 8]
                    spacing: 6
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.15, 0.2, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [10, 10, 10, 10]
                        Color:
                            rgba: 0.3, 0.3, 0.4, 1
                        Line:
                            rounded_rectangle: self.pos[0], self.pos[1], self.size[0], self.size[1], 10

                    BoxLayout:
                        size_hint_y: None
                        height: 28
                        spacing: 8
                        Label:
                            text: '连续 ' + root.streak + ' 天'
                            font_name: 'ChineseFont'
                            font_size: '15sp'
                            bold: True
                            color: 0.9, 0.5, 0.13, 1
                        Label:
                            text: '今日 ' + root.today + ' 句'
                            font_name: 'ChineseFont'
                            font_size: '15sp'
                            bold: True
                            color: 0.5, 0.8, 1.0, 1
                        Label:
                            text: '总计 ' + root.total + ' 句'
                            font_name: 'ChineseFont'
                            font_size: '15sp'
                            bold: True
                            color: 0.3, 1.0, 0.5, 1

                    Label:
                        id: encourage_label
                        text: ''
                        font_name: 'ChineseFont'
                        font_size: '14sp'
                        color: 0.8, 0.5, 0.9, 1
                        italic: True
                        size_hint_y: None
                        height: 22

                # End session button
                Button:
                    text: '结束学习'
                    size_hint_y: None
                    height: 44
                    background_normal: ''
                    background_color: 0.91, 0.3, 0.24, 1
                    color: 1, 1, 1, 1
                    font_name: 'ChineseFont'
                    font_size: '15sp'
                    on_press: root.end_session()
""")


class LearnScreen(Screen):
    # Properties for data binding
    current_idx = NumericProperty(1)
    total_count = NumericProperty(1)
    completed_count = NumericProperty(0)
    streak = StringProperty("0")
    today = StringProperty("0")
    total = StringProperty("0")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_id = None
        self.subtitles = []
        self._in_session = False

    def on_enter(self):
        """Called when screen becomes visible."""
        self._update_ui_state()
        self._update_stats()

    def _update_ui_state(self):
        """Show/hide import and translation areas."""
        self.ids.import_area.opacity = 0 if self._in_session else 1
        self.ids.import_area.disabled = self._in_session
        self.ids.translation_area.opacity = 1 if self._in_session else 0
        self.ids.translation_area.disabled = not self._in_session

        if not self._in_session:
            # Show recent history
            cfg = load_config()
            recent = cfg.get("recent_pairs", []) or []
            if recent:
                self.ids.recent_label.text = f"最近: {recent[0].get('name', '')}"
            else:
                self.ids.recent_label.text = ""

    def _update_stats(self):
        stats = get_all_stats()
        self.streak = str(stats["streak"])
        self.today = str(stats["today"])
        self.total = str(stats["total"])

    def _show_encouragement(self):
        import random
        messages = [
            "坚持就是胜利！",
            "每一句都在进步！",
            "离目标又近了一步！",
            "今天的努力是明天的底气！",
            "积少成多，你正在变强！",
            "保持这个节奏！",
            "很棒，继续加油！",
            "每一天都在超越昨天的自己！",
            "坚持练习，英语会越来越好！",
            "你在做一件很酷的事！",
            "不积跬步，无以至千里！",
            "又完成一句，离大师更近了！",
            "每一句翻译都是经验的积累！",
            "坚持下去，你就是冠军！",
        ]
        msg = random.choice(messages)
        self.ids.encourage_label.text = msg
        Clock.schedule_once(lambda dt: self._clear_encouragement(msg), 5)

    def _clear_encouragement(self, msg):
        if self.ids.encourage_label.text == msg:
            self.ids.encourage_label.text = ""

    def import_srt(self):
        """Import SRT files using the Kivy FileChooser."""
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        content = BoxLayout(orientation='vertical', spacing=8, padding=16)

        prompt_label = Label(
            text='请选择 SRT 文件所在目录',
            font_name='ChineseFont',
            font_size='15sp',
            size_hint_y=None,
            height=30,
            color=(0.8, 0.8, 0.8, 1),
        )
        content.add_widget(prompt_label)

        filechooser = FileChooserListView(
            filters=['*.srt'],
            path=os.path.expanduser('~'),
        )
        content.add_widget(filechooser)

        btn_layout = BoxLayout(size_hint_y=None, height=44, spacing=12)
        cancel_btn = Button(
            text='取消',
            font_name='ChineseFont',
            background_normal='',
            background_color=(0.85, 0.85, 0.85, 1),
            color=(0.3, 0.3, 0.3, 1),
            font_size='15sp',
        )
        select_btn = Button(
            text='选择中文 SRT',
            font_name='ChineseFont',
            background_normal='',
            background_color=(0.29, 0.56, 0.85, 1),
            color=(1, 1, 1, 1),
            font_size='15sp',
            bold=True,
        )
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(select_btn)
        content.add_widget(btn_layout)

        popup = Popup(
            title='导入字幕',
            content=content,
            size_hint=(0.9, 0.8),
            auto_dismiss=False,
        )

        self._selected_ch_path = None
        self._selected_en_path = None
        self._popup = popup
        self._filechooser = filechooser
        self._select_btn = select_btn
        self._select_step = 1

        def on_select(btn):
            selection = filechooser.selection
            if not selection:
                return
            path = selection[0]
            if not path.endswith('.srt'):
                return

            if self._select_step == 1:
                self._selected_ch_path = path
                self._select_step = 2
                btn.text = '选择英文 SRT'
                prompt_label.text = '请选择对应的英文 SRT 文件'
                filechooser.path = os.path.dirname(path)
                filechooser.selection = []
            else:
                self._selected_en_path = path
                popup.dismiss()
                Clock.schedule_once(lambda dt: self._do_import(), 0.1)

        def on_cancel(btn):
            popup.dismiss()
            self._select_step = 1
            self._selected_ch_path = None
            self._selected_en_path = None

        select_btn.bind(on_press=on_select)
        cancel_btn.bind(on_press=on_cancel)

        popup.open()

    def _do_import(self):
        if not self._selected_ch_path or not self._selected_en_path:
            return

        self._select_step = 1
        ch_path = self._selected_ch_path
        en_path = self._selected_en_path

        try:
            with open(ch_path, "r", encoding="utf-8") as f:
                ch_subs = parse_srt(f.read())
            with open(en_path, "r", encoding="utf-8") as f:
                en_subs = parse_srt(f.read())
        except Exception as e:
            self._show_popup("文件错误", f"无法读取字幕文件:\n{e}")
            return

        pairs = pair_by_timecode(ch_subs, en_subs)
        if not pairs:
            pairs = pair_by_index(ch_subs, en_subs)

        if not pairs:
            self._show_popup("配对失败", "没有找到可配对的中英字幕。")
            return

        cfg = load_config()
        recent = list(cfg.get("recent_pairs", []) or [])
        name = os.path.splitext(os.path.basename(ch_path))[0]
        recent = [p for p in recent if not (
            p.get("ch_path") == ch_path and p.get("en_path") == en_path
        )]
        recent.insert(0, {
            "name": name,
            "ch_path": ch_path,
            "en_path": en_path,
            "use_timecode": False,
        })
        cfg["recent_pairs"] = recent[:8]
        save_config(cfg)

        init_db()
        clear_session_data()

        self.session_id = create_session(name, len(pairs))
        self.total_count = len(pairs)
        self.completed_count = 0
        self.current_idx = 1

        self.subtitles = []
        for i, (ch, en) in enumerate(pairs):
            self.subtitles.append({
                "idx": i + 1,
                "chinese": ch["text"],
                "english_official": en["text"],
                "prev_chinese": pairs[i - 1][0]["text"] if i > 0 else "",
                "prev_english": pairs[i - 1][1]["text"] if i > 0 else "",
                "next_chinese": pairs[i + 1][0]["text"] if i < len(pairs) - 1 else "",
                "next_english": pairs[i + 1][1]["text"] if i < len(pairs) - 1 else "",
            })

        create_subtitles_batch(self.session_id, self.subtitles)

        self._in_session = True
        self._update_ui_state()
        self._show_current_sentence()

    def _show_current_sentence(self):
        if self.current_idx > self.total_count:
            self.end_session()
            return
        sub = self.subtitles[self.current_idx - 1]
        self.ids.chinese_label.text = sub["chinese"]
        self.ids.progress_bar.value = self.completed_count
        self.ids.input_field.text = ""
        self.ids.input_field.focus = True

    def submit_translation(self):
        if not self._in_session:
            return
        text = self.ids.input_field.text.strip()
        if not text:
            return

        sub = self.subtitles[self.current_idx - 1]
        subtitle_id = self._get_subtitle_id(self.current_idx)
        if subtitle_id is None:
            return

        translate_id = create_translation(subtitle_id, text, 1)
        eval_id = create_evaluation(translate_id)

        self.completed_count += 1
        self.current_idx += 1

        record_sentence_completed()
        self._update_stats()
        self._show_encouragement()

        if self.session_id:
            update_session_completed(self.session_id, self.completed_count)

        app = self._get_app()
        if app and app.worker:
            context = self._build_context(sub)
            app.worker.add_task(
                eval_id, 0, text, sub["english_official"], context
            )

        self._show_current_sentence()

    def skip_sentence(self):
        if not self._in_session:
            return
        self.completed_count += 1
        self.current_idx += 1
        record_sentence_completed()
        self._update_stats()
        if self.session_id:
            update_session_completed(self.session_id, self.completed_count)
        self._show_current_sentence()

    def end_session(self):
        if not self._in_session:
            return
        self._in_session = False
        self._update_ui_state()

        stats = get_all_stats()
        msg = (
            f"学习小结\n\n"
            f"本次完成：{self.completed_count} 句\n"
            f"今日累计：{stats['today']} 句\n"
            f"连续打卡：{stats['streak']} 天\n"
            f"历史总计：{stats['total']} 句\n"
        )
        if stats['streak'] >= 3:
            msg += f"\n连续 {stats['streak']} 天打卡，太棒了！"
        elif stats['streak'] >= 1:
            msg += "\n今天也打卡成功，明天继续！"
        else:
            msg += "\n明天继续加油！"

        self._show_popup("学习小结", msg)

        self.manager.get_screen("review").load_session(self.session_id, only_translated=True)
        self.manager.current = "review"

    def _build_context(self, sub):
        cfg = load_config()
        n = cfg.get("context_n", 1)
        if n == 0:
            return ""
        parts = []
        for s in self.subtitles:
            idx = s["idx"]
            if idx < self.current_idx - 1 and idx >= self.current_idx - 1 - n:
                parts.append(f"前一句: {s['chinese']}")
            elif idx > self.current_idx - 1 and idx <= self.current_idx - 1 + n:
                parts.append(f"后一句: {s['chinese']}")
        if parts:
            return "上下文（仅供参考，不参与评分）:\n" + "\n".join(parts)
        return ""

    def _get_subtitle_id(self, idx):
        subs = get_subtitles_for_session(self.session_id)
        for s in subs:
            if s["idx"] == idx:
                return s["id"]
        return None

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()

    def _show_popup(self, title, message):
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from kivy.uix.boxlayout import BoxLayout

        content = BoxLayout(orientation='vertical', spacing=12, padding=16)
        content.add_widget(Label(
            text=message,
            font_name='ChineseFont',
            font_size='15sp',
            color=(0.8, 0.8, 0.8, 1),
            halign='center',
            text_size=(300, None),
        ))
        btn = Button(
            text='确定',
            font_name='ChineseFont',
            size_hint_y=None,
            height=44,
            background_normal='',
            background_color=(0.29, 0.56, 0.85, 1),
            color=(1, 1, 1, 1),
            font_size='15sp',
        )
        content.add_widget(btn)

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.5),
            auto_dismiss=False,
        )
        btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def go_home(self):
        self.manager.current = "home"

    def load_favorites_review(self, session_id, subtitles):
        """Load favorites as a review session."""
        self.session_id = session_id
        self.subtitles = subtitles
        self.total_count = len(subtitles)
        self.completed_count = 0
        self.current_idx = 1
        self._in_session = True
        self._update_ui_state()
        self._update_stats()
        self._show_current_sentence()