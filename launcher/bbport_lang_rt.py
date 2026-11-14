# SPDX-License-Identifier: GPL-2.0-or-later
"""Localized texts of the path tracing fork's Path tracing section (Picture & performance, All graphics:
path_tracing_section, RT_SLIDERS)."""

KEYS = (
    'Path tracing',
    'Ray-traced moonlight, bounce light, shadows and reflections. Needs a GeForce RTX or Radeon RX 6000 or '
    'newer. In game, F9 switches it off and on to compare (about 3 seconds while the exposure adjusts).',
    'Bounce light',
    'Light bouncing off walls and floors into the shadows.',
    'Reflections',
    'Traced reflections on water, puddles, glass and polished stone.',
    'Shadows',
    'How dark the traced shadows of the moon and lamps are.',
    'Auto', 'Low', 'Medium', 'High', 'Custom',
    'Changes apply at the next start of the game. Extra variables (Advanced > Diagnostics) still override '
    'these, e.g. BB_RT_GI_STRENGTH=1.3.',
)
TEXTS = {
    'en': KEYS,
    'ru': (
        'Трассировка пути',
        'Трассированный лунный свет, отражённый свет, тени и отражения. Нужна GeForce RTX или Radeon RX 6000 '
        'и новее. В игре F9 выключает и включает её для сравнения '
        '(около 3 секунд, пока подстраивается экспозиция).',
        'Отражённый свет',
        'Свет, отражённый от стен и пола в тени.',
        'Отражения',
        'Трассированные отражения на воде, лужах, стекле и полированном камне.',
        'Тени',
        'Насколько темны трассированные тени от луны и фонарей.',
        'Авто', 'Низко', 'Средне', 'Высоко', 'Своё',
        'Изменения вступают в силу при следующем запуске игры. Доп. переменные (Дополнительно > Для '
        'разработчика) по-прежнему важнее, напр. BB_RT_GI_STRENGTH=1.3.',
    ),
    'pt': (
        'Path tracing',
        'Luar, luz rebatida, sombras e reflexos com ray tracing. Precisa de uma GeForce RTX ou Radeon RX 6000 '
        'ou mais nova. No jogo, F9 desliga e liga para comparar (cerca de '
        '3 segundos enquanto a exposição se ajusta).',
        'Luz rebatida',
        'Luz que rebate nas paredes e no chão e chega às sombras.',
        'Reflexos',
        'Reflexos traçados na água, poças, vidro e pedra polida.',
        'Sombras',
        'O quão escuras são as sombras traçadas da lua e dos lampiões.',
        'Auto', 'Baixo', 'Médio', 'Alto', 'Personalizado',
        'As mudanças valem a partir do próximo início do jogo. Variáveis extras (Avançado > Diagnóstico) '
        'continuam valendo por cima destas, ex. BB_RT_GI_STRENGTH=1.3.',
    ),
    'es': (
        'Path tracing',
        'Luz de luna, luz rebotada, sombras y reflejos con trazado de rayos. Necesita una GeForce RTX o Radeon '
        'RX 6000 o más nueva. En el juego, F9 lo apaga y enciende para '
        'comparar (unos 3 segundos mientras se ajusta la exposición).',
        'Luz rebotada',
        'Luz que rebota en paredes y suelos hacia las sombras.',
        'Reflejos',
        'Reflejos trazados en el agua, charcos, cristal y piedra pulida.',
        'Sombras',
        'Lo oscuras que son las sombras trazadas de la luna y las farolas.',
        'Auto', 'Bajo', 'Medio', 'Alto', 'Personalizado',
        'Los cambios se aplican en el próximo inicio del juego. Las variables extra (Avanzado > Diagnóstico) '
        'siguen teniendo prioridad, p. ej. BB_RT_GI_STRENGTH=1.3.',
    ),
    'fr': (
        'Path tracing',
        'Clair de lune, lumière réfléchie, ombres et reflets en lancer de rayons. Nécessite une GeForce RTX ou '
        'une Radeon RX 6000 ou plus récente. En jeu, F9 le coupe et le '
        "rallume pour comparer (environ 3 secondes le temps que l'exposition s'ajuste).",
        'Lumière réfléchie',
        'La lumière renvoyée par les murs et les sols dans les ombres.',
        'Reflets',
        "Reflets tracés sur l'eau, les flaques, le verre et la pierre polie.",
        'Ombres',
        'La noirceur des ombres tracées de la lune et des lanternes.',
        'Auto', 'Faible', 'Moyen', 'Élevé', 'Personnalisé',
        'Les changements prennent effet au prochain lancement du jeu. Les variables supplémentaires (Avancé > '
        'Diagnostic) restent prioritaires, p. ex. BB_RT_GI_STRENGTH=1.3.',
    ),
    'de': (
        'Path Tracing',
        'Raytracing für Mondlicht, indirektes Licht, Schatten und Spiegelungen. Braucht eine GeForce RTX oder '
        'Radeon RX 6000 oder neuer. Im Spiel schaltet F9 es zum '
        'Vergleich aus und an (etwa 3 Sekunden, bis sich die Belichtung anpasst).',
        'Indirektes Licht',
        'Licht, das von Wänden und Böden in die Schatten zurückgeworfen wird.',
        'Spiegelungen',
        'Berechnete Spiegelungen auf Wasser, Pfützen, Glas und poliertem Stein.',
        'Schatten',
        'Wie dunkel die berechneten Schatten von Mond und Laternen sind.',
        'Auto', 'Niedrig', 'Mittel', 'Hoch', 'Eigene',
        'Änderungen gelten ab dem nächsten Spielstart. Zusätzliche Variablen (Erweitert > Diagnose) haben '
        'weiter Vorrang, z. B. BB_RT_GI_STRENGTH=1.3.',
    ),
    'it': (
        'Path tracing',
        'Luce lunare, luce riflessa, ombre e riflessi in ray tracing. Serve una GeForce RTX o Radeon RX 6000 o '
        'più recente. In gioco, F9 lo spegne e lo riaccende per confrontare '
        "(circa 3 secondi mentre l'esposizione si adatta).",
        'Luce riflessa',
        'La luce che rimbalza su muri e pavimenti fin dentro le ombre.',
        'Riflessi',
        "Riflessi tracciati su acqua, pozzanghere, vetro e pietra levigata.",
        'Ombre',
        'Quanto sono scure le ombre tracciate della luna e delle lanterne.',
        'Auto', 'Basso', 'Medio', 'Alto', 'Personalizzato',
        "Le modifiche valgono dal prossimo avvio del gioco. Le variabili extra (Avanzate > Diagnostica) hanno "
        'ancora la precedenza, es. BB_RT_GI_STRENGTH=1.3.',
    ),
    'pl': (
        'Path tracing',
        'Śledzone promieniami światło księżyca, światło odbite, cienie i odbicia. Wymaga GeForce RTX lub Radeon '
        'RX 6000 albo nowszej. W grze F9 wyłącza i włącza je dla '
        'porównania (około 3 sekund, aż ekspozycja się dostosuje).',
        'Światło odbite',
        'Światło odbijane od ścian i podłóg w głąb cieni.',
        'Odbicia',
        'Śledzone odbicia na wodzie, kałużach, szkle i polerowanym kamieniu.',
        'Cienie',
        'Jak ciemne są śledzone cienie księżyca i latarni.',
        'Auto', 'Niskie', 'Średnie', 'Wysokie', 'Własne',
        'Zmiany działają od następnego uruchomienia gry. Dodatkowe zmienne (Zaawansowane > Diagnostyka) nadal '
        'mają pierwszeństwo, np. BB_RT_GI_STRENGTH=1.3.',
    ),
    'tr': (
        'Path tracing',
        'Işın izlemeli ay ışığı, yansıyan ışık, gölgeler ve yansımalar. GeForce RTX veya Radeon RX 6000 ya da '
        'daha yenisi gerekir. Oyunda F9 karşılaştırmak için '
        'kapatıp açar (pozlama ayarlanırken yaklaşık 3 saniye).',
        'Yansıyan ışık',
        'Duvarlardan ve zeminden gölgelere yansıyan ışık.',
        'Yansımalar',
        'Su, su birikintileri, cam ve cilalı taş üzerinde izlenen yansımalar.',
        'Gölgeler',
        'Ayın ve fenerlerin izlenen gölgelerinin ne kadar koyu olduğu.',
        'Otomatik', 'Düşük', 'Orta', 'Yüksek', 'Özel',
        'Değişiklikler oyunun bir sonraki başlatılışında geçerli olur. Ek değişkenler (Gelişmiş > Tanılama) '
        'yine önceliklidir, ör. BB_RT_GI_STRENGTH=1.3.',
    ),
    'ar': (
        'تتبع المسار',
        'ضوء القمر والضوء المرتد والظلال والانعكاسات بتتبع الأشعة. يحتاج GeForce RTX أو Radeon RX 6000 أو أحدث. '
        'داخل اللعبة يوقفه F9 ويشغله للمقارنة (نحو 3 ثوانٍ ريثما يتكيف '
        'التعريض).',
        'الضوء المرتد',
        'الضوء المرتد من الجدران والأرضيات إلى الظلال.',
        'الانعكاسات',
        'انعكاسات متتبعة على الماء والبرك والزجاج والحجر المصقول.',
        'الظلال',
        'مدى عتمة الظلال المتتبعة للقمر والفوانيس.',
        'تلقائي', 'منخفض', 'متوسط', 'مرتفع', 'مخصص',
        'تسري التغييرات عند التشغيل التالي للعبة. المتغيرات الإضافية (متقدم > التشخيص) تبقى لها الأولوية، '
        'مثل BB_RT_GI_STRENGTH=1.3.',
    ),
    'zh': (
        '路径追踪',
        '光线追踪的月光、反弹光、阴影和反射。需要 GeForce RTX 或 Radeon RX 6000 及更新的显卡。'
        '游戏中按 F9 可关闭/开启以作对比（曝光调整约需 3 秒）。',
        '反弹光',
        '从墙壁和地面反弹进阴影中的光。',
        '反射',
        '水面、水洼、玻璃和抛光石面上的追踪反射。',
        '阴影',
        '月亮和灯具的追踪阴影有多暗。',
        '自动', '低', '中', '高', '自定义',
        '更改在下次启动游戏时生效。额外变量（高级 > 诊断）仍优先于这些设置，例如 BB_RT_GI_STRENGTH=1.3。',
    ),
    'ja': (
        'パストレーシング',
        'レイトレーシングによる月光、反射光、影、映り込み。GeForce RTX または Radeon RX 6000 以降が必要です。'
        'ゲーム中は F9 でオフ/オンを切り替えて比較できます'
        '（露出の調整に約 3 秒）。',
        '反射光',
        '壁や床から影の中へ跳ね返る光。',
        '映り込み',
        '水面、水たまり、ガラス、磨かれた石へのトレースされた映り込み。',
        '影',
        '月とランプのトレースされた影の暗さ。',
        '自動', '低', '中', '高', 'カスタム',
        '変更は次回のゲーム起動から反映されます。追加の変数（詳細 > 診断）が引き続き優先されます。'
        '例: BB_RT_GI_STRENGTH=1.3。',
    ),
    'ko': (
        '패스 트레이싱',
        '레이 트레이싱 달빛, 반사광, 그림자, 반사. GeForce RTX 또는 Radeon RX 6000 이상이 필요합니다. '
        '게임 중 F9로 끄고 켜서 비교할 수 있습니다(노출 조정에 약 3초).',
        '반사광',
        '벽과 바닥에서 그림자 속으로 튕겨 들어오는 빛.',
        '반사',
        '물, 웅덩이, 유리, 광택 있는 돌에 추적된 반사.',
        '그림자',
        '달과 등불의 추적된 그림자가 얼마나 어두운지.',
        '자동', '낮음', '중간', '높음', '사용자 지정',
        '변경 사항은 다음 게임 실행부터 적용됩니다. 추가 변수(고급 > 진단)가 여전히 우선합니다. '
        '예: BB_RT_GI_STRENGTH=1.3.',
    ),
}
TRANSLATIONS = {language: dict(zip(KEYS, texts, strict=True)) for language, texts in TEXTS.items()}
