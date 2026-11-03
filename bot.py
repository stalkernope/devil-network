import os
import sys
import json
import re
import html
import random
import time
from datetime import datetime, timedelta, timezone

import requests
import feedparser
from deep_translator import GoogleTranslator

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.environ["CHANNEL_ID"]
GH_TOKEN = os.environ.get("GITHUB_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "posted.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; DevilNetworkBot/1.0)"}

FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://www.securityweek.com/feed/",
]
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
TOOL_TOPICS = ["pentest", "security-tools", "ctf", "osint", "hacking",
               "reverse-engineering", "malware-analysis", "red-team", "bug-bounty"]

TAG_RULES = {
    "ransomware": "#ransomware", "phishing": "#фишинг", "zero-day": "#0day",
    "vulnerability": "#уязвимости", "malware": "#malware", "breach": "#утечка",
    "leak": "#утечка", "android": "#android", "windows": "#windows",
    "linux": "#linux", "ddos": "#ddos", "botnet": "#botnet", "apple": "#apple",
    "chrome": "#chrome", "ai ": "#AI",
}

QUIZ = [
    ("Какой порт по умолчанию использует SSH?", ["21", "22", "23", "80"], 1,
     "SSH работает на TCP-порту 22. FTP — 21, Telnet — 23."),
    ("Что означает XSS?", ["Cross-Site Scripting", "Extra Secure Socket", "XML Source Script", "Cross-Server Sync"], 0,
     "XSS — внедрение вредоносного JavaScript на страницу, которую видят другие пользователи."),
    ("Какой инструмент чаще всего используют для сканирования портов?", ["Nmap", "Wireshark", "Hashcat", "Burp Suite"], 0,
     "Nmap — классика сетевого сканирования. Wireshark — анализ трафика, Hashcat — подбор хешей."),
    ("Что такое фишинг?", ["Подбор паролей перебором", "Обман пользователя, чтобы выманить данные",
                           "Перехват трафика в Wi-Fi", "Шифрование файлов ради выкупа"], 1,
     "Фишинг — социальная инженерия: поддельные письма и сайты, чтобы получить логины, пароли, карты."),
    ("Как называется вредонос, который шифрует файлы и требует выкуп?",
     ["Spyware", "Adware", "Ransomware", "Rootkit"], 2,
     "Ransomware — программа-вымогатель. Лучшая защита: офлайн-бэкапы и обновления."),
    ("Что делает хеш-функция SHA-256?", ["Шифрует данные ключом", "Создаёт отпечаток данных фиксированной длины",
                                         "Сжимает файлы", "Генерирует пары ключей"], 1,
     "Хеш всегда 256 бит, и обратно «расшифровать» его нельзя."),
    ("SQL-инъекция — это уязвимость в...", ["Веб-приложениях, плохо обрабатывающих ввод в запросах к БД",
                                            "Только в прошивках роутеров", "Протоколе WPA2", "Загрузчике ОС"], 0,
     "Защита: параметризованные запросы и валидация ввода."),
    ("Что такое 2FA?", ["Двухфакторная аутентификация", "Двойное шифрование", "Два антивируса", "Второй пароль от Wi-Fi"], 0,
     "Пароль + второй фактор (код, ключ, приложение). Взломать аккаунт становится намного сложнее."),
    ("CTF в мире ИБ — это...", ["Протокол передачи файлов", "Соревнование по информационной безопасности",
                                "Тип вируса", "Сертификат"], 1,
     "Capture The Flag: решаешь задачи по взлому и защите в легальной среде и ищешь «флаги»."),
    ("Какой порт по умолчанию у HTTPS?", ["80", "443", "8080", "22"], 1,
     "HTTPS — 443, обычный HTTP — 80."),
    ("Что такое 0-day уязвимость?", ["Уязвимость, для которой ещё нет патча", "Вирус, удаляющий себя через день",
                                     "Первый день работы пентестера", "Пустой пароль"], 0,
     "У разработчика было «0 дней» на исправление: атаки идут раньше, чем выходит патч."),
    ("Что такое атака Man-in-the-Middle?", ["Перебор паролей по словарю", "Перегрузка сервиса запросами",
                                            "Атакующий встаёт между сторонами и перехватывает обмен", "Подмена файла на диске"], 2,
     "MitM — перехват и возможное изменение трафика между двумя участниками. HTTPS сильно защищает от этого."),
    ("Что такое DDoS?", ["Утечка базы паролей", "Распределённая атака, перегружающая сервис запросами",
                         "Взлом через USB", "Подмена DNS"], 1,
     "Много устройств (часто ботнет) одновременно заваливают сервис запросами."),
    ("Kali Linux — это...", ["Антивирус", "Менеджер паролей", "Дистрибутив Linux для тестирования на проникновение", "Облачный сервис"], 2,
     "Kali — сборка с набором инструментов для пентеста и обучения."),
    ("Как правильно хранить пароли в базе данных?", ["В открытом виде", "Как хеш с солью (bcrypt/argon2)",
                                                    "В base64", "Шифруя одним общим ключом из кода"], 1,
     "Медленные хеши с солью (bcrypt, argon2) сильно усложняют подбор при утечке базы."),
]


# ---------- служебное ----------

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ids": []}


def save_state(state):
    state["ids"] = state["ids"][-1500:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def esc(s):
    return html.escape(s or "", quote=True)


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"The post .*? appeared first on .*", "", text, flags=re.S)
    return re.sub(r"\s+", " ", text).strip()


def shorten(text, n):
    if len(text) <= n:
        return text
    cut = text[:n]
    dot = cut.rfind(". ")
    if dot > n * 0.5:
        return cut[:dot + 1]
    return cut[:cut.rfind(" ")] + "…"


def translate(text):
    if not text:
        return text
    try:
        return GoogleTranslator(source="auto", target="ru").translate(text) or text
    except Exception as e:
        print("translate error:", e)
        return text


def tags_for(text):
    low = text.lower()
    tags = ["#кибербезопасность", "#infosec"]
    for key, tag in TAG_RULES.items():
        if key in low and tag not in tags:
            tags.append(tag)
    return " ".join(tags[:6])


def og_image(url):
    try:
        r = requests.get(url, headers=UA, timeout=10)
        head = r.text[:200000]
        m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', head)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', head))
        return html.unescape(m.group(1)) if m else None
    except Exception:
        return None


def tg(method, **data):
    r = requests.post(f"{API}/{method}", json=data, timeout=30)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(f"Telegram {method}: {j.get('description')}")
    return j


def send_post(text, image=None):
    if image and len(text) <= 1000:
        try:
            tg("sendPhoto", chat_id=CHANNEL, photo=image, caption=text, parse_mode="HTML")
            return
        except Exception as e:
            print("photo failed, sending text:", e)
    tg("sendMessage", chat_id=CHANNEL, text=text, parse_mode="HTML",
       link_preview_options={"is_disabled": True})


# ---------- режимы ----------

def mode_news(state):
    items = []
    for url in FEEDS:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            feed = feedparser.parse(r.content)
        except Exception as e:
            print("feed error:", url, e)
            continue
        for e in feed.entries[:10]:
            ts = e.get("published_parsed") or e.get("updated_parsed")
            items.append((time.mktime(ts) if ts else 0, e))
    items.sort(key=lambda x: x[0], reverse=True)

    for _, e in items:
        link = e.get("link")
        if not link or link in state["ids"]:
            continue
        title_en = clean(e.get("title", ""))
        summary_en = shorten(clean(e.get("summary", "")), 380)
        title = translate(title_en)
        summary = translate(summary_en) if summary_en else ""
        image = None
        media = e.get("media_content") or e.get("media_thumbnail")
        if media:
            image = media[0].get("url")
        if not image:
            image = og_image(link)
        text = f"🔥 <b>{esc(title)}</b>\n\n"
        if summary:
            text += f"{esc(summary)}\n\n"
        text += f'🔗 <a href="{esc(link)}">Источник</a>\n\n{tags_for(title_en + " " + summary_en)}'
        send_post(text, image)
        state["ids"].append(link)
        return True
    print("новых новостей нет")
    return False


def mode_cve(state):
    r = requests.get(KEV_URL, headers=UA, timeout=60)
    vulns = r.json()["vulnerabilities"]
    vulns.sort(key=lambda v: v["dateAdded"], reverse=True)
    for v in vulns:
        uid = "cve:" + v["cveID"]
        if uid in state["ids"]:
            continue
        name = translate(v.get("vulnerabilityName", ""))
        desc = translate(shorten(v.get("shortDescription", ""), 500))
        action = translate(shorten(v.get("requiredAction", ""), 300))
        cve = v["cveID"]
        text = (
            f"🕳 <b>Уязвимость дня: {esc(cve)}</b>\n\n"
            f"<b>Продукт:</b> {esc(v.get('vendorProject', ''))} {esc(v.get('product', ''))}\n"
            f"<b>Суть:</b> {esc(name)}\n\n"
            f"{esc(desc)}\n\n"
            f"⚠️ Уязвимость уже используется в реальных атаках (список CISA KEV).\n"
            f"🛡 <b>Что делать:</b> {esc(action)}\n\n"
            f'🔗 <a href="https://nvd.nist.gov/vuln/detail/{esc(cve)}">Подробнее в NVD</a>\n\n'
            f"#CVE #уязвимости #кибербезопасность #infosec"
        )
        send_post(text)
        state["ids"].append(uid)
        return True
    print("новых CVE нет")
    return False


def mode_tool(state):
    headers = dict(UA)
    headers["Accept"] = "application/vnd.github+json"
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    since = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    topics = TOOL_TOPICS[:]
    random.shuffle(topics)
    for topic in topics:
        r = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": f"topic:{topic} stars:>300 pushed:>{since}", "sort": "stars", "per_page": 30},
            headers=headers, timeout=30,
        )
        for repo in r.json().get("items", []):
            uid = "repo:" + repo["full_name"]
            if uid in state["ids"] or not repo.get("description"):
                continue
            desc = translate(shorten(clean(repo["description"]), 300))
            stars = f"{repo['stargazers_count']:,}".replace(",", " ")
            text = (
                f"🛠 <b>Инструмент недели: {esc(repo['name'])}</b>\n\n"
                f"{esc(desc)}\n\n"
                f"⭐ {stars}"
                + (f" · 💻 {esc(repo['language'])}" if repo.get("language") else "")
                + f'\n🔗 <a href="{esc(repo["html_url"])}">GitHub</a>\n\n'
                f"⚖️ Используй только на своих системах или с разрешения владельца.\n\n"
                f"#инструменты #pentest #infosec #github"
            )
            send_post(text)
            state["ids"].append(uid)
            return True
    print("инструментов не нашлось")
    return False


def mode_quiz(state):
    unused = [i for i in range(len(QUIZ)) if f"quiz:{i}" not in state["ids"]]
    if not unused:
        state["ids"] = [x for x in state["ids"] if not x.startswith("quiz:")]
        unused = list(range(len(QUIZ)))
    i = random.choice(unused)
    q, options, correct, expl = QUIZ[i]
    pairs = list(enumerate(options))
    random.shuffle(pairs)
    new_options = [o for _, o in pairs]
    new_correct = [idx for idx, (orig, _) in enumerate(pairs) if orig == correct][0]
    tg("sendPoll", chat_id=CHANNEL, question="🧠 " + q, options=new_options, type="quiz",
       correct_option_id=new_correct, explanation=expl[:200], is_anonymous=True)
    state["ids"].append(f"quiz:{i}")
    return True


MODES = {"news": mode_news, "cve": mode_cve, "tool": mode_tool, "quiz": mode_quiz}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "news"
    if mode not in MODES:
        sys.exit(f"unknown mode: {mode}")
    state = load_state()
    MODES[mode](state)
    save_state(state)
