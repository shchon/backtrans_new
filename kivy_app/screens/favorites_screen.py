"""
Favorites screen - manage saved sentences.
"""
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock

from backtranslate.database.operations import (
    get_favorites, remove_favorite, clear_favorites,
    create_session, create_subtitles_batch, get_subtitles_for_session,
)
from backtranslate.database.connection import init_db

Builder.load_string("""
<FavoritesScreen>:
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
                text: '收藏夹'
                font_name: 'ChineseFont'
                font_size: '18sp'
                bold: True
                color: 1, 1, 1, 1
            Button:
                text: '复习'
                size_hint_x: None
                width: 48
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 0.6, 1.0, 0.6, 1
                font_name: 'ChineseFont'
                font_size: '15sp'
                on_press: root.start_review()
            Button:
                text: '清空'
                size_hint_x: None
                width: 48
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 0.6, 0.6, 1
                font_name: 'ChineseFont'
                font_size: '15sp'
                on_press: root.clear_all()

        # Count label
        Label:
            id: count_label
            text: ''
            font_name: 'ChineseFont'
            font_size: '14sp'
            color: 0.7, 0.7, 0.7, 1
            size_hint_y: None
            height: 32
            padding: [16, 6]

        # Scrollable list
        ScrollView:
            BoxLayout:
                id: list_layout
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [12, 8]
                spacing: 8
""")


class FavoritesScreen(Screen):
    def on_enter(self):
        self._refresh()

    def _refresh(self):
        layout = self.ids.list_layout
        layout.clear_widgets()

        favorites = get_favorites()
        self.ids.count_label.text = f"共 {len(favorites)} 句"

        if not favorites:
            layout.add_widget(Label(
                text='暂无收藏句子',
                font_name='ChineseFont',
                font_size='16sp',
                color=(0.6, 0.6, 0.6, 1),
                size_hint_y=None,
                height=200,
            ))
            layout.height = 200
            return

        for i, fav in enumerate(favorites):
            card = self._build_card(i + 1, fav)
            layout.add_widget(card)

        layout.height = len(favorites) * 110

    def _build_card(self, idx, fav):
        """Build a card widget for a favorite item."""
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=100,
            padding=12,
            spacing=4,
        )
        # Card background
        with card.canvas.before:
            from kivy.graphics import Color, RoundedRectangle, Line
            Color(rgba=(0.18, 0.18, 0.22, 1))
            RoundedRectangle(pos=card.pos, size=card.size, radius=[8, 8, 8, 8])
            Color(rgba=(0.3, 0.3, 0.4, 1))
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, 8))

        def update_bg(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                from kivy.graphics import Color, RoundedRectangle, Line
                Color(rgba=(0.18, 0.18, 0.22, 1))
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[8, 8, 8, 8])
                Color(rgba=(0.3, 0.3, 0.4, 1))
                Line(rounded_rectangle=(instance.x, instance.y, instance.width, instance.height, 8))
        card.bind(pos=update_bg, size=update_bg)

        # Row: index + chinese + delete button
        row = BoxLayout(size_hint_y=None, height=36, spacing=8)
        idx_label = Label(
            text=f"#{idx}",
            font_name='ChineseFont',
            font_size='12sp',
            color=(0.6, 0.6, 0.6, 1),
            size_hint_x=None,
            width=32,
        )
        row.add_widget(idx_label)

        ch_label = Label(
            text=fav["chinese"],
            font_name='ChineseFont',
            font_size='15sp',
            color=(0.9, 0.9, 0.9, 1),
            halign='left',
            text_size=(self.width - 120, None),
        )
        ch_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (self.width - 120, None)))
        row.add_widget(ch_label)

        del_btn = Button(
            text='×',
            font_size='20sp',
            color=(0.91, 0.3, 0.24, 1),
            size_hint_x=None,
            width=36,
            background_normal='',
            background_color=(0, 0, 0, 0),
        )
        del_btn.fav_id = fav["id"]
        del_btn.bind(on_press=self._delete_favorite)
        row.add_widget(del_btn)

        card.add_widget(row)

        # English toggle
        en_btn = Button(
            text='查看英文 ▸',
            font_name='ChineseFont',
            font_size='12sp',
            color=(0.29, 0.56, 0.85, 1),
            size_hint_y=None,
            height=26,
            background_normal='',
            background_color=(0, 0, 0, 0),
            halign='left',
        )
        en_label = Label(
            text=fav["english_official"],
            font_name='ChineseFont',
            font_size='13sp',
            color=(0.7, 0.7, 0.7, 1),
            italic=True,
            size_hint_y=None,
            height=26,
            opacity=0,
            disabled=True,
            text_size=(self.width - 40, None),
        )

        def toggle_en(btn, lbl=en_label):
            lbl.opacity = 1 - lbl.opacity
            lbl.disabled = not lbl.disabled
            btn.text = '隐藏英文 ▾' if lbl.opacity else '查看英文 ▸'

        en_btn.bind(on_press=toggle_en)
        card.add_widget(en_btn)
        card.add_widget(en_label)

        return card

    def _delete_favorite(self, btn):
        remove_favorite(btn.fav_id)
        self._refresh()

    def start_review(self):
        """Start reviewing all favorites in the learn screen."""
        favorites = get_favorites()
        if not favorites:
            self._show_toast('收藏夹为空，请先收藏句子')
            return

        init_db()
        from backtranslate.database.operations import clear_session_data
        clear_session_data()

        session_id = create_session("收藏复习", len(favorites))
        subs = []
        for i, fav in enumerate(favorites):
            subs.append({
                "idx": i + 1,
                "chinese": fav["chinese"],
                "english_official": fav["english_official"],
                "prev_chinese": fav.get("prev_chinese", ""),
                "prev_english": fav.get("prev_english", ""),
                "next_chinese": fav.get("next_chinese", ""),
                "next_english": fav.get("next_english", ""),
            })
        create_subtitles_batch(session_id, subs)

        # Load into learn screen
        db_subs = get_subtitles_for_session(session_id)
        learn_screen = self.manager.get_screen("learn")
        learn_screen.load_favorites_review(session_id, db_subs)
        self.manager.current = "learn"

    def _show_toast(self, message):
        popup = Popup(
            title='',
            content=Label(
                text=message,
                font_name='ChineseFont',
                font_size='15sp',
                color=(0.8, 0.8, 0.8, 1),
            ),
            size_hint=(0.7, 0.25),
            auto_dismiss=True,
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

    def clear_all(self):
        content = BoxLayout(orientation='vertical', spacing=12, padding=16)
        content.add_widget(Label(
            text='确定要清空收藏夹中所有句子吗？\n此操作不可撤销。',
            font_name='ChineseFont',
            font_size='15sp',
            color=(0.8, 0.8, 0.8, 1),
            halign='center',
            text_size=(300, None),
        ))
        btn_layout = BoxLayout(size_hint_y=None, height=44, spacing=12)
        cancel_btn = Button(
            text='取消',
            font_name='ChineseFont',
            font_size='15sp',
            background_normal='',
            background_color=(0.85, 0.85, 0.85, 1),
            color=(0.7, 0.7, 0.7, 1),
        )
        confirm_btn = Button(
            text='确定清空',
            font_name='ChineseFont',
            font_size='15sp',
            background_normal='',
            background_color=(0.91, 0.3, 0.24, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)
        content.add_widget(btn_layout)

        popup = Popup(
            title='确认清空',
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False,
        )

        def do_clear(btn):
            clear_favorites()
            popup.dismiss()
            self._refresh()

        confirm_btn.bind(on_press=do_clear)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def go_home(self):
        self.manager.current = "home"