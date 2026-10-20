"""The launcher's search (launcher/bbport_search.py): the players' words find settings, pages
and Help topics."""
from paths import ROOT
import importlib.util
import sys
import unittest

sys.path.insert(0, str(ROOT / 'launcher'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'launcher/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


search = load('bbport_search')
help_ = load('bbport_help')


class Launcher:
    EXPERT_PAGES = {'graphics', 'cheats', 'system', 'advanced', 'log'}

    @staticmethod
    def _(*texts):
        return texts[0]


class Fake(search.SearchMixin):
    def __init__(self, mode='simple'):
        self.app = {'ui_mode': mode}
        entries = [
            {'kind': 'setting', 'page': 'picture', 'title': 'Fullscreen', 'hint': '', 'key': 'fullscreen'},
            {'kind': 'setting', 'page': 'graphics', 'title': 'Frame rate', 'hint': 'Community patches', 'key': 'fps_mode'},
            {'kind': 'setting', 'page': 'game', 'title': 'Text language', 'hint': '', 'key': 'language'},
            {'kind': 'page', 'page': 'controls', 'title': 'Controls', 'hint': '', 'key': 'page:controls'},
            {'kind': 'page', 'page': 'saves', 'title': 'Saves', 'hint': '', 'key': 'page:saves'},
        ]
        for key in help_.TOPIC_ORDER:
            title, why, _steps = help_.TOPICS[key]
            entries.append({'kind': 'topic', 'page': 'help', 'topic': key, 'title': title, 'hint': why,
                            'key': f'topic:{key}'})
        for entry in entries:
            entry['haystack'] = (search.fold(entry['title']), search.fold(entry['hint']),
                                 search.fold(search.WORDS.get(entry['key'], '')))
        self.search_entries = entries


class SearchTests(unittest.TestCase):
    def setUp(self):
        search.bind(Launcher)

    def first(self, query, mode='simple'):
        found = Fake(mode).search(query)
        return (found[0].get('topic') or found[0]['key']) if found else None

    def test_players_words(self):
        self.assertEqual(self.first('vollbild'), 'fullscreen')
        self.assertEqual(self.first('Fullscreen'), 'fullscreen')
        self.assertEqual(self.first('schwarzer bildschirm'), 'black_screen')
        self.assertEqual(self.first('black screen'), 'black_screen')
        self.assertEqual(self.first('controller'), 'page:controls')
        self.assertEqual(self.first('spielstand shadps4'), 'page:saves')
        self.assertEqual(self.first('code 3'), 'page_file')
        self.assertEqual(self.first('eboot lance'), 'eboot_modified')
        self.assertEqual(self.first('deutsch'), 'language')

    def test_accents_and_case_do_not_matter(self):
        self.assertEqual(search.fold('Stürzt AB'), 'sturzt ab')
        self.assertEqual(search.fold('Größe'), 'grosse')
        self.assertEqual(self.first('STÜRZT'), self.first('sturzt'))

    def test_every_word_must_match(self):
        self.assertIsNone(self.first('vollbild xyzzy'))
        self.assertEqual(Fake().search(''), [])

    def test_symptoms_find_the_fix_first(self):
        self.assertIn(self.first('ruckelt'), ('shader_cache', 'vram'))  # Help topics before the settings

    def test_words_point_at_things_that_exist(self):
        topics = set(help_.TOPICS)
        for key in search.WORDS:
            if key.startswith('topic:'):
                self.assertIn(key[6:], topics, key)


if __name__ == '__main__':
    unittest.main()
