"""The path tracing fork's launcher: path tracing on by default (Extra variables still override it), updates from
the fork's repository only for a newer fork release, strength presets (auto by default)."""
from paths import ROOT
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402


def release(tag):
    return {'tag_name': tag, 'html_url': 'https://example.invalid/' + tag,
            'assets': [{'name': 'Bloodborne-Windows.zip', 'browser_download_url': 'https://example.invalid/zip'}]}


class RtForkLauncher(unittest.TestCase):
    def test_path_tracing_is_on_by_default(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            env = L.game_environment(dict(L.APP_DEFAULTS), L.INI_DEFAULTS)
        for key, value in L.RT_ENV.items():
            self.assertEqual(env[key], value, key)

    def test_extra_variables_override_the_defaults(self):
        settings = {**L.APP_DEFAULTS, 'extra_env': 'BB_RT=0 BB_RT_GI_STRENGTH=1.3'}
        with mock.patch.dict('os.environ', {}, clear=True):
            env = L.game_environment(settings, L.INI_DEFAULTS)
        self.assertEqual((env['BB_RT'], env['BB_RT_GI_STRENGTH']), ('0', '1.3'))

    def test_presets(self):
        def strengths(**modes):
            settings = {**L.APP_DEFAULTS, 'rt_gi': '1.9', **{f'{k}_mode': v for k, v in modes.items()}}
            with mock.patch.dict('os.environ', {}, clear=True):
                env = L.game_environment(settings, L.INI_DEFAULTS)
            return env['BB_RT_GI_STRENGTH'], env['BB_RT_REFLECT_STRENGTH'], env['BB_RT_SHADOW_STRENGTH']
        self.assertEqual(strengths(), ('1.00', '1.00', '0.75'))  # auto by default; the slider is ignored
        self.assertEqual(strengths(rt_gi='low', rt_reflect='high', rt_shadow='medium'), ('0.60', '1.50', '0.75'))
        self.assertEqual(strengths(rt_gi='custom', rt_shadow='nonsense'), ('1.90', '1.00', '0.75'))

    def test_path_tracing_section_settings(self):
        settings = {**L.APP_DEFAULTS, 'rt_gi': '1.5', 'rt_reflect': '0.4', 'rt_shadow': '9',
                    'rt_gi_mode': 'custom', 'rt_reflect_mode': 'custom', 'rt_shadow_mode': 'custom'}
        with mock.patch.dict('os.environ', {}, clear=True):
            env = L.game_environment(settings, L.INI_DEFAULTS)
        self.assertEqual((env['BB_RT'], env['BB_RT_GI_STRENGTH'], env['BB_RT_REFLECT_STRENGTH'],
                          env['BB_RT_SHADOW_STRENGTH']), ('1', '1.50', '0.40', '1.50'))  # 9 kept to the range
        with mock.patch.dict('os.environ', {}, clear=True):
            env = L.game_environment({**L.APP_DEFAULTS, 'rt_on': False}, L.INI_DEFAULTS)
        self.assertEqual(env['BB_RT'], '0')
        self.assertNotIn('BB_RT_GI', env)

    def test_updates_come_from_the_fork(self):
        for url in (L.RELEASES_API, L.RELEASES_PAGE, L.RELEASES_LIST_API):
            self.assertIn(L.RT_REPO, url)

    def offer(self, releases):
        with mock.patch.object(L.bbport_tls, 'urlopen') as urlopen, \
                mock.patch.object(L.json, 'load', return_value=releases):
            urlopen.return_value.__enter__.return_value = None
            return L.update_to_offer()

    def test_only_a_newer_fork_release_is_offered(self):
        own = f'windows-v{L.VERSION}-{L.RT_VERSION}'
        for tag, offered in ((own, False), (f'windows-v{L.VERSION}-pt9.0', True), ('windows-v9.0.0.0-pt2.0', True)):
            self.assertEqual(self.offer([release(tag)]) is not None, offered, tag)

    def test_mod_only_releases_are_never_offered(self):
        # 2026-11-14: the repository's latest release "pt2.3" (the 4-file mod zip) read as version 2.3, was
        # offered as an update, and its download had no Bloodborne.exe.
        mod = {'tag_name': 'pt2.3', 'html_url': 'x', 'assets': [
            {'name': 'Bloodborne-PC-Path-Tracing-pt2.3.zip', 'browser_download_url': 'https://example.invalid/mod'}]}
        self.assertIsNone(self.offer([mod]))
        newer = release(f'windows-v{L.VERSION}-pt9.0')
        self.assertEqual(self.offer([mod, newer])[1], 'https://example.invalid/zip')



if __name__ == '__main__':
    unittest.main()
