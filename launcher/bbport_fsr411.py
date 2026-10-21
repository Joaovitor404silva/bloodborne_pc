# SPDX-License-Identifier: GPL-2.0-or-later
"""Selected-adapter support and installed files are separate FSR 4.1.1 checks."""
import json
import os
from pathlib import Path
import subprocess

_cache = {}
DLL = {'vk': 'amd_fidelityfx_upscaler_vk.dll', 'dx12': 'amd_fidelityfx_upscaler_dx12.dll'}


def executable(port):
    packaged = Path(port) / 'bin/bb-gpu-capabilities.exe'
    return packaged if packaged.is_file() else Path(port) / 'out/bb-gpu-capabilities.exe'


def vulkan_folder(port, data_dir, env):
    folder = Path(env.get('BB_FSR4VK_DIR') or Path(env.get('BB_DATA_DIR') or data_dir) / 'fsr4vk')
    return folder if folder.is_absolute() else Path(port) / folder


def environment(port, settings=None):
    env = dict(os.environ)
    for item in str((settings or {}).get('extra_env', '')).split():
        if '=' in item:
            key, value = item.split('=', 1)
            env[key] = value
    if not (Path(port) / 'bin/SDL3.dll').is_file():
        clang = Path(env.get('MSYS2_ROOT', r'C:\msys64')) / 'clang64/bin'
        env['PATH'] = str(clang) + os.pathsep + env.get('PATH', '')
    return env


def query(port, env=None, refresh=False):
    port = Path(port)
    env = environment(port) if env is None else env
    exe = executable(port)
    runtime = exe.parent / DLL['dx12']
    def stamp(path):
        try:
            s = path.stat()
            return s.st_size, s.st_mtime_ns
        except OSError:
            return None
    key = (str(exe), stamp(exe), stamp(runtime), tuple(sorted(env.items())))
    if not refresh and key in _cache:
        return _cache[key]
    try:
        result = subprocess.run([str(exe), '--fsr411'], cwd=port, env=env,
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        data = json.loads(result.stdout)
        if result.returncode or not isinstance(data, dict) or type(data.get('vendor_id')) is not int:
            raise ValueError('invalid capability response')
        for method in ('vk', 'dx12'):
            status = data.get(method)
            if not isinstance(status, dict) or type(status.get('supported')) is not bool or \
                    not isinstance(status.get('reason'), str) or not isinstance(status.get('detail'), str):
                raise ValueError('invalid method response')
        _cache[key] = data
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {'vendor_id': None, **{m: dict(supported=False, reason='check', detail='')
                                     for m in ('vk', 'dx12')}}


def default_backend(port, settings=None):
    return 'dx12' if query(port, environment(port, settings)).get('vendor_id') == 0x1002 else 'vk'


def method_status(port, data_dir, method, capabilities, fetch_fsr4vk, env=None):
    """Recheck files after a download; never turn file absence into a GPU diagnosis."""
    env = os.environ if env is None else env
    hardware = capabilities and capabilities[method]
    # These results are independent of the package. A download cannot supply GPU features.
    hardware_failure = hardware and hardware['reason'] in ('hardware', 'driver', 'adapter', 'interop')
    missing_status = None
    if method == 'vk':
        if env.get('BB_FSR4VK') == '0':
            return dict(supported=False, reason='disabled', detail='BB_FSR4VK=0')
        folder = vulkan_folder(port, data_dir, env)
        missing = [name for _, name, size, sha in fetch_fsr4vk.FILES
                   if not fetch_fsr4vk.verified(folder / name, size, sha)]
        if missing:
            missing_status = dict(supported=False, reason='download', detail=', '.join(missing))
    else:
        exe = executable(port)
        paths = [exe.parent / DLL['dx12']] if exe.is_file() else \
            [Path(port) / sub / DLL['dx12'] for sub in ('bin', 'out')]
        try:
            present = any(p.is_file() and p.stat().st_size for p in paths)
        except OSError:
            present = False
        if not present:
            missing_status = dict(supported=False, reason='files', detail=DLL['dx12'])
    if hardware_failure:
        return {**hardware, 'files_problem': missing_status}
    if missing_status:
        return missing_status
    if capabilities is None:
        return dict(supported=False, reason='checking', detail='')
    return capabilities[method]


def message(status, translate):
    key = {
        'ready': 'Available for this GPU and driver.',
        'checking': 'Checking GPU and driver support…',
        'check': 'Support check failed. Recheck support or update the driver.',
        'download': 'Download fsr4vk in Graphics. Missing or changed files: {}',
        'files': 'Reinstall the Windows package. Missing file: {}',
        'hardware': 'GPU/driver requirement missing: {}',
        'driver': 'GPU/driver requirement missing: {}',
        'adapter': 'GPU/driver requirement missing: {}',
        'interop': 'GPU/driver requirement missing: {}',
        'runtime': 'AMD runtime could not be loaded: {}',
        'provider': 'AMD FSR 4.1.1 is unavailable for this GPU/driver: {}',
        'disabled': 'Provider disabled: {}',
    }.get(status['reason'], 'Support check failed. Recheck support or update the driver.')
    text = translate(key).format(status.get('detail', ''))
    if status.get('files_problem'):
        text += '\n' + message(status['files_problem'], translate)
    return text


KEYS = ('Available for this GPU and driver.', 'Checking GPU and driver support…',
    'Support check failed. Recheck support or update the driver.',
    'Download fsr4vk in Graphics. Missing or changed files: {}',
    'Reinstall the Windows package. Missing file: {}',
    'GPU/driver requirement missing: {}', 'AMD runtime could not be loaded: {}',
    'AMD FSR 4.1.1 is unavailable for this GPU/driver: {}', 'Provider disabled: {}', 'Recheck support')
TEXTS = {
    'en': KEYS,
    'de': ('Für diese GPU und diesen Treiber verfügbar.', 'GPU- und Treiberunterstützung wird geprüft…',
        'Unterstützung konnte nicht geprüft werden. Erneut prüfen oder Treiber aktualisieren.',
        'fsr4vk unter Grafik herunterladen. Fehlende oder geänderte Dateien: {}',
        'Windows-Paket erneut installieren. Fehlende Datei: {}',
        'GPU-/Treibervoraussetzung fehlt: {}', 'AMD-Laufzeitbibliothek konnte nicht geladen werden: {}',
        'AMD FSR 4.1.1 ist für diese GPU/Treiber-Kombination nicht verfügbar: {}',
        'Provider deaktiviert: {}', 'Erneut prüfen'),
    'ru': ('Доступно для этой видеокарты и драйвера.', 'Проверка видеокарты и драйвера…',
        'Проверка поддержки не удалась. Повторите её или обновите драйвер.',
        'Скачайте fsr4vk в разделе «Графика». Отсутствующие или изменённые файлы: {}',
        'Переустановите пакет Windows. Отсутствует файл: {}',
        'Не выполнено требование видеокарты/драйвера: {}', 'Не удалось загрузить библиотеку AMD: {}',
        'AMD FSR 4.1.1 недоступна для этой видеокарты/драйвера: {}',
        'Провайдер отключён: {}', 'Проверить снова'),
    'es': ('Disponible para esta GPU y controlador.', 'Comprobando GPU y controlador…',
        'No se pudo comprobar la compatibilidad. Reintenta o actualiza el controlador.',
        'Descarga fsr4vk en Gráficos. Archivos ausentes o modificados: {}',
        'Reinstala el paquete de Windows. Falta el archivo: {}',
        'Falta un requisito de GPU/controlador: {}', 'No se pudo cargar la biblioteca AMD: {}',
        'AMD FSR 4.1.1 no está disponible para esta GPU/controlador: {}',
        'Proveedor desactivado: {}', 'Comprobar de nuevo'),
    'pt': ('Disponível para esta GPU e driver.', 'Verificando GPU e driver…',
        'Não foi possível verificar o suporte. Tente novamente ou atualize o driver.',
        'Baixe fsr4vk em Gráficos. Arquivos ausentes ou alterados: {}',
        'Reinstale o pacote Windows. Arquivo ausente: {}',
        'Requisito de GPU/driver ausente: {}', 'Não foi possível carregar a biblioteca AMD: {}',
        'AMD FSR 4.1.1 indisponível para esta GPU/driver: {}',
        'Provedor desativado: {}', 'Verificar novamente'),
    'fr': ('Disponible pour ce GPU et ce pilote.', 'Vérification du GPU et du pilote…',
        'Vérification impossible. Réessayez ou mettez le pilote à jour.',
        'Téléchargez fsr4vk dans Graphismes. Fichiers absents ou modifiés : {}',
        'Réinstallez le package Windows. Fichier absent : {}',
        'Prérequis GPU/pilote manquant : {}', 'Chargement de la bibliothèque AMD impossible : {}',
        'AMD FSR 4.1.1 indisponible pour ce GPU/pilote : {}',
        'Fournisseur désactivé : {}', 'Vérifier à nouveau'),
    'it': ('Disponibile per questa GPU e driver.', 'Verifica di GPU e driver…',
        'Verifica non riuscita. Riprova o aggiorna il driver.',
        'Scarica fsr4vk in Grafica. File mancanti o modificati: {}',
        'Reinstalla il pacchetto Windows. File mancante: {}',
        'Requisito GPU/driver mancante: {}', 'Impossibile caricare la libreria AMD: {}',
        'AMD FSR 4.1.1 non disponibile per questa GPU/driver: {}',
        'Provider disattivato: {}', 'Verifica di nuovo'),
    'pl': ('Dostępne dla tej karty GPU i sterownika.', 'Sprawdzanie GPU i sterownika…',
        'Nie udało się sprawdzić obsługi. Ponów próbę lub zaktualizuj sterownik.',
        'Pobierz fsr4vk w Grafice. Brakujące lub zmienione pliki: {}',
        'Zainstaluj ponownie pakiet Windows. Brak pliku: {}',
        'Niespełnione wymaganie GPU/sterownika: {}', 'Nie można załadować biblioteki AMD: {}',
        'AMD FSR 4.1.1 niedostępne dla tej karty GPU/sterownika: {}',
        'Dostawca wyłączony: {}', 'Sprawdź ponownie'),
    'tr': ('Bu GPU ve sürücü için kullanılabilir.', 'GPU ve sürücü desteği denetleniyor…',
        'Destek denetlenemedi. Tekrar deneyin veya sürücüyü güncelleyin.',
        'Grafik bölümünden fsr4vk indirin. Eksik veya değiştirilmiş dosyalar: {}',
        'Windows paketini yeniden kurun. Eksik dosya: {}',
        'Eksik GPU/sürücü gereksinimi: {}', 'AMD çalışma zamanı yüklenemedi: {}',
        'AMD FSR 4.1.1 bu GPU/sürücü için kullanılamıyor: {}',
        'Sağlayıcı devre dışı: {}', 'Tekrar denetle'),
    'ar': ('متاح لهذه البطاقة وبرنامج التشغيل.', 'جارٍ فحص البطاقة وبرنامج التشغيل…',
        'تعذر فحص الدعم. أعد الفحص أو حدّث برنامج التشغيل.',
        'نزّل fsr4vk من إعدادات الرسومات. الملفات المفقودة أو المعدلة: {}',
        'أعد تثبيت حزمة Windows. الملف المفقود: {}',
        'متطلب مفقود للبطاقة أو برنامج التشغيل: {}', 'تعذر تحميل مكتبة AMD: {}',
        'AMD FSR 4.1.1 غير متاح لهذه البطاقة وبرنامج التشغيل: {}',
        'المزوّد معطّل: {}', 'إعادة الفحص'),
    'zh': ('适用于此 GPU 和驱动程序。', '正在检查 GPU 和驱动支持…',
        '支持检查失败。请重新检查或更新驱动。',
        '请在图形设置中下载 fsr4vk。缺失或已更改的文件：{}',
        '请重新安装 Windows 软件包。缺失文件：{}',
        'GPU/驱动缺少必要功能：{}', '无法加载 AMD 运行库：{}',
        '此 GPU/驱动无法使用 AMD FSR 4.1.1：{}', '提供程序已禁用：{}', '重新检查'),
    'ja': ('この GPU とドライバーで利用可能です。', 'GPU とドライバーの対応を確認中…',
        '対応を確認できませんでした。再確認するかドライバーを更新してください。',
        'グラフィック設定から fsr4vk をダウンロードしてください。不足または変更されたファイル：{}',
        'Windows パッケージを再インストールしてください。不足ファイル：{}',
        'GPU/ドライバーの必要機能がありません：{}', 'AMD ランタイムを読み込めませんでした：{}',
        'この GPU/ドライバーでは AMD FSR 4.1.1 を利用できません：{}',
        'プロバイダーは無効です：{}', '再確認'),
    'ko': ('이 GPU와 드라이버에서 사용할 수 있습니다.', 'GPU 및 드라이버 지원 확인 중…',
        '지원을 확인하지 못했습니다. 다시 확인하거나 드라이버를 업데이트하세요.',
        '그래픽에서 fsr4vk를 다운로드하세요. 누락되거나 변경된 파일: {}',
        'Windows 패키지를 다시 설치하세요. 누락된 파일: {}',
        'GPU/드라이버 요구 사항 누락: {}', 'AMD 런타임을 불러올 수 없습니다: {}',
        '이 GPU/드라이버에서 AMD FSR 4.1.1을 사용할 수 없습니다: {}',
        '공급자 비활성화: {}', '다시 확인'),
}
TRANSLATIONS = {lang: dict(zip(KEYS, texts, strict=True)) for lang, texts in TEXTS.items()}
