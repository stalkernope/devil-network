# ====== ВСЕ ИСТОЧНИКИ ТУТ. Добавляй/удаляй строки — остальное не трогай ======
# (название, url, тип, теги, макс. возраст в днях)   тип: rss | kev | gh
NEWS = [
    # --- кибербезопасность, мир
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews", "rss", "#новости #кибербезопасность", 2),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/", "rss", "#новости #взломы", 2),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/", "rss", "#расследования #хакеры", 3),
    ("Dark Reading", "https://www.darkreading.com/rss.xml", "rss", "#кибербезопасность", 2),
    ("SecurityWeek", "https://feeds.feedburner.com/securityweek", "rss", "#кибербезопасность", 2),
    ("Schneier on Security", "https://www.schneier.com/feed/atom/", "rss", "#аналитика", 4),
    ("SANS ISC", "https://isc.sans.edu/rssfeed.xml", "rss", "#угрозы", 3),
    ("Securelist", "https://securelist.com/feed/", "rss", "#вирусы #исследования", 5),
    ("Exploit-DB", "https://www.exploit-db.com/rss.xml", "rss", "#эксплойты #уязвимости", 2),
    # --- даркнет, утечки, ransomware
    ("The Record", "https://therecord.media/feed", "rss", "#даркнет #кибервойна", 2),
    ("Hackread", "https://www.hackread.com/feed/", "rss", "#даркнет #утечки", 2),
    ("Cybernews", "https://cybernews.com/feed/", "rss", "#даркнет #утечки", 2),
    ("DataBreaches.net", "https://databreaches.net/feed/", "rss", "#утечки #даркнет", 2),
    ("Darknet Diaries", "https://feeds.megaphone.fm/darknetdiaries", "rss", "#даркнет #подкаст", 14),
    ("Ransomware.live", "https://www.ransomware.live/rss.xml", "rss", "#ransomware #даркнет", 1),
    # --- мошенничество и фишинг
    ("Malwarebytes Labs", "https://www.malwarebytes.com/blog/feed/index.xml", "rss", "#мошенничество #фишинг", 3),
    ("Bitdefender Hot for Security", "https://www.bitdefender.com/blog/hotforsecurity/rss/", "rss", "#мошенничество", 3),
    ("Kaspersky Daily", "https://www.kaspersky.ru/blog/feed/", "rss", "#мошенничество #безопасность", 3),
    # --- русскоязычные
    ("Хакер", "https://xakep.ru/feed/", "rss", "#хакинг #новости", 2),
    ("Хабр ИБ", "https://habr.com/ru/rss/hubs/infosecurity/all/?fl=ru", "rss", "#ИБ", 2),
    ("SecurityLab", "https://www.securitylab.ru/_services/export/rss/", "rss", "#кибербезопасность", 2),
    ("Anti-Malware", "https://www.anti-malware.ru/rss", "rss", "#кибербезопасность", 3),
    # --- IT вообще
    ("Hacker News 200+", "https://hnrss.org/frontpage?points=200", "rss", "#IT #технологии", 2),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "rss", "#IT #технологии", 2),
    ("TechCrunch", "https://techcrunch.com/feed/", "rss", "#IT #стартапы", 2),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "rss", "#IT #гаджеты", 2),
    ("3DNews", "https://3dnews.ru/news/rss/", "rss", "#IT #новости", 1),
    ("Хабр Новости", "https://habr.com/ru/rss/news/?fl=ru", "rss", "#IT #новости", 1),
    # --- расследования краж в крипте и громкие дела про даркнет
    ("Chainalysis", "https://www.chainalysis.com/blog/feed/", "rss", "#расследование #крипта #даркнет", 10),
    ("TRM Labs", "https://www.trmlabs.com/post/rss.xml", "rss", "#расследование #крипта", 10),
    ("Elliptic", "https://www.elliptic.co/blog/rss.xml", "rss", "#расследование #крипта #даркнет", 10),
    ("Rekt News", "https://rekt.news/rss.xml", "rss", "#взломы #DeFi #крипта", 7),
    ("Immunefi", "https://medium.com/feed/immunefi", "rss", "#взломы #DeFi", 10),
    ("Europol", "https://www.europol.europa.eu/rss.xml", "rss", "#даркнет #аресты #расследование", 14),
    # --- крипта
    ("Cointelegraph", "https://cointelegraph.com/rss", "rss", "#крипта", 2),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "rss", "#крипта", 2),
    ("Decrypt", "https://decrypt.co/feed", "rss", "#крипта #web3", 2),
    # --- уязвимости
    ("CISA KEV", "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", "kev", "#уязвимости #CVE", 7),
    # --- новые версии хакерских инструментов (GitHub)
    ("Nuclei", "https://github.com/projectdiscovery/nuclei/releases.atom", "gh", "#инструменты #pentest", 14),
    ("Hashcat", "https://github.com/hashcat/hashcat/releases.atom", "gh", "#инструменты #пароли", 30),
    ("Aircrack-ng", "https://github.com/aircrack-ng/aircrack-ng/releases.atom", "gh", "#инструменты #wifi", 30),
    ("BloodHound", "https://github.com/BloodHoundAD/BloodHound/releases.atom", "gh", "#инструменты #pentest", 30),
    ("Metasploit", "https://github.com/rapid7/metasploit-framework/tags.atom", "gh", "#инструменты #metasploit", 14),
    ("Nmap", "https://github.com/nmap/nmap/tags.atom", "gh", "#инструменты #nmap", 30),
    ("Wireshark", "https://github.com/wireshark/wireshark/tags.atom", "gh", "#инструменты #сети", 30),
]

# Telegram-каналы (публичные), читаются через веб-превью t.me/s/<имя>
# (имя без @, теги)
TG_CHANNELS = [
    ("mamai11", "#подборка"),
    ("maska_238", "#подборка"),
    ("telegram", "#telegram #обновления"),
    ("durov", "#telegram #Дуров"),
    ("tginfo", "#telegram #новости"),
    ("true_secator", "#кибербезопасность #взломы"),
    ("zachxbt", "#расследование #крипта #кражи"),
]

# YouTube-каналы по @хэндлу (ID находится автоматически). Для статей из видео.
VIDEO_HANDLES = ["NetworkChuck", "_JohnHammond", "LiveOverflow", "davidbombal", "TheCyberMentor",
                 "ippsec", "Seytonic", "hak5", "LoiLiangYang", "STOKfredrik", "Computerphile",
                 "mamai11", "maska_238"]   # последние два — на случай если это YouTube-каналы

# Порядок типов постов по кругу
PATTERN = ["news", "news", "tg", "video"]

# Рубрики по расписанию (время МСК). days: None = каждый день, иначе номера дней недели (0=пн ... 6=вс)
# (ключ, дни, час)
RUBRICS = [
    ("tip",      None, 9),    # 🛡 Совет дня
    ("quiz",     None, 12),   # 🧠 Квиз (опрос)
    ("term",     None, 15),   # 📖 Словарь хакера
    ("top_day",  None, 21),   # 🏆 Топ-5 за день
    ("tool",     [2],  19),   # 🛠 Инструмент недели (ср)
    ("thefts",   [4],  18),   # 💸 Кражи недели (пт)
    ("top_week", [6],  19),   # 📊 Итоги недели (вс)
]
