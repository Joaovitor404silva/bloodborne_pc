# SPDX-License-Identifier: GPL-2.0-or-later
"""The texts of sharpening with FSR 4 (off in the settings made for the PC, the hint on All graphics). In every
language besides English; keyed by the English text like bbport_lang, merged into its tables on import."""
import bbport_lang

KEYS = [
    # sharpening with FSR 4: All graphics, the settings for this PC (bbport_hardware.SHARPEN_WITH_FSR4)
    'Off with FSR 4: it sharpens by itself, and sharpening on top of it brings flaws along edges.',
    'FSR 4 sharpens by itself: sharpening on top of it brings flaws along edges.',
    'Derived from the requirements and the hardware check on bbport.de for your PC at {} ({}). Chromatic aberration, '
    'depth of field, motion blur and sharpening are taste and stay as you set them; only with FSR 4, which sharpens '
    'by itself, sharpening goes off.',
]

TEXTS = {
    'ru': [
        'С FSR 4 — выкл.: FSR 4 сам повышает резкость, и дополнительная резкость поверх него даёт артефакты на '
        'краях.',
        'FSR 4 сам повышает резкость: дополнительная резкость поверх него даёт артефакты на краях.',
        'Подобрано по системным требованиям и проверке оборудования на bbport.de для вашего ПК при {} ({}). '
        'Хроматическая аберрация, глубина резкости, размытие в движении и резкость — дело вкуса и остаются такими, '
        'как вы их задали; только с FSR 4, который сам повышает резкость, резкость выключается.',
    ],
    'ar': [
        'إيقاف مع FSR 4: فهو يزيد الحدة بنفسه، وزيادة الحدة فوقه تُظهر عيوبًا على الحواف.',
        'يزيد FSR 4 الحدة بنفسه: زيادة الحدة فوقه تُظهر عيوبًا على الحواف.',
        'مستمدة من المتطلبات وفحص العتاد على bbport.de لحاسوبك عند {} ({}). الانحراف اللوني وعمق المجال وضبابية '
        'الحركة والحدة مسألة ذوق، وتبقى كما ضبطتها؛ فقط مع FSR 4، الذي يزيد الحدة بنفسه، تُطفأ الحدة.',
    ],
    'es': [
        'Desactivada con FSR 4: ya aplica nitidez por sí mismo, y más nitidez encima deja defectos en los bordes.',
        'FSR 4 aplica nitidez por sí mismo: más nitidez encima deja defectos en los bordes.',
        'Basado en los requisitos y la comprobación de hardware de bbport.de para tu PC a {} ({}). La aberración '
        'cromática, la profundidad de campo, el desenfoque de movimiento y la nitidez son cuestión de gusto y se '
        'quedan como los pusiste; solo con FSR 4, que aplica nitidez por sí mismo, la nitidez se desactiva.',
    ],
    'pt': [
        'Desligada com FSR 4: ele já aplica nitidez sozinho, e mais nitidez por cima causa defeitos nas bordas.',
        'O FSR 4 aplica nitidez sozinho: mais nitidez por cima causa defeitos nas bordas.',
        'Derivado dos requisitos e da verificação de hardware do bbport.de para o seu PC em {} ({}). Aberração '
        'cromática, profundidade de campo, desfoque de movimento e nitidez são questão de gosto e ficam como você '
        'definiu; só com o FSR 4, que aplica nitidez sozinho, a nitidez é desligada.',
    ],
    'fr': [
        'Désactivée avec FSR 4 : il accentue la netteté lui-même, et une netteté ajoutée par-dessus crée des défauts '
        'sur les contours.',
        'FSR 4 accentue la netteté lui-même : une netteté ajoutée par-dessus crée des défauts sur les contours.',
        'Déduit de la configuration requise et de la vérification du matériel de bbport.de pour votre PC en {} ({}). '
        'L’aberration chromatique, la profondeur de champ, le flou de mouvement et la netteté sont une affaire de '
        'goût et restent tels que vous les avez réglés ; seulement avec FSR 4, qui accentue la netteté lui-même, la '
        'netteté est désactivée.',
    ],
    'de': [
        'Aus mit FSR 4: FSR 4 schärft selbst, und Schärfen obendrauf bringt Fehler an Kanten.',
        'FSR 4 schärft selbst: Schärfen obendrauf bringt Fehler an Kanten.',
        'Abgeleitet aus den Anforderungen und dem Hardware-Check auf bbport.de für deinen PC bei {} ({}). '
        'Chromatische Aberration, Tiefenschärfe, Bewegungsunschärfe und Schärfe sind Geschmackssache und bleiben, '
        'wie du sie eingestellt hast; nur mit FSR 4, das selbst schärft, geht das Schärfen aus.',
    ],
    'it': [
        'Disattivata con FSR 4: aumenta già la nitidezza da solo, e altra nitidezza sopra crea difetti sui bordi.',
        'FSR 4 aumenta la nitidezza da solo: altra nitidezza sopra crea difetti sui bordi.',
        'Ricavate dai requisiti e dalla verifica hardware su bbport.de per il tuo PC a {} ({}). Aberrazione '
        'cromatica, profondità di campo, sfocatura di movimento e nitidezza sono questione di gusti e restano come le '
        'hai impostate; solo con FSR 4, che aumenta la nitidezza da solo, la nitidezza viene disattivata.',
    ],
    'pl': [
        'Wyłączone z FSR 4: sam wyostrza obraz, a wyostrzanie na nim daje błędy na krawędziach.',
        'FSR 4 sam wyostrza obraz: wyostrzanie na nim daje błędy na krawędziach.',
        'Wyznaczone na podstawie wymagań i testu sprzętu z bbport.de dla twojego PC przy {} ({}). Aberracja '
        'chromatyczna, głębia ostrości, rozmycie ruchu i wyostrzanie to kwestia gustu i pozostają tak, jak je '
        'ustawiono; tylko z FSR 4, który sam wyostrza obraz, wyostrzanie zostaje wyłączone.',
    ],
    'tr': [
        'FSR 4 ile kapalı: kendisi keskinleştirir, üstüne keskinleştirme kenarlarda bozulmalara yol açar.',
        'FSR 4 kendisi keskinleştirir: üstüne keskinleştirme kenarlarda bozulmalara yol açar.',
        'bbport.de’deki gereksinimlerden ve donanım kontrolünden, bilgisayarınız için {} çözünürlükte ({}) türetildi. '
        'Renk sapması, alan derinliği, hareket bulanıklığı ve keskinleştirme kişisel tercihtir ve ayarladığınız gibi '
        'kalır; yalnızca kendisi keskinleştiren FSR 4 ile keskinleştirme kapatılır.',
    ],
    'zh': [
        '使用 FSR 4 时关闭：它自带锐化，再叠加锐化会让边缘出现瑕疵。',
        'FSR 4 自带锐化：再叠加锐化会让边缘出现瑕疵。',
        '根据 bbport.de 上的配置要求和硬件检测，针对你的电脑在 {}（{}）下得出。色差、景深、动态模糊和锐化属于个人喜好，'
        '会保持你的设置不变；只有使用自带锐化的 FSR 4 时，锐化会被关闭。',
    ],
    'ja': [
        'FSR 4 ではオフ：FSR 4 は自らシャープ化するため、さらにシャープ化すると輪郭に乱れが出ます。',
        'FSR 4 は自らシャープ化します：さらにシャープ化すると輪郭に乱れが出ます。',
        'bbport.de の動作環境とハードウェアチェックをもとに、この PC の {}（{}）向けに算出しました。色収差、被写界深度、'
        'モーションブラー、シャープ化は好みの問題なので、設定したままになります。ただし自らシャープ化する FSR 4 では、'
        'シャープ化はオフになります。',
    ],
    'ko': [
        'FSR 4에서는 끄기: FSR 4가 스스로 선명화하므로, 그 위에 선명화를 더하면 가장자리에 결함이 생깁니다.',
        'FSR 4는 스스로 선명화합니다: 그 위에 선명화를 더하면 가장자리에 결함이 생깁니다.',
        'bbport.de의 요구 사양과 하드웨어 검사를 바탕으로 이 PC의 {} ({})에 맞춘 설정입니다. 색수차, 피사계 심도, '
        '모션 블러, 선명화는 취향의 문제이므로 설정한 그대로 유지됩니다. 다만 스스로 선명화하는 FSR 4에서는 선명화가 '
        '꺼집니다.',
    ],
}

for _language, _texts in TEXTS.items():
    assert len(_texts) == len(KEYS), (_language, len(_texts), len(KEYS))
    bbport_lang.EXTRA_TRANSLATIONS.setdefault(_language, {}).update(zip(KEYS, _texts))
