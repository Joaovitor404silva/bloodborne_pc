"""The players online on The Hunter's Dream (launcher/bbport_launcher_win.py hunters_online): read
from the public statistics its start page shows, nothing when the server does not answer."""
from paths import ROOT
import io
import json
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(ROOT / 'launcher'))
sys.path.insert(0, str(ROOT / 'scripts'))
import bbport_launcher_win as L  # noqa: E402


def answer(data):
    response = io.BytesIO(json.dumps(data).encode())
    response.__enter__ = lambda *a: response
    response.__exit__ = lambda *a: None
    return mock.patch.object(L.bbport_tls, 'urlopen', return_value=response)


class HuntersOnlineTests(unittest.TestCase):
    def test_the_count_and_the_split(self):
        data = {'stats': {}, 'active_sessions': {'count': 798, 'server_online': True,
                                                 'by_client': {'bbhost': 787, 'shadps4': 11}}}
        with answer(data):
            self.assertEqual(L.hunters_online(), (798, 787, 11))

    def test_nothing_when_the_game_server_is_down_or_unreachable(self):
        with answer({'active_sessions': {'count': 0, 'server_online': False}}):
            self.assertIsNone(L.hunters_online())
        with mock.patch.object(L.bbport_tls, 'urlopen', side_effect=OSError('offline')):
            self.assertIsNone(L.hunters_online())
        with answer(['not', 'what', 'it', 'sends']):
            self.assertIsNone(L.hunters_online())

    def test_asked_rarely(self):
        self.assertGreaterEqual(L.HUNTERS_ONLINE_EVERY, 600)  # its answer is about 140 KB


class SignInTests(unittest.TestCase):
    """The Discord sign-in's calls go through the launcher's HTTPS (bbport_tls: expired copies in the
    Windows stores left out, Windows' trust when OpenSSL refuses), like every request of the launcher.
    Nothing is sent: the real device/start would make a sign-in code on the server."""

    def test_the_account_service_is_asked_through_it(self):
        with answer({'ResKind': 0, 'DeviceCode': 'd', 'UserCode': 'U'}) as urlopen:
            reply = L.thd_call(L.COMMUNITY_SERVER + '/auth/device/start', {'DeviceName': 'bbport on PC'})
        self.assertEqual(reply['UserCode'], 'U')
        request = urlopen.call_args.args[0]
        self.assertEqual((request.full_url, request.get_method()),
                         ('https://thehuntersdream.com/auth/device/start', 'POST'))

    def test_a_refused_certificate_says_why(self):
        reason = L.bbport_tls.CertificateRefused('The date or time of this PC looks wrong.', OSError())
        with mock.patch.object(L.bbport_tls, 'urlopen', side_effect=reason):
            with self.assertRaises(OSError) as caught:  # the sign-in shows "Sign-in failed: {}"
                L.thd_sign_in(L.COMMUNITY_SERVER, lambda page, code: None)
        self.assertEqual(str(caught.exception), 'The date or time of this PC looks wrong.')



class PoolTests(unittest.TestCase):
    """The co-op pools: The Hunter's Dream by default, a shadNet server of the player's choice; SuperMedo
    Server is no longer in the launcher."""

    def test_the_hunters_dream_by_default(self):
        self.assertEqual(L.APP_DEFAULTS['online_pool'], 'huntersdream')
        self.assertFalse([key for key in L.APP_DEFAULTS if 'supermedo' in key])

    def test_a_saved_supermedo_pool_plays_on_the_hunters_dream(self):
        settings = {**L.APP_DEFAULTS, 'online': True, 'online_pool': 'supermedo', 'thd_online_id': 'Hunter',
                    'thd_token': 't'}
        with mock.patch.object(L, 'HUNTERS_DREAM_POOL', True):
            env = L.game_environment(settings)
        self.assertEqual(env.get('BB_NET_BACKEND'), 'thd')
        self.assertNotIn('supermedo', env.get('BB_SHADNET_SERVER', '').lower())

    def test_no_supermedo_server_left(self):
        source = (ROOT / 'launcher' / 'bbport_launcher_win.py').read_text(encoding='utf-8').lower()
        self.assertNotIn('supermedo.com', source)
        self.assertNotIn("value='supermedo'", source)


if __name__ == '__main__':
    unittest.main()
