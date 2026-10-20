# SPDX-License-Identifier: GPL-2.0-or-later
"""The launcher's search: a field at the top of the side bar (Ctrl+F) that finds settings, pages
and Help topics by the words players use ("ruckelt", "black screen", "controller"), not only by
the settings' names. Enter or a click opens the page, scrolls to the setting and marks it for a
moment; settings of the expert view are found in the simple view too (and say so).

Every row, switch and folder field registers itself while the pages are built (index_entry);
the pages, the Help topics and a few cards are added in search_ready(). Words in WORDS add the
players' words to a setting (by its key), a page or a Help topic, in German and English.
"""
import unicodedata

import bbport_theme as theme

L = None  # bbport_launcher_win, set by bind()


def bind(module):
    global L
    L = module


def _(*texts):
    return L._(*texts) if L else texts[0]


# The players' words for a setting key, a page ('page:…') or a Help topic ('topic:…').
WORDS = {
    'fullscreen': 'vollbild fenster fullscreen window borderless randlos',
    'hdr': 'hdr helligkeit brightness',
    'fps_mode': 'fps bildrate framerate frame rate 30 60 120 unbegrenzt unlock flussig ruckelt lag',
    'frame_cap': 'fps grenze limit cap 120 144 165 240',
    'frames_ahead': 'latenz input lag ruckelt stutter',
    'present_mode': 'vsync tearing mailbox fifo',
    'output_res': 'auflosung resolution 4k 1440p 1080p 2160p 720p scharf unscharf pixelig',
    'upscaler': 'upscaler fsr dlss taa hochskalierung kantenglattung scharf unscharf',
    'preset': 'qualitat quality balanced performance native aa scharfer schoner',
    'sharpen': 'scharf scharfe unscharf blurry verwaschen rcas', 'sharpness': 'scharf scharfe unscharf blurry rcas',
    'object_motion': 'ghosting schlieren nachziehen bewegungsvektoren',
    'model_lod': 'lod detail modelldetail details pop-in plopp modelle sichtweite',
    'fov': 'sichtfeld fov field of view weitwinkel kamera',
    'show_fps': 'fps zahler counter anzeige overlay',
    'frame_gen': 'frame generation zwischenbilder dlss fsr fg',
    'hud_position': 'hud ultrawide 21:9 32:9 interface',
    'live_resolution': 'auflosung neustart restart',
    'effect_motion_blur': 'unscharfe motion blur bewegungsunscharfe',
    'effect_dof': 'tiefenscharfe depth of field unscharf hintergrund',
    'effect_chromatic_aberration': 'farbsaum chromatic aberration farbrander',
    'effect_ssao': 'ssao umgebungsverdeckung schatten ambient occlusion',
    'effect_dynamic_shadows': 'schatten shadows licht',
    'effect_ssr': 'spiegelungen reflections ssr',
    'effect_game_aa': 'kantenglattung anti aliasing aa treppen',
    'language': 'sprache language deutsch englisch untertitel text subtitles',
    'voice_language': 'stimmen voice sprache synchro audio',
    'player_name': 'name psn spielername',
    'game_dir': 'spielordner eboot cusa03173 ordner pfad folder spiel',
    'dlc_dir': 'dlc old hunters erweiterung',
    'user_dir': 'spielstande saves speicherstand ordner',
    'skip_intro': 'intro logos video uberspringen skip',
    'mute_unfocused': 'ton stumm sound mute hintergrund lautstarke volume audio',
    'cheat_no_death': 'unsterblich unverwundbar nie sterben god mode godmode immortal invincible',
    'button:shortcut': 'desktop verknupfung verknuepfung shortcut icon symbol',
    'button:steam': 'steam bibliothek library non-steam deck',
    'button:port_folder': 'ordner port folder installation explorer',
    'button:updates': 'update updates aktualisieren neue version',
    'button:report': 'bericht report support zip discord fehler',
    'button:shader_cache': 'shader cache leeren loschen clear',
    'online': 'online koop coop multiplayer freunde glocke beschworen invasion',
    'online_pool': 'server online shadnet supermedo hunters dream thd bbhost spielen mit play with',
    'mods_enabled': 'mods mod remaster texturen',
    'translucent_window': 'transparent durchsichtig transparenz glas acrylic opacity deckkraft see through '
                          'unreadable unlesbar',
    'ui_language': 'sprache language launcher',
    'draw_pipe': 'absturz crash instabil pipeline',
    'close_on_play': 'schliessen beenden',
    'page:controls': 'tasten tastatur maus controller gamepad belegung tastenbelegung steuerung keyboard mouse keys '
                     'bindings keybindings keybinds xbox dualsense',
    'page:saves': 'spielstand spielstande save saves import shadps4 bbhost awaken backup sicherung charakter',
    'page:help': 'hilfe help problem fehler absturz crash',
    'action:setup': 'einrichtung ersteinrichtung setup assistent guide wizard erster start first start neu '
                    'wiederholen repeat again',
    'page:trophies': 'erfolge trophaen trophies achievements platin',
    'page:online': 'online koop coop multiplayer freunde hunters dream shadnet anmelden discord',
    'page:mods': 'mods mod remaster patches',
    'page:system': 'pc hardware grafikkarte prozessor anforderungen requirements benchmark test messen stabilitat beta',
    'page:picture': 'grafik bild leistung fps ziel flussig ausgewogen leise laptop akku messen benchmark',
    'page:graphics': 'grafik graphics alle einstellungen',
    'page:cheats': 'cheats unsterblich god mode tricks debug',
    'page:advanced': 'erweitert update verknupfung steam diagnose',
    'page:log': 'log protokoll ausgabe',
    'page:game': 'spiel sprache ordner eboot dlc',
    'topic:page_file': 'absturz crash code 3 stürzt schliesst startet nicht speicher auslagerungsdatei ram guest memory',
    'topic:eboot_modified': 'eboot 30 fps 60fps patch lance sauber clean gesten',
    'topic:eboot_truncated': 'eboot abgeschnitten out of bounds kaputt',
    'topic:eboot_unreadable': 'eboot lesen self',
    'topic:version': '1.09 version update 30 fps',
    'topic:update_only': 'gxshader update ordner startet nicht',
    'topic:empty_files': 'leere dateien entpacken kaputt',
    'topic:antivirus': 'virenscanner antivirus defender winerror blockiert permission',
    'topic:location': 'onedrive programme program files ordner',
    'topic:vram': 'vram grafikspeicher ruckelt texturen gesichter memory',
    'topic:driver': 'treiber driver device lost absturz grafikkarte',
    'topic:shader_cache': 'ruckeln ruckelt stutter erste minuten shader',
    'topic:smartscreen': 'smartscreen windows geschutzt schutz warnung',
    'topic:black_screen': 'schwarz schwarzer bildschirm black screen shader cache leeren',
}


def fold(text):
    """Lower case without accents (ä→a, ß→ss): what the player types matches either way."""
    text = str(text).casefold().replace('ß', 'ss')
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))



def near(word, text):
    """A word as the text has it at the start of one of its words, without a plural or inflected
    ending ("details" -> "detail", "einstellungen" -> "einstellung"); None if there is none."""
    for cut in (1, 2):
        stem = word[:-cut]
        if len(stem) >= 5 and f' {stem}' in f' {text}':
            return stem
    return None


def shown(widget, page):
    """Whether a widget is laid out on its page (not in a part that is hidden for another choice)."""
    while widget is not None and widget is not page:
        try:
            if not widget.winfo_manager():
                return False
        except Exception:  # a widget that is gone
            return False
        widget = widget.master
    return True

class SearchMixin:
    """The search field, its index and the jump to a result."""

    # ---- the index -------------------------------------------------------------------------------
    def index_entry(self, widget, title, hint='', key=None, mark=None):
        """A setting on a page: found by its title, its hint and WORDS[key]; `mark` is the widget
        marked after the jump (its label)."""
        if not hasattr(self, 'search_settings'):
            self.search_settings = []
        if title:
            self.search_settings.append({'kind': 'setting', 'widget': widget, 'mark': mark or widget,
                                        'title': str(title), 'hint': str(hint or ''), 'key': key})

    def search_ready(self):
        """After every page is built: which page each setting is on, then the pages and the Help topics."""
        import bbport_help
        titles = dict((name, _(*title)) for name, title in L.NAV_SIMPLE + L.NAV_EXPERT)
        titles['log'] = _('Log', 'Журнал')
        self.page_titles = titles
        pages = {str(frame): name for name, frame in self.pages.items()}
        entries = []
        for entry in getattr(self, 'search_settings', []):
            widget, page = entry['widget'], None
            while widget is not None and page is None:
                page = pages.get(str(widget))
                widget = widget.master
            if page:
                entry['page'] = page
                entries.append(entry)
        for name, title in titles.items():
            entries.append({'kind': 'page', 'page': name, 'title': title, 'hint': '', 'key': f'page:{name}'})
        for key in bbport_help.TOPIC_ORDER:
            title, why, _steps = bbport_help.TOPICS[key]
            entries.append({'kind': 'topic', 'page': 'help', 'topic': key, 'title': _(title), 'hint': _(why),
                            'key': f'topic:{key}'})
        entries.append({'kind': 'action', 'page': 'game', 'run': 'open_setup', 'title': _('Repeat the setup'),
                        'hint': _('Set everything up again, step by step.'), 'key': 'action:setup'})
        for entry in entries:
            words = WORDS.get(entry.get('key') or '', '')
            entry['haystack'] = (fold(entry['title']), fold(entry['hint']), fold(words))
        self.search_entries = entries

    def search(self, query, limit=7):
        """The best entries for a query: every word must be found; the title counts most."""
        words = [w for w in fold(query).split() if w]
        if not words:
            return []
        scored = []
        for entry in self.search_entries:
            title, hint, extra = entry['haystack']
            score = 0
            for word in words:
                penalty = 0
                if word not in title and word not in extra and word not in hint:
                    stem = near(word, title + ' ' + extra + ' ' + hint)
                    if stem:  # a near form counts a little less than the word itself
                        word, penalty = stem, 1
                score -= penalty
                in_title = f' {word}' in f' {title}'
                if in_title:
                    score += 6
                elif word in title:
                    score += 4
                elif f' {word}' in f' {extra}' or word in extra:
                    score += 3
                elif word in hint:
                    score += 1
                else:
                    score = 0
                    break
            if score and entry['kind'] == 'setting' and not shown(entry.get('widget'),
                                                                  getattr(self, 'pages', {}).get(entry['page'])):
                score = 0
            if score:
                bonus = {'setting': 0.5, 'topic': 0.6, 'page': 0.3, 'action': 0.6}[entry['kind']]  # symptoms: the fix first
                expert = entry['page'] in L.EXPERT_PAGES
                scored.append((score + bonus - (0.2 if expert and self.app.get('ui_mode') != 'expert' else 0), entry))
        scored.sort(key=lambda item: -item[0])
        seen, out = set(), []
        for _score, entry in scored:
            ident = (entry['kind'], entry['page'], entry['title'])
            if ident not in seen:
                seen.add(ident)
                out.append(entry)
            if len(out) == limit:
                break
        return out

    # ---- the field and its results ----------------------------------------------------------------
    def build_search(self, side):
        tk, px = self.tk, self.px
        box = tk.Frame(side, bg=theme.LINE if hasattr(theme, 'LINE') else theme.BORDER, padx=1, pady=1)
        box.pack(fill='x', padx=px(14), pady=(0, px(10)))
        inner = tk.Frame(box, bg=theme.DEEP)
        inner.pack(fill='x')
        tk.Label(inner, text='', bg=theme.DEEP, fg=theme.MUTED, font=(theme.ICONS, 10)).pack(
            side='left', padx=(px(9), px(4)))
        self.search_var = tk.StringVar()
        entry = tk.Entry(inner, textvariable=self.search_var, bg=theme.DEEP, fg=theme.TEXT_STRONG, relief='flat', bd=0,
                         insertbackground=theme.TEXT_STRONG, font=(theme.BODY, 10), highlightthickness=0)
        entry.pack(side='left', fill='x', expand=True, ipady=px(6))
        hint = tk.Label(inner, text=_('Search…') + '   ' + _('Ctrl+F'), bg=theme.DEEP, fg=theme.MUTED,
                        font=(theme.BODY, 9))
        hint.place(in_=entry, x=0, rely=0.5, anchor='w')
        self.search_box, self.search_field, self.search_hint = box, entry, hint
        self.search_popup, self.search_results, self.search_pick = None, [], 0

        def placeholder(*_a):
            if self.search_var.get() or self.root.focus_get() is entry:
                hint.place_forget()
            else:
                hint.place(in_=entry, x=0, rely=0.5, anchor='w')
        self.search_var.trace_add('write', lambda *_a: (placeholder(), self.search_update()))
        entry.bind('<FocusIn>', lambda _e: (placeholder(), box.configure(bg=theme.GOLD), self.search_update()))
        entry.bind('<FocusOut>', lambda _e: (placeholder(), box.configure(bg=theme.BORDER),
                                             self.root.after(180, self.search_close)))
        hint.bind('<Button-1>', lambda _e: entry.focus_set())
        entry.bind('<Down>', lambda _e: self.search_move(1))
        entry.bind('<Up>', lambda _e: self.search_move(-1))
        entry.bind('<Return>', lambda _e: self.search_go())
        entry.bind('<Escape>', lambda _e: (self.search_var.set(''), self.search_close(), self.root.focus_set()))
        self.root.bind_all('<Control-f>', self.search_focus)
        box.configure(bg=theme.BORDER)

    def search_focus(self, _event=None):
        """Ctrl+F: the search field; not while a key is being bound on the Controls page (Ctrl+F
        can be a binding) or while the setup guide covers the window."""
        if getattr(self, 'remap_listening', False) or getattr(self, 'guide', None):
            return None
        self.search_field.focus_set()
        self.search_field.select_range(0, 'end')
        return 'break'

    def search_update(self):
        query = self.search_var.get().strip()
        self.search_results = self.search(query) if query else []
        self.search_pick = 0
        if not self.search_results:
            self.search_close()
            if query:
                self.search_show([None])
            return
        self.search_show(self.search_results)

    def search_where(self, entry):
        page = self.page_titles.get(entry['page'], entry['page'])
        if entry['kind'] == 'topic':
            where = _('Help') + ' · ' + _('problem')
        elif entry['kind'] == 'page':
            where = _('Page')
        else:
            where = page
        if entry['page'] in L.EXPERT_PAGES and self.app.get('ui_mode') != 'expert':
            where += ' · ' + _('expert view')
        return where

    def search_show(self, results):
        tk, px = self.tk, self.px
        if not self.search_popup:
            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.attributes('-topmost', True)
            popup.configure(bg=theme.GOLD)
            self.search_popup = popup
        popup = self.search_popup
        for child in popup.winfo_children():
            child.destroy()
        frame = tk.Frame(popup, bg=theme.CARD, padx=px(4), pady=px(4))
        frame.pack(fill='both', expand=True, padx=1, pady=1)
        self.search_rows = []
        for index, entry in enumerate(results):
            row = tk.Frame(frame, bg=theme.CARD, padx=px(8), pady=px(5), cursor='hand2')
            row.pack(fill='x')
            if entry is None:
                tk.Label(row, text=_('Nothing found. Try other words, or open Help.'), bg=theme.CARD, fg=theme.MUTED,
                         font=(theme.BODY, 9)).pack(anchor='w')
                row.bind('<Button-1>', lambda _e: (self.search_close(), self.show('help')))
                continue
            title = tk.Label(row, text=entry['title'], bg=theme.CARD, fg=theme.TEXT_STRONG, font=(theme.BODY_SEMI, 10),
                             anchor='w', justify='left', wraplength=px(330))
            title.pack(anchor='w', fill='x')
            where = tk.Label(row, text=self.search_where(entry), bg=theme.CARD, fg=theme.MUTED, font=(theme.BODY, 8),
                             anchor='w')
            where.pack(anchor='w')
            for widget in (row, title, where):
                widget.bind('<Button-1>', lambda _e, i=index: (setattr(self, 'search_pick', i), self.search_go()))
                widget.bind('<Enter>', lambda _e, i=index: self.search_mark(i))
            self.search_rows.append((row, title, where))
        self.search_mark(self.search_pick)
        field = self.search_field
        x = field.winfo_rootx() - px(30)
        y = self.search_box.winfo_rooty() + self.search_box.winfo_height() + px(4)
        popup.update_idletasks()
        popup.geometry(f'{px(370)}x{frame.winfo_reqheight() + 2}+{x}+{y}')
        popup.deiconify()

    def search_mark(self, index):
        self.search_pick = index
        for i, (row, title, where) in enumerate(getattr(self, 'search_rows', [])):
            color = theme.SURFACE if i == index else theme.CARD
            for widget in (row, title, where):
                widget.configure(bg=color)

    def search_move(self, step):
        if self.search_results:
            self.search_mark((self.search_pick + step) % len(self.search_results))
        return 'break'

    def search_close(self):
        if self.search_popup and self.root.focus_get() is not self.search_field:
            self.search_popup.destroy()
            self.search_popup = None
        elif self.search_popup and not self.search_var.get().strip():
            self.search_popup.destroy()
            self.search_popup = None

    def search_go(self):
        if not self.search_results:
            return 'break'
        entry = self.search_results[min(self.search_pick, len(self.search_results) - 1)]
        self.search_var.set('')
        if self.search_popup:
            self.search_popup.destroy()
            self.search_popup = None
        self.root.focus_set()
        self.jump(entry)
        return 'break'

    def jump(self, entry):
        """Opens a result: its page, scrolled to it and marked for a moment (a Help topic opens)."""
        if entry['kind'] == 'topic':
            self.open_topic(entry['topic'])
            return
        if entry['kind'] == 'action':
            getattr(self, entry['run'])()
            return
        if entry['page'] in L.EXPERT_PAGES and self.app.get('ui_mode') != 'expert':
            self.expert_var.set(True)  # the page and its place in the side bar, not a page out of nowhere
            self.toggle_mode()
            self.status.configure(text=_('The expert view is on now, to show this. The switch is at the bottom of '
                                         'the side bar.'), fg=theme.GOLD_LIGHT)
        self.show(entry['page'])
        if entry['kind'] == 'setting':
            self.root.update_idletasks()
            self.scroll_to(entry['widget'])
            self.root.after(60, lambda: self.flash(entry['mark']))

    def scroll_to(self, widget, above=None):
        tk = self.tk
        inner = widget
        while inner.master is not None and not isinstance(inner.master, tk.Canvas):
            inner = inner.master
        canvas = inner.master
        if canvas is None:
            return
        try:
            top = widget.winfo_rooty() - inner.winfo_rooty()
            canvas.yview_moveto(max(0, top - (above if above is not None else self.px(70))) /
                                max(1, inner.winfo_height()))
        except tk.TclError:
            pass

    def flash(self, widget):
        """A gold bar beside a widget for a moment: here it is."""
        tk, px = self.tk, self.px
        try:
            bar = tk.Frame(widget.master, bg=theme.GOLD, width=px(4))
            bar.place(in_=widget, x=-px(12), y=0, relheight=1, width=px(4))
            glow = tk.Frame(widget.master, bg=theme.GOLD)
            glow.place(in_=widget, x=-px(4), rely=1.0, y=px(1), relwidth=1, height=px(2))
        except tk.TclError:
            return
        self.root.after(1600, lambda: (bar.destroy(), glow.destroy()))
