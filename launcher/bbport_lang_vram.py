# SPDX-License-Identifier: GPL-2.0-or-later
"""The video memory warning's switch (Advanced > Performance, beside the low-VRAM profile), in every
language besides English and Russian (Russian is in the code). Keyed by the English text like
bbport_lang; merged into its tables on import."""
import bbport_lang

KEYS = [
    'Warn when video memory runs low',
    'Off: no "Video memory is running low" banner in the game. Memory is freed as before; the log still says '
    'when it ran short.',
]
TEXTS = {
    'ar': [
        'التحذير عند انخفاض ذاكرة الفيديو',
        'إيقاف: لا تظهر لافتة "ذاكرة الفيديو منخفضة" في اللعبة. تُحرَّر الذاكرة كما من قبل، ويذكر السجل متى نقصت.',
    ],
    'es': [
        'Avisar cuando quede poca memoria de vídeo',
        'Desactivado: sin el aviso "Queda poca memoria de vídeo" en el juego. La memoria se libera como antes; el '
        'registro sigue indicando cuándo faltó.',
    ],
    'pt': [
        'Avisar quando a memória de vídeo estiver baixa',
        'Desligado: sem o aviso "A memória de vídeo está baixa" no jogo. A memória é liberada como antes; o log '
        'continua dizendo quando faltou.',
    ],
    'fr': [
        'Avertir quand la mémoire vidéo est presque pleine',
        'Désactivé : plus de bandeau « La mémoire vidéo est presque pleine » en jeu. La mémoire est libérée comme '
        'avant ; le journal indique toujours quand elle a manqué.',
    ],
    'de': [
        'Warnen, wenn der Videospeicher knapp wird',
        'Aus: kein Hinweis „Videospeicher wird knapp“ im Spiel. Speicher wird wie bisher freigegeben; das Protokoll '
        'nennt weiterhin, wann er knapp war.',
    ],
    'it': [
        'Avvisa quando la memoria video sta per esaurirsi',
        'Disattivato: nessun avviso "La memoria video sta per esaurirsi" nel gioco. La memoria viene liberata come '
        'prima; il registro indica comunque quando è mancata.',
    ],
    'pl': [
        'Ostrzegaj, gdy kończy się pamięć wideo',
        'Wyłączone: brak komunikatu „Kończy się pamięć wideo” w grze. Pamięć jest zwalniana jak dotąd; dziennik '
        'nadal podaje, kiedy jej zabrakło.',
    ],
    'tr': [
        'Video belleği azaldığında uyar',
        'Kapalı: oyunda "Video belleği azalıyor" uyarısı çıkmaz. Bellek eskisi gibi boşaltılır; günlük yine ne zaman '
        'yetmediğini yazar.',
    ],
    'zh': [
        '显存不足时发出警告',
        '关闭：游戏中不再显示“显存即将不足”横幅。显存仍照常释放；日志仍会记录何时不足。',
    ],
    'ja': [
        'ビデオメモリが不足しそうなときに警告する',
        'オフ：ゲーム内に「ビデオメモリが不足しています」のバナーを表示しません。メモリは従来どおり解放され、'
        '不足した時はログに記録されます。',
    ],
    'ko': [
        '비디오 메모리가 부족할 때 경고',
        '끄기: 게임에서 "비디오 메모리가 부족합니다" 배너를 표시하지 않습니다. 메모리는 전처럼 해제되며, 부족했던 때는 '
        '로그에 계속 기록됩니다.',
    ],
}

for _language, _texts in TEXTS.items():
    assert len(_texts) == len(KEYS), (_language, len(_texts), len(KEYS))
    bbport_lang.EXTRA_TRANSLATIONS.setdefault(_language, {}).update(zip(KEYS, _texts))
