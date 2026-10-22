# SPDX-License-Identifier: GPL-2.0-or-later
"""The 1.9.5 texts (the shadNet server that turns the port away: Online play's note, Help's topic),
in every language besides English, with the launcher's existing words for the pages and buttons
they name. Keyed by the English text like bbport_lang; merged into its tables on import."""
import bbport_lang

KEYS = [
    "shadPS4's public shadNet server doesn't accept this port's version at the moment, so online play there "
    "fails. Play with The Hunter's Dream, or a shadNet server that accepts the port under Use my own servers.",
    'The shadNet server turned this port away',
    "shadPS4's public shadNet server checks which program connects and doesn't accept this port's version at the "
    'moment. The game then plays offline. Your account and your settings are fine.',
    "Online play: Play with The Hunter's Dream, then Sign in with Discord.",
    'Or a shadNet server that accepts the port: Use my own servers, with the addresses from the person who runs '
    'it.',
    'Open Online play',
    'Online play was off this time. Its log names the cause:',
]

TEXTS = {
    'ru': [
        "Публичный сервер shadNet от shadPS4 сейчас не принимает версию этого порта, поэтому онлайн-игра на нём не "
        "работает. Выберите «Играть через» The Hunter's Dream или сервер shadNet, который принимает порт, в "
        "«Использовать свои серверы».",
        'Сервер shadNet не пустил этот порт',
        'Публичный сервер shadNet от shadPS4 проверяет, какая программа подключается, и сейчас не принимает версию '
        'этого порта. Тогда игра идёт офлайн. С вашей учётной записью и настройками всё в порядке.',
        "Онлайн-игра: «Играть через» The Hunter's Dream, затем «Войти через Discord».",
        'Или сервер shadNet, который принимает порт: «Использовать свои серверы» с адресами от его владельца.',
        'Открыть «Онлайн-игру»',
        'В этот раз онлайн-игра была выключена. Журнал называет причину:',
    ],
    'ar': [
        "خادم shadNet العام من shadPS4 لا يقبل إصدار هذا المنفذ حاليًا، لذا يفشل اللعب عبر الإنترنت عليه. اختر "
        "في «العب باستخدام» The Hunter's Dream، أو خادم shadNet يقبل المنفذ من «استخدام خوادمي الخاصة».",
        'رفض خادم shadNet هذا المنفذ',
        'يتحقق خادم shadNet العام من shadPS4 من البرنامج المتصل، ولا يقبل إصدار هذا المنفذ حاليًا. عندها تعمل اللعبة '
        'دون اتصال. حسابك وإعداداتك سليمة.',
        "اللعب عبر الإنترنت: «العب باستخدام» The Hunter's Dream، ثم «تسجيل الدخول باستخدام Discord».",
        'أو خادم shadNet يقبل المنفذ: «استخدام خوادمي الخاصة» مع العناوين من الشخص الذي يديره.',
        'فتح «اللعب عبر الإنترنت»',
        'كان اللعب عبر الإنترنت متوقفًا هذه المرة. يذكر السجل السبب:',
    ],
    'es': [
        "El servidor público de shadNet de shadPS4 no acepta por ahora la versión de este port, así que el juego en "
        "línea allí falla. En «Jugar con» elige The Hunter's Dream, o un servidor shadNet que acepte el port en "
        "«Usar mis propios servidores».",
        'El servidor shadNet rechazó este port',
        'El servidor público de shadNet de shadPS4 comprueba qué programa se conecta y por ahora no acepta la versión '
        'de este port. El juego funciona entonces sin conexión. Tu cuenta y tus ajustes están bien.',
        "Juego en línea: «Jugar con» The Hunter's Dream y luego «Iniciar sesión con Discord».",
        'O un servidor shadNet que acepte el port: «Usar mis propios servidores», con las direcciones de quien lo '
        'gestiona.',
        'Abrir «Juego en línea»',
        'Esta vez el juego en línea estuvo desactivado. Su registro indica la causa:',
    ],
    'pt': [
        "O servidor público shadNet do shadPS4 não aceita no momento a versão deste port, então o jogo online nele "
        "falha. Em «Jogar com» escolha The Hunter's Dream, ou um servidor shadNet que aceite o port em «Usar meus "
        "próprios servidores».",
        'O servidor shadNet recusou este port',
        'O servidor público shadNet do shadPS4 verifica qual programa se conecta e no momento não aceita a versão '
        'deste port. O jogo então roda offline. Sua conta e suas configurações estão certas.',
        "Jogo online: «Jogar com» The Hunter's Dream e depois «Entrar com o Discord».",
        'Ou um servidor shadNet que aceite o port: «Usar meus próprios servidores», com os endereços de quem o '
        'administra.',
        'Abrir «Jogo online»',
        'Desta vez o jogo online ficou desligado. O registro dele aponta a causa:',
    ],
    'fr': [
        "Le serveur shadNet public de shadPS4 n'accepte pas pour l'instant la version de ce port : le jeu en ligne y "
        "échoue. Dans « Jouer avec », choisissez The Hunter's Dream, ou un serveur shadNet qui accepte le port avec "
        "« Utiliser mes propres serveurs ».",
        'Le serveur shadNet a refusé ce port',
        'Le serveur shadNet public de shadPS4 vérifie quel programme se connecte et n\'accepte pas pour l\'instant la '
        'version de ce port. Le jeu passe alors hors ligne. Votre compte et vos réglages sont corrects.',
        "Jeu en ligne : « Jouer avec » The Hunter's Dream, puis « Se connecter avec Discord ».",
        'Ou un serveur shadNet qui accepte le port : « Utiliser mes propres serveurs », avec les adresses de la '
        'personne qui le gère.',
        'Ouvrir « Jeu en ligne »',
        'Le jeu en ligne était désactivé cette fois. Son journal en donne la cause :',
    ],
    'de': [
        "Der öffentliche shadNet-Server von shadPS4 nimmt die Version dieses Ports derzeit nicht an, online spielen "
        "schlägt dort fehl. Wähle unter „Spielen mit“ The Hunter's Dream oder unter „Eigene Server verwenden“ einen "
        "shadNet-Server, der den Port annimmt.",
        'Der shadNet-Server hat diesen Port abgewiesen',
        'Der öffentliche shadNet-Server von shadPS4 prüft, welches Programm sich verbindet, und nimmt die Version '
        'dieses Ports derzeit nicht an. Das Spiel läuft dann offline. Dein Konto und deine Einstellungen sind in '
        'Ordnung.',
        "Online spielen: „Spielen mit“ The Hunter's Dream, dann „Mit Discord anmelden“.",
        'Oder ein shadNet-Server, der den Port annimmt: „Eigene Server verwenden“ mit den Adressen von dem, der ihn '
        'betreibt.',
        '„Online spielen“ öffnen',
        'Online spielen war diesmal aus. Sein Protokoll nennt den Grund:',
    ],
    'it': [
        "Il server shadNet pubblico di shadPS4 al momento non accetta la versione di questo port, quindi il gioco "
        "online lì non funziona. In «Gioca con» scegli The Hunter's Dream, o un server shadNet che accetti il port "
        "con «Usa i miei server».",
        'Il server shadNet ha rifiutato questo port',
        'Il server shadNet pubblico di shadPS4 controlla quale programma si collega e al momento non accetta la '
        'versione di questo port. Il gioco va allora offline. Il tuo account e le tue impostazioni sono a posto.',
        "Gioco online: «Gioca con» The Hunter's Dream, poi «Accedi con Discord».",
        'Oppure un server shadNet che accetti il port: «Usa i miei server», con gli indirizzi di chi lo gestisce.',
        'Apri «Gioco online»',
        'Questa volta il gioco online era spento. Il suo registro indica la causa:',
    ],
    'pl': [
        "Publiczny serwer shadNet od shadPS4 obecnie nie przyjmuje wersji tego portu, więc gra online na nim nie "
        "działa. W „Graj z” wybierz The Hunter's Dream albo serwer shadNet, który przyjmuje port, w „Używaj "
        "własnych serwerów”.",
        'Serwer shadNet odrzucił ten port',
        'Publiczny serwer shadNet od shadPS4 sprawdza, który program się łączy, i obecnie nie przyjmuje wersji tego '
        'portu. Gra działa wtedy offline. Twoje konto i ustawienia są w porządku.',
        "Gra online: „Graj z” The Hunter's Dream, potem „Zaloguj się przez Discord”.",
        'Albo serwer shadNet, który przyjmuje port: „Używaj własnych serwerów” z adresami od osoby, która go '
        'prowadzi.',
        'Otwórz „Grę online”',
        'Tym razem gra online była wyłączona. Jej dziennik podaje przyczynę:',
    ],
    'tr': [
        "shadPS4'ün herkese açık shadNet sunucusu şu anda bu portun sürümünü kabul etmiyor, bu yüzden orada çevrim "
        "içi oyun başarısız oluyor. \"Oynanacak sunucu\" olarak The Hunter's Dream'i ya da \"Kendi sunucularımı "
        "kullan\" ile portu kabul eden bir shadNet sunucusunu seç.",
        'shadNet sunucusu bu portu geri çevirdi',
        "shadPS4'ün herkese açık shadNet sunucusu hangi programın bağlandığını denetliyor ve şu anda bu portun "
        'sürümünü kabul etmiyor. Oyun o zaman çevrim dışı çalışır. Hesabın ve ayarların sorunsuz.',
        "Çevrim içi oyun: \"Oynanacak sunucu\" The Hunter's Dream, ardından \"Discord ile oturum aç\".",
        'Ya da portu kabul eden bir shadNet sunucusu: işleten kişinin verdiği adreslerle "Kendi sunucularımı kullan".',
        '"Çevrim içi oyun"u aç',
        'Bu sefer çevrim içi oyun kapalıydı. Günlüğü nedenini söylüyor:',
    ],
    'zh': [
        "shadPS4 的公共 shadNet 服务器目前不接受本移植版的版本，因此在其上在线游玩会失败。请在“游玩设备”中选择 "
        "The Hunter's Dream，或在“使用我自己的服务器”中使用接受本移植版的 shadNet 服务器。",
        'shadNet 服务器拒绝了本移植版',
        'shadPS4 的公共 shadNet 服务器会检查连接的程序，目前不接受本移植版的版本。游戏随后以离线方式运行。你的账号和设置都没有问题。',
        "在线游玩：“游玩设备”选 The Hunter's Dream，然后“使用 Discord 登录”。",
        '或使用接受本移植版的 shadNet 服务器：“使用我自己的服务器”，填入服务器管理者提供的地址。',
        '打开“在线游玩”',
        '这次在线游玩处于关闭状态。日志指出了原因：',
    ],
    'ja': [
        "shadPS4 の公開 shadNet サーバーは現在このポートのバージョンを受け付けないため、そこでのオンラインプレイは"
        "失敗します。「接続先」で The Hunter's Dream を選ぶか、「自分のサーバーを使う」でこのポートを受け付ける "
        "shadNet サーバーを使ってください。",
        'shadNet サーバーがこのポートを拒否しました',
        'shadPS4 の公開 shadNet サーバーは接続するプログラムを確認しており、現在このポートのバージョンを受け付けません。'
        'その場合ゲームはオフラインで動きます。アカウントや設定に問題はありません。',
        "オンラインプレイ：「接続先」を The Hunter's Dream にして、「Discord でサインイン」。",
        'またはこのポートを受け付ける shadNet サーバー：「自分のサーバーを使う」で、運営者から聞いたアドレスを入力。',
        '「オンラインプレイ」を開く',
        '今回はオンラインプレイがオフでした。ログに原因があります：',
    ],
    'ko': [
        "shadPS4의 공개 shadNet 서버가 현재 이 포트의 버전을 받지 않아 그 서버에서는 온라인 플레이가 실패합니다. "
        "'함께 플레이'에서 The Hunter's Dream을 고르거나, '내 서버 사용'에서 이 포트를 받는 shadNet 서버를 쓰세요.",
        'shadNet 서버가 이 포트를 거부했습니다',
        'shadPS4의 공개 shadNet 서버는 접속하는 프로그램을 확인하며, 현재 이 포트의 버전을 받지 않습니다. 이때 게임은 '
        '오프라인으로 실행됩니다. 계정과 설정은 문제없습니다.',
        "온라인 플레이: '함께 플레이'를 The Hunter's Dream으로, 그다음 'Discord로 로그인'.",
        "또는 이 포트를 받는 shadNet 서버: '내 서버 사용'에 운영자에게 받은 주소를 입력.",
        "'온라인 플레이' 열기",
        '이번에는 온라인 플레이가 꺼져 있었습니다. 로그에 원인이 있습니다:',
    ],
}

for _language, _texts in TEXTS.items():
    assert len(_texts) == len(KEYS), (_language, len(_texts), len(KEYS))
    bbport_lang.EXTRA_TRANSLATIONS.setdefault(_language, {}).update(zip(KEYS, _texts))
