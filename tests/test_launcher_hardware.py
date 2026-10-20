"""The launcher's hardware check and the settings it recommends (launcher/bbport_hardware.py)."""
from paths import ROOT
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location('bbport_hardware', ROOT / 'launcher/bbport_hardware.py')
hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hardware)


def rate(card, cpu, ram):
    return hardware.assess(hardware.GPU_BY_ID[card], hardware.cpu_from_name(cpu), ram)


def profile(rating, display=(2560, 1440), current=None, goal='smooth'):
    available = hardware.outputs(*display)
    res = hardware.recommended_class(rating, available)
    return {key: value for _store, key, value, _why in hardware.profile(rating, res, available[res], current, goal)}


class TableTests(unittest.TestCase):
    """The tables of the hardware check on bbport.de/install."""

    def test_cards_and_scores(self):
        self.assertEqual(len(hardware.GPU_LIST), 161)
        self.assertEqual(hardware.GPU_BY_ID['amd-rx-9070-xt'].score, 275)
        self.assertEqual(hardware.GPU_BY_ID['nvidia-rtx-4060'].vram, 8)
        self.assertTrue(hardware.GPU_BY_ID['nvidia-rtx-4060'].dlss)
        self.assertTrue(hardware.GPU_BY_ID['amd-rx-7800-xt'].fsr4)
        self.assertFalse(hardware.GPU_BY_ID['amd-rx-6800-xt'].fsr4)

    def test_vulkan_names_match_the_table(self):
        for name, vram, expected in (('NVIDIA GeForce RTX 4070 Laptop GPU', 8, 'nvidia-rtx-4070-laptop'),
                                     ('AMD Radeon RX 9070 XT', 16, 'amd-rx-9070-xt'),
                                     ('AMD Radeon RX 580 Series', 8, 'amd-rx-580-8-gb'),
                                     ('Intel(R) Arc(TM) A770 Graphics', 16, 'intel-arc-a770-16-gb'),
                                     ('AMD Radeon(TM) 890M Graphics', 0, 'amd-radeon-890m-ryzen-ai-300')):
            self.assertEqual(hardware.match_gpu(name, vram).id, expected, name)
        self.assertIsNone(hardware.match_gpu('AMD Radeon(TM) Graphics', 0))

    def test_processors(self):
        for name, score, support in (('12th Gen Intel(R) Core(TM) i7-12700K', 195, 'ok'),
                                     ('Intel(R) Core(TM) i5-3570K CPU @ 3.40GHz', 60, 'compat'),
                                     ('Intel(R) Core(TM) i7 CPU 920 @ 2.67GHz', 0, 'none'),
                                     ('AMD Ryzen 7 5800X 8-Core Processor', 180, 'ok'),
                                     ('AMD FX(tm)-8350 Eight-Core Processor', 0, 'none'),
                                     ('Intel(R) Celeron(R) N4020 CPU @ 1.10GHz', 0, 'none')):
            cpu = hardware.cpu_from_name(name)
            self.assertEqual((cpu.score, cpu.support), (score, support), name)

    def test_the_laptops_dedicated_card_wins(self):
        lines = ['AMD Radeon(TM) Graphics, integrated, 512 MiB', 'NVIDIA GeForce RTX 4060 Laptop GPU, discrete, 8188 MiB']
        self.assertEqual(hardware.best_gpu_line(lines), lines[1])

    def test_vendor(self):
        self.assertEqual(hardware.vendor_of('AMD Radeon RX 9070 XT'), 'amd')
        self.assertEqual(hardware.vendor_of('NVIDIA GeForce RTX 3060'), 'nvidia')
        self.assertEqual(hardware.vendor_of('Intel(R) Arc(TM) A770 Graphics'), 'intel')


class RatingTests(unittest.TestCase):
    def test_tiers(self):
        top = rate('amd-rx-9070-xt', 'AMD Ryzen 7 5800X 8-Core Processor', 32)
        self.assertEqual((top.tier_label, top.levels), ('4K-ready', {'1080p': 5, '1440p': 5, '4K': 4}))
        low = rate('nvidia-gtx-1650', 'Intel(R) Core(TM) i5-9400F CPU @ 2.90GHz', 16)
        self.assertEqual((low.tier_label, low.limit), ('Minimum', 'gpu'))
        self.assertEqual(rate('amd-rx-9070-xt', 'AMD FX(tm)-8350 Eight-Core Processor', 32).tier, 0)
        self.assertEqual(rate('amd-rx-9070-xt', 'AMD Ryzen 7 5800X 8-Core Processor', 8).limit, 'ram')


class ProfileTests(unittest.TestCase):
    def test_a_strong_radeon_at_1440p(self):
        settings = profile(rate('amd-rx-9070-xt', 'AMD Ryzen 7 5800X 8-Core Processor', 32))
        self.assertEqual(settings['output_res'], '2560x1440')
        self.assertEqual((settings['upscaler'], settings['preset'], settings['fps_mode']), ('fsr4', '1', 'uncap'))
        self.assertEqual(settings['model_lod'], '-2')
        self.assertTrue(settings['object_motion'] and settings['effect_ssao'])
        self.assertFalse(settings['effect_game_aa'])

    def test_four_gigabyte_cards_follow_the_website(self):
        settings = profile(rate('nvidia-gtx-1650', 'Intel(R) Core(TM) i5-9400F CPU @ 2.90GHz', 16), (1920, 1080))
        self.assertEqual((settings['upscaler'], settings['preset'], settings['fps_mode']), ('fsr3', '3', '60'))
        self.assertEqual(settings['model_lod'], '0')
        self.assertFalse(settings['object_motion'])

    def test_intel_graphics_without_an_upscaler(self):
        settings = profile(rate('intel-arc-a770-16-gb', 'Intel(R) Core(TM) i5-13400F', 16))
        self.assertEqual(settings['upscaler'], 'off')
        self.assertNotIn('preset', settings)
        self.assertTrue(settings['effect_game_aa'])

    def test_dlss_only_on_a_geforce(self):
        for card in hardware.GPU_LIST:
            if not card.vulkan13:
                continue
            r = hardware.assess(card, hardware.cpu_from_name('AMD Ryzen 7 5800X'), 32)
            if r.tier == 0:
                continue
            upscaler = profile(r, (3840, 2160))['upscaler']
            self.assertTrue(upscaler != 'dlss' or card.vendor == 'nvidia', card.label)
            self.assertTrue(upscaler != 'fsr4' or card.fsr4, card.label)

    def test_taste_is_left_alone(self):
        settings = profile(rate('amd-rx-9070-xt', 'AMD Ryzen 7 5800X 8-Core Processor', 32))
        for key in ('effect_chromatic_aberration', 'effect_dof', 'effect_motion_blur', 'sharpen', 'sharpness'):
            self.assertNotIn(key, settings)
        self.assertNotIn('effect_ssr', settings)  # off only where the card has no room for it
        weaker = rate('nvidia-rtx-4060', 'AMD Ryzen 5 5600X', 16)
        self.assertFalse(profile(weaker, current={'effect_ssr': True})['effect_ssr'])

    def test_frame_generation_off_only_where_it_cannot_work(self):
        weak = rate('nvidia-gtx-1650', 'Intel(R) Core(TM) i5-9400F CPU @ 2.90GHz', 16)
        self.assertEqual(profile(weak, (1920, 1080), {'frame_gen': 'fsr3'})['frame_gen'], 'off')
        strong = rate('nvidia-rtx-4070', 'AMD Ryzen 7 5800X', 32)
        self.assertNotIn('frame_gen', profile(strong, current={'frame_gen': 'dlss'}))

    def test_ultrawide_outputs(self):
        self.assertEqual(hardware.outputs(3440, 1440), {'1080p': '2560x1080', '1440p': '3440x1440'})
        self.assertEqual(hardware.outputs(1920, 1080), {'1080p': '1920x1080'})


class GoalTests(unittest.TestCase):
    """The player's goal (Play page): smooth, balanced (60 FPS, best picture), quiet (60 FPS, less work)."""

    def test_a_strong_pc(self):
        r = rate('amd-rx-9070-xt', 'AMD Ryzen 7 5800X 8-Core Processor', 32)
        smooth, balanced, quiet = (profile(r, goal=g) for g in hardware.GOALS)
        self.assertEqual((smooth['preset'], smooth['fps_mode'], smooth['model_lod']), ('1', 'uncap', '-2'))
        self.assertEqual((balanced['preset'], balanced['fps_mode'], balanced['model_lod']), ('0', '60', '-2'))
        self.assertEqual((quiet['preset'], quiet['fps_mode'], quiet['model_lod']), ('2', '60', '0'))
        self.assertTrue(smooth['object_motion'] and balanced['object_motion'])
        self.assertFalse(quiet['object_motion'])

    def test_balanced_gives_more_detail_only_with_room(self):
        r = rate('nvidia-rtx-4060', 'Intel Core i5-12400F', 16)
        smooth, balanced = profile(r), profile(r, goal='balanced')
        self.assertEqual(balanced['preset'], smooth['preset'])  # no headroom for Native AA
        self.assertEqual(balanced['fps_mode'], '60')

    def test_a_weak_pc_keeps_its_cap(self):
        r = rate('nvidia-gtx-1650', 'Intel Core i3-10100', 16)
        for goal in hardware.GOALS:
            self.assertIn(profile(r, display=(1920, 1080), goal=goal)['fps_mode'], ('30', '60'))

    def test_unknown_goal_is_smooth(self):
        r = rate('amd-rx-9070-xt', 'AMD Ryzen 7 5800X 8-Core Processor', 32)
        self.assertEqual(profile(r, goal='fast'), profile(r))
        self.assertEqual(hardware.GOAL_FPS, {'smooth': 120, 'balanced': 60, 'quiet': 60})


if __name__ == '__main__':
    unittest.main()
