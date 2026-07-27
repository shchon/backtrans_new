"""
Expressions screen - manage collected expressions.
"""
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

from backtranslate.database.operations import get_all_expressions, delete_expression

Builder.load_string("""
<ExpressionsScreen>:
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
                text: '表达库'
                font_size: '18sp'
                bold: True
                color: 1, 1, 1, 1
            Widget:
                size_hint_x: None
                width: 60

        # Search bar
        TextInput:
            id: search_input
            hint_text: '🔍 搜索表达...'
            font_size: '15sp'
            size_hint_y: None
            height: 44
            padding: [12, 10]
            multiline: False
            on_text: root._refresh()

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


class ExpressionsScreen(Screen):
    def on_enter(self):
        self._refresh()

    def _refresh(self):
        layout = self.ids.list_layout
        layout.clear_widgets()

        expressions = get_all_expressions()
        query = self.ids.search_input.text.strip().lower()

        for expr in expressions:
            if query and query not in expr["phrase"].lower():
                continue

            card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=52,
                padding=12,
                spacing=4,
            )
            with card.canvas.before:
                from kivy.graphics import Color, RoundedRectangle, Line
                Color(rgba=(0.98, 0.98, 0.98, 1))
                RoundedRectangle(pos=card.pos, size=card.size, radius=[8, 8, 8, 8])
                Color(rgba=(0.9, 0.9, 0.9, 1))
                Line(rounded_rectangle=(card.x, card.y, card.width, card.height, 8))

            def update_bg(instance, value):
                instance.canvas.before.clear()
                with instance.canvas.before:
                    from kivy.graphics import Color, RoundedRectangle, Line
                    Color(rgba=(0.98, 0.98, 0.98, 1))
                    RoundedRectangle(pos=instance.pos, size=instance.size, radius=[8, 8, 8, 8])
                    Color(rgba=(0.9, 0.9, 0.9, 1))
                    Line(rounded_rectangle=(instance.x, instance.y, instance.width, instance.height, 8))
            card.bind(pos=update_bg, size=update_bg)

            row = BoxLayout(size_hint_y=None, height=32, spacing=8)

            phrase_label = Label(
                text=expr["phrase"],
                font_size='15sp',
                bold=True,
                color=(0.1, 0.1, 0.1, 1),
                halign='left',
                text_size=(self.width - 120, None),
            )
            phrase_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (self.width - 120, None)))
            row.add_widget(phrase_label)

            del_btn = Button(
                text='删除',
                font_size='13sp',
                color=(0.91, 0.3, 0.24, 1),
                size_hint_x=None,
                width=52,
                background_normal='',
                background_color=(0, 0, 0, 0),
            )
            del_btn.expr_id = expr["id"]
            del_btn.bind(on_press=self._delete_expression)
            row.add_widget(del_btn)

            card.add_widget(row)
            layout.add_widget(card)

        if not layout.children:
            layout.add_widget(Label(
                text='还没有收藏的表达',
                font_size='16sp',
                color=(0.6, 0.6, 0.6, 1),
                size_hint_y=None,
                height=200,
            ))
            layout.height = 200
        else:
            layout.height = len(layout.children) * 60

    def _delete_expression(self, btn):
        delete_expression(btn.expr_id)
        self._refresh()

    def go_home(self):
        self.manager.current = "home"