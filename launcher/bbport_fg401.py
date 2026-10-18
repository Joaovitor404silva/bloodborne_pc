# SPDX-License-Identifier: GPL-2.0-or-later
"""Capability query and translations for the optional AMD ML-FG method."""
import json
import os
import subprocess
from pathlib import Path

def query(port, env=None):
    try:
        result=subprocess.run([str(Path(port)/'bin/bb-fg401-capabilities.exe')],
            cwd=port,env=env,capture_output=True,text=True,timeout=15,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        data=json.loads(result.stdout)
        if not isinstance(data, dict):
            return dict(supported=False,reason='check')
        if result.returncode or data.get('supported') is not True or data.get('provider')!='4.0.1':
            return dict(supported=False,reason=data.get('reason','check'))
        return dict(supported=True,reason='ready')
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return dict(supported=False,reason='check')

KEYS=('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, experimental)', 'ML-FG 4.0.1: checking support…', 'ML-FG 4.0.1 requires an RX 9000, Windows 11 and a supported AMD driver/runtime. FSR 3.1 remains available.')
TEXTS={
'en':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, experimental)', 'ML-FG 4.0.1: checking support…', 'ML-FG 4.0.1 requires an RX 9000, Windows 11 and a supported AMD driver/runtime. FSR 3.1 remains available.'),
'de':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, experimentell)', 'ML-FG 4.0.1: Unterstützung wird geprüft…', 'ML-FG 4.0.1 benötigt eine RX 9000, Windows 11 und einen unterstützten AMD-Treiber samt Laufzeitbibliothek. FSR 3.1 bleibt verfügbar.'),
'ru':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, экспериментально)', 'ML-FG 4.0.1: проверка поддержки…', 'Для ML-FG 4.0.1 нужны RX 9000, Windows 11 и совместимые драйвер и библиотеки AMD. FSR 3.1 остаётся доступной.'),
'ar':('AMD ML-FG 4.0.1 (RX 9000، 2× SDR، تجريبي)', 'ML-FG 4.0.1: جارٍ التحقق من الدعم…', 'يتطلب ML-FG 4.0.1 بطاقة RX 9000 وWindows 11 وبرنامج تشغيل ومكتبات AMD متوافقة. يبقى FSR 3.1 متاحًا.'),
'es':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, experimental)', 'ML-FG 4.0.1: comprobando compatibilidad…', 'ML-FG 4.0.1 requiere una RX 9000, Windows 11 y un controlador y bibliotecas AMD compatibles. FSR 3.1 sigue disponible.'),
'pt':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, experimental)', 'ML-FG 4.0.1: verificando compatibilidade…', 'ML-FG 4.0.1 requer uma RX 9000, Windows 11 e um driver e bibliotecas AMD compatíveis. FSR 3.1 continua disponível.'),
'fr':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, expérimental)', 'ML-FG 4.0.1 : vérification de la compatibilité…', 'ML-FG 4.0.1 nécessite une RX 9000, Windows 11 et un pilote et des bibliothèques AMD compatibles. FSR 3.1 reste disponible.'),
'it':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, sperimentale)', 'ML-FG 4.0.1: verifica della compatibilità…', 'ML-FG 4.0.1 richiede una RX 9000, Windows 11 e un driver e librerie AMD compatibili. FSR 3.1 resta disponibile.'),
'pl':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, eksperymentalne)', 'ML-FG 4.0.1: sprawdzanie obsługi…', 'ML-FG 4.0.1 wymaga RX 9000, Windows 11 oraz zgodnego sterownika i bibliotek AMD. FSR 3.1 pozostaje dostępne.'),
'tr':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, deneysel)', 'ML-FG 4.0.1: destek denetleniyor…', 'ML-FG 4.0.1 için RX 9000, Windows 11 ve uyumlu AMD sürücüsü ile kitaplıkları gerekir. FSR 3.1 kullanılabilir durumda kalır.'),
'zh':('AMD ML-FG 4.0.1（RX 9000，2× SDR，实验性）', 'ML-FG 4.0.1：正在检查支持…', 'ML-FG 4.0.1 需要 RX 9000、Windows 11 及兼容的 AMD 驱动和运行库。FSR 3.1 仍可使用。'),
'ja':('AMD ML-FG 4.0.1（RX 9000、2× SDR、実験的）', 'ML-FG 4.0.1：対応状況を確認中…', 'ML-FG 4.0.1 には RX 9000、Windows 11、対応する AMD ドライバーとランタイムが必要です。FSR 3.1 も引き続き利用できます。'),
'ko':('AMD ML-FG 4.0.1 (RX 9000, 2× SDR, 실험적)', 'ML-FG 4.0.1: 지원 확인 중…', 'ML-FG 4.0.1에는 RX 9000, Windows 11 및 호환 AMD 드라이버와 런타임이 필요합니다. FSR 3.1도 계속 사용할 수 있습니다.')
}
TRANSLATIONS={lang:dict(zip(KEYS,texts,strict=True)) for lang,texts in TEXTS.items()}
