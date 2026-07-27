"""
Home screen - main navigation hub with stats overview.
"""
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.button import Button

from backtranslate.database.operations import get_all_stats


class NavButton(Button):
    """Navigation button with two-line text using markup."""
    secondary_text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True
        self.font_name = 'ChineseFont'
        self.halign = 'center'
        self.valign = 'middle'
        self.text_size = (self.width - 20, None)
        self.bind(size=self._update_text_size)
        self._nav_updating = False

    def _update_text_size(self, *args):
        self.text_size = (self.width - 20, None)

    def on_secondary_text(self, *args):
        if not self._nav_updating and self.text and self.secondary_text:
            self._nav_updating = True
            self.text = f'[b]{self.text}[/b]\n{self.secondary_text}'
            self._nav_updating = False

    def on_text(self, *args):
        if not self._nav_updating and self.text and self.secondary_text:
            self._nav_updating = True
            self.text = f'[b]{self.text}[/b]\n{self.secondary_text}'
            self._nav_updating = False


Builder.load_string("""
<HomeScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 0
        spacing: 0

        # Top bar
        BoxLayout:
            size_hint_y: None
            height: 56
            padding: [16, 0]
            canvas.before:
                Color:
                    rgba: 0.29, 0.56, 0.85, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: 'BackTranslate'
                font_name: 'ChineseFont'
                font_size: '20sp'
                bold: True
                color: 1, 1, 1, 1

        # Scrollable content
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [16, 16]
                spacing: 16

                # Stats card
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: 100
                    padding: [16, 12]
                    spacing: 8
                    canvas.before:
                        Color:
                            rgba: 0.94, 0.97, 1.0, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [12, 12, 12, 12]
                        Color:
                            rgba: 0.82, 0.89, 0.97, 1
                        Line:
                            rounded_rectangle: self.pos[0], self.pos[1], self.size[0], self.size[1], 12

                    Label:
                        text: '🔥 连续 ' + root.streak + ' 天'
                        font_name: 'ChineseFont'
                        font_size: '22sp'
                        bold: True
                        color: 0.9, 0.5, 0.13, 1
                        size_hint_y: None
                        height: 30
                    BoxLayout:
                        size_hint_y: None
                        height: 30
                        Label:
                            text: '今日 ' + root.today + ' 句'
                            font_name: 'ChineseFont'
                            font_size: '16sp'
                            color: 0.29, 0.56, 0.85, 1
                        Label:
                            text: '总计 ' + root.total + ' 句'
                            font_name: 'ChineseFont'
                            font_size: '16sp'
                            color: 0.15, 0.68, 0.38, 1

                # Navigation buttons
                NavButton:
                    text: '📖  开始学习'
                    secondary_text: '导入字幕，进行回译训练'
                    on_press: root.go_learn()
                NavButton:
                    text: '📊  复盘'
                    secondary_text: '查看翻译批改结果'
                    on_press: root.go_review()
                NavButton:
                    text: '⭐  收藏夹'
                    secondary_text: '管理收藏的句子'
                    on_press: root.go_favorites()
                NavButton:
                    text: '📝  表达库'
                    secondary_text: '积累的地道表达'
                    on_press: root.go_expressions()
                NavButton:
                    text: '⚙️  设置'
                    secondary_text: 'API 配置、提示词模板'
                    on_press: root.go_settings()

                # Bottom spacing
                Widget:
                    size_hint_y: None
                    height: 20


<NavButton>:
    size_hint_y: None
    height: 72
    background_normal: ''
    background_color: 0.98, 0.98, 0.98, 1
    font_name: 'ChineseFont'
    font_size: '17sp'
    color: 0.2, 0.2, 0.2, 1
    halign: 'center'
    valign: 'middle'
    markup: True
    canvas.before:
        Color:
            rgba: 0.98, 0.98, 0.98, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10, 10, 10, 10]
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Line:
            rounded_rectangle: self.pos[0], self.pos[1], self.size[0], self.size[1], 10
""")


class HomeScreen(Screen):
    streak = StringProperty("0")
    today = StringProperty("0")
    total = StringProperty("0")

    def on_enter(self):
        """Refresh stats when screen is shown."""
        self._update_stats()

    def _update_stats(self):
        stats = get_all_stats()
        self.streak = str(stats["streak"])
        self.today = str(stats["today"])
        self.total = str(stats["total"])

    def go_learn(self):
        self.manager.current = "learn"

    def go_review(self):
        self.manager.current = "review"

    def go_favorites(self):
        self.manager.current = "favorites"

    def go_expressions(self):
        self.manager.current = "expressions"

    def go_settings(self):
        self.manager.current = "settings"