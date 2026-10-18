# SPDX-License-Identifier: GPL-2.0-or-later
"""ML-FG selection follows the selected adapter's verified capabilities."""
import importlib
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
sys.path.insert(0,str(ROOT/'scripts'))
import bbport_fg401 as fg
import bbport_launcher_win as launcher

class CapabilityTests(unittest.TestCase):
    def result(self,stdout,code=0):
        with patch.object(fg.subprocess,'run',return_value=types.SimpleNamespace(returncode=code,stdout=stdout)):
            return fg.query(ROOT)

    def test_exact_verified_provider(self):
        self.assertTrue(self.result('{"supported":true,"provider":"4.0.1"}')['supported'])

    def test_unavailable_or_other_provider(self):
        for stdout in ['{}','[]','null','broken','{"supported":false}',
                       '{"supported":true,"provider":"3.1.6"}',
                       '{"supported":1,"provider":"4.0.1"}']:
            with self.subTest(stdout=stdout):
                self.assertFalse(self.result(stdout)['supported'])
        self.assertFalse(self.result('{"supported":true,"provider":"4.0.1"}',1)['supported'])

    def test_missing_and_timeout(self):
        for error in [FileNotFoundError(),subprocess.TimeoutExpired('probe',15)]:
            with self.subTest(error=error),patch.object(fg.subprocess,'run',side_effect=error):
                self.assertFalse(fg.query(ROOT)['supported'])

    def test_translations_and_mode_label(self):
        self.assertEqual(len(fg.TEXTS),13)
        previous=launcher.LANG
        try:
            for language in fg.TEXTS:
                launcher.LANG=language
                for key in fg.KEYS:
                    self.assertEqual(launcher._(key),fg.TRANSLATIONS[language][key])
                label=fg.TEXTS[language][0]
                self.assertIn('RX 9000',label)
                self.assertIn('2×',label)
                self.assertIn('SDR',label)
            self.assertFalse(any('ready (' in key for key in fg.KEYS))
        finally:
            launcher.LANG=previous

class SelectionTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            from tkinter import ttk
            self.root=tk.Tk()
        except Exception as error:
            self.skipTest(f'Tk session unavailable: {error}')
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        obj=launcher.Launcher.__new__(launcher.Launcher)
        obj.tk=tk;obj.ttk=ttk;obj.root=self.root;obj.vars={}
        obj.ini=launcher.INI_DEFAULTS.copy();obj.app=launcher.APP_DEFAULTS.copy()
        obj.fg401_support=None;obj.fg401_refreshers=[]
        self.parent=ttk.Frame(self.root)
        obj.fg401_status=ttk.Label(self.parent)
        obj.fg401_status.grid(row=1,column=0)
        self.obj=obj
        self.box=obj.fg401_choice(self.parent)
        self.var=obj.var('frame_gen','ini')

    def test_available_only_after_probe(self):
        self.assertFalse(any('4.0.1' in text for text in self.box['values']))
        self.obj.fg401_support={'supported':True}
        self.obj.refresh_fg401()
        self.assertTrue(any('4.0.1' in text for text in self.box['values']))
        self.assertEqual(self.obj.fg401_status.cget('text'),'')
        self.assertEqual(self.obj.fg401_status.winfo_manager(),'')

    def test_stored_selection_fallback(self):
        self.var.set('fsr401')
        self.assertEqual(self.var.get(),'fsr401')
        self.obj.fg401_support={'supported':False}
        self.obj.refresh_fg401()
        self.assertEqual(self.var.get(),'fsr3')
        self.assertFalse(any('4.0.1' in text for text in self.box['values']))
        self.assertEqual(self.obj.fg401_status.winfo_manager(),'grid')

    def test_existing_selection_preserved(self):
        for supported in [True,False]:
            self.obj.fg401_support={'supported':supported}
            for value in ['off','fsr3','dlss']:
                self.var.set(value)
                self.obj.refresh_fg401()
                self.assertEqual(self.var.get(),value)

if __name__=='__main__':
    unittest.main()
