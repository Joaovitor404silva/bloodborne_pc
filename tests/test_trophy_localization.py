"""Exercise the achievement page and notification text without opening a Tk window."""
from paths import ROOT
import importlib.util
import sys
import time
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(ROOT / 'launcher'))
spec = importlib.util.spec_from_file_location('trophy_launcher', ROOT / 'launcher/bbport_launcher_win.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class Widget:
    def __init__(self, parent=None, **options):
        self.children = []
        self.options = options
        if parent is not None:
            parent.children.append(self)

    def winfo_children(self):
        return self.children

    def pack(self, **options):
        pass

    def bind(self, *args):
        pass

    def place(self, **options):
        pass

    def lift(self):
        pass

    def create_rectangle(self, *args, **options):
        pass


def labels(widget):
    return ([widget.options['text']] if 'text' in widget.options else []) + [
        text for child in widget.children for text in labels(child)]


class TrophyLocalizationTests(unittest.TestCase):
    def setUp(self):
        previous = launcher.LANG
        self.addCleanup(setattr, launcher, 'LANG', previous)
        launcher.LANG = 'zh'
        self.app = object.__new__(launcher.Launcher)
        self.app.tk = SimpleNamespace(Frame=Widget, Label=Widget, Canvas=Widget)
        self.app.px = lambda value: value
        self.app.trophy_icon = lambda parent, *args: Widget(parent)
        self.app.trophy_body = Widget()
        self.app.trophy_state = None
        self.app.trophy_filter = 'all'
        self.app.tracker = SimpleNamespace(unlocked={14: 0})
        self.app.content = Widget()
        self.app.root = SimpleNamespace(after=lambda *args: None)

    def test_all_base_and_dlc_trophies_are_translated_on_the_page(self):
        self.app.render_trophies()
        text = labels(self.app.trophy_body)
        for _id, name, description, _grade, _group in launcher.trophies.TROPHIES:
            with self.subTest(trophy=_id):
                translated_name = launcher._(name)
                translated_description = launcher._(description)
                self.assertNotEqual(translated_name, name)
                self.assertNotEqual(translated_description, description)
                self.assertIn(translated_name, text)
                self.assertIn(translated_description, text)
        for expected in ('血源诅咒', '老猎人', '已解锁 1 / 40 个奖杯', '全部   40',
                         '已解锁   1', '未解锁   39', '未解锁', '铜奖杯', '白金奖杯'):
            self.assertIn(expected, text)
        self.assertIn(time.strftime('%Y年%m月%d日', time.localtime(0)), text)

    def test_notification_and_unknown_trophy_fallback(self):
        self.app.toasts = [14]
        self.app.show_toast()
        self.assertIn('奖杯已解锁', labels(self.app.content))
        self.assertIn('加斯科因神父', labels(self.app.content))
        self.app.content = Widget()
        self.app.toasts = [999]
        self.app.show_toast()
        self.assertIn('奖杯 999', labels(self.app.content))

    def test_empty_filters_use_chinese_messages(self):
        self.app.tracker.unlocked = {}
        self.app.trophy_filter = 'earned'
        self.app.render_trophies()
        self.assertIn(launcher._('No trophies yet. They appear here as soon as the game unlocks them.'),
                      labels(self.app.trophy_body))
        self.app.trophy_body = Widget()
        self.app.tracker.unlocked = {t[0]: 0 for t in launcher.trophies.TROPHIES}
        self.app.trophy_filter = 'locked'
        self.app.render_trophies()
        self.assertIn('奖杯已全部解锁。向你致敬，善良的猎人。', labels(self.app.trophy_body))

    def test_other_languages_keep_the_english_trophy_fallback(self):
        for language in ('en', 'ru', 'fr'):
            with self.subTest(language=language):
                launcher.LANG = language
                body = Widget()
                self.app.trophy_card(body, launcher.trophies.BY_ID[14], None)
                self.assertIn('Father Gascoigne', labels(body))
                self.assertIn('Defeat the beast that once was Father Gascoigne.', labels(body))


if __name__ == '__main__':
    unittest.main()
