#!/usr/bin/env python3
"""DEVIL NETWORK autoposter v4: новости, даркнет, TG-каналы, статьи из видео, рубрики, квизы, дайджесты, кросспост."""
import html, json, os, random, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from config import NEWS, TG_CHANNELS, VIDEO_HANDLES, PATTERN, RUBRICS
import content

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.environ["CHANNEL_ID"]
INTERVAL_MIN = int(os.environ.get("INTERVAL_MIN", "40"))
MAX_CATCHUP = int(os.environ.get("MAX_CATCHUP", "3"))
VIDEO_AGE_DAYS, TG_AGE_DAYS = 30, 2
STATE_FILE = "posted.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; DevilNetworkBot/3.0)"}
ICON = {"rss": "📰", "kev": "🚨", "gh": "🛠", "tg": "📡", "yt": "🎬"}
MSK = timezone(timedelta(hours=3))
TARGETS = [CHANNEL] + [c.strip() for c in os.environ.get("EXTRA_CHANNELS", "").split(",") if c.strip()]

KEYWORDS = {"zero-day": 4, "0-day": 4, "actively exploited": 4, "ransomware": 3, "breach": 3, "leak": 2, "million": 3,
            "billion": 4, "stolen": 3, "hacked": 3, "exploit": 2, "critical": 3, "telegram": 3, "arrest": 3,
            "seized": 3, "takedown": 3, "darknet": 3, "dark web": 3, "cve-": 2, "scam": 2, "phishing": 2,
            "malware": 2, "backdoor": 2, "crypto": 1, "bitcoin": 1, "даркнет": 3, "утечк": 3, "взлом": 3,
            "хакер": 2, "миллион": 3, "мошенник": 2, "шифровальщик": 3, "арест": 3, "уязвимост": 2, "телеграм": 3}


def now_msk():
    return datetime.now(MSK)


def score_item(item, kind):
    text = (item["title"] + " " + item["text"][:300]).lower()
    s = sum(w for k, w in KEYWORDS.items() if k in text)
    age_h = (datetime.now(timezone.utc) - item["date"]).total_seconds() / 3600
    s += max(0.0, 3 - age_h / 12) + (2 if kind == "kev" else 0) + random.uniform(0, 2)
    return round(s, 2)


def toks(t):
    return set(re.findall(r"[a-zа-яё0-9\-]{4,}", (t or "").lower()))


def item_key(item):
    return item["title"] or item["text"][:200]


def is_dup(item, recent):
    a = toks(item_key(item))
    cves = set(re.findall(r"cve-\d{4}-\d+", (item["title"] + " " + item["text"]).lower()))
    for r in recent[-200:]:
        b = set(r.get("tok", []))
        if a and b and len(a & b) / len(a | b) >= 0.5:
            return True
        if cves and cves & set(r.get("cve", [])):
            return True
    return False


def get(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(t):
    t = re.sub(r"<[^>]+>", " ", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()


def parse_date(s):
    if not s:
        return datetime.now(timezone.utc)
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def find_image(it):
    for el in it.iter():
        u = el.get("url")
        if el.tag in ("thumbnail", "content") and u and re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I):
            return u
        if el.tag == "enclosure" and u and el.get("type", "").startswith("image"):
            return u
    m = re.search(r'<img[^>]+src="([^"]+)"', html.unescape(it.findtext("description") or it.findtext("encoded") or ""))
    return m.group(1) if m else None


def parse_feed(raw):
    root = ET.fromstring(raw)
    for el in root.iter():
        el.tag = el.tag.split("}")[-1]
    out = []
    for it in list(root.iter("item")) + list(root.iter("entry")):
        link = it.findtext("link") or ""
        if not link.strip():
            l = it.find("link")
            link = l.get("href", "") if l is not None else ""
        date = it.findtext("pubDate") or it.findtext("published") or it.findtext("updated")
        body = it.findtext("description") or it.findtext("summary") or it.findtext("content") or ""
        out.append({"id": link.strip(), "title": clean(it.findtext("title")), "text": clean(body),
                    "link": link.strip(), "date": parse_date(date), "image": find_image(it)})
    return out


def parse_kev(raw):
    out = []
    for v in json.loads(raw).get("vulnerabilities", []):
        d = datetime.fromisoformat(v["dateAdded"]).replace(tzinfo=timezone.utc)
        out.append({"id": v["cveID"],
                    "title": f'{v["cveID"]}: {v["vendorProject"]} {v["product"]} — {v["vulnerabilityName"]}',
                    "text": v.get("shortDescription", ""),
                    "link": f'https://nvd.nist.gov/vuln/detail/{v["cveID"]}', "date": d, "image": None})
    return out


def parse_tg(raw, ch):
    page = raw.decode("utf-8", "ignore")
    out = []
    for blk in re.split(r'<div class="tgme_widget_message_wrap', page)[1:]:
        m = re.search(r'data-post="([^"]+)"', blk)
        t = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', blk, re.S)
        d = re.search(r'<time[^>]+datetime="([^"]+)"', blk)
        if not (m and t and d):
            continue
        text = clean(re.sub(r"<br\s*/?>", " ", t.group(1)))
        if len(text) < 80:
            continue
        out.append({"id": "tg:" + m.group(1), "title": "", "text": text,
                    "link": "https://t.me/" + m.group(1), "date": parse_date(d.group(1)), "image": None})
    return out


def resolve_channel(handle, cache):
    if handle in cache:
        return cache[handle]
    page = get(f"https://www.youtube.com/@{handle}").decode("utf-8", "ignore")
    m = re.search(r'"channelId":"(UC[\w-]{22})"', page) or re.search(r"channel_id=(UC[\w-]{22})", page)
    if not m:
        raise RuntimeError("channel id not found")
    cache[handle] = m.group(1)
    return cache[handle]


def is_ru(t):
    cyr = len(re.findall(r"[а-яё]", t, re.I))
    return cyr > 0.3 * max(1, len(re.findall(r"\w", t)))


def translate(text):
    if not text or is_ru(text):
        return text
    try:
        q = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "ru", "dt": "t", "q": text})
        data = json.loads(get("https://translate.googleapis.com/translate_a/single?" + q))
        return "".join(p[0] for p in data[0] if p[0])
    except Exception as e:
        print("translate fail:", e, file=sys.stderr)
        return text


def llm(system, user, max_tokens=1500):
    """OpenAI-совместимый API. По умолчанию — бесплатные GitHub Models (GITHUB_TOKEN)."""
    key = os.environ.get("LLM_API_KEY") or os.environ.get("GITHUB_TOKEN")
    if not key:
        return None
    url = os.environ.get("LLM_URL", "https://models.github.ai/inference/chat/completions")
    model = os.environ.get("LLM_MODEL", "openai/gpt-4.1-mini")
    body = json.dumps({"model": model, "max_tokens": max_tokens, "temperature": 0.5,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    try:
        r = json.loads(get(url, body, {"Authorization": "Bearer " + key, "Content-Type": "application/json"}, 90))
        return r["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("llm fail:", e, file=sys.stderr)
        return None


def transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        tr = YouTubeTranscriptApi().fetch(video_id, languages=["ru", "en"])
        return " ".join(s.text for s in tr)[:14000]
    except Exception as e:
        print("transcript fail:", e, file=sys.stderr)
        return None


def trim(t, n):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def strip_md(t):
    return re.sub(r"\*\*|`|^#+\s*", "", t, flags=re.M).strip()


def split_title(t):
    t = strip_md(t)
    head, _, body = t.partition("\n")
    return trim(head.strip(), 120), body.strip()


SYS_EDITOR = ("Ты редактор русскоязычного Telegram-канала про IT, кибербезопасность и хакеров. "
              "Пиши живо, по делу, без воды и без выдумок: только факты из переданного текста. "
              "Не добавляй ссылок и рекламы. Рассказывай о событиях, расследованиях и арестах, но никогда не давай инструкций, как совершать преступления, создавать нелегальные площадки или красть средства. Формат ответа: первая строка — цепкий заголовок (до 90 символов), "
              "дальше пустая строка и текст.")


def build(item, kind, name, tags):
    """Возвращает (текст_html, короткий_заголовок)."""
    link = html.escape(item["link"])
    tail = f"\n\n{tags} #DEVILNETWORK"
    if kind == "yt":
        title, body = item["title"], ""
        m = re.search(r"v=([\w-]{11})", item["link"])
        tr = transcript(m.group(1)) if m else None
        if tr:
            art = llm(SYS_EDITOR + " Сейчас пиши мини-статью по расшифровке видео: 4-6 коротких абзацев или пунктов, "
                      "главное, ключевые выводы и чем это полезно читателю, до 2500 символов.",
                      f"Название видео: {item['title']}\nКанал: {name}\n\nРасшифровка:\n{tr}", 1800)
            if art:
                title, body = split_title(art)
        title = translate(title)
        head = f'{ICON[kind]} <b>{html.escape(title)}</b>'
        if body:
            return (f'{head}\n\n{html.escape(trim(body, 3200))}\n\n▶️ <a href="{link}">Смотреть видео ({html.escape(name)})</a>{tail}', title)
        return (f'{head}\n\nНовое видео с канала {html.escape(name)}. Смотрим 👇\n\n▶️ <a href="{link}">Смотреть</a>{tail}', title)
    if kind == "tg":
        res = llm(SYS_EDITOR + " Перепиши пост своими словами в короткую заметку 300-700 символов.",
                  f"Источник: Telegram-канал @{name}\n\n{trim(item['text'], 3000)}", 900)
        if res:
            title, body = split_title(res)
        else:
            title, body = "", trim(item["text"], 600)
        head = f'{ICON[kind]} <b>{html.escape(title)}</b>\n\n' if title else f'{ICON[kind]} '
        return (f'{head}{html.escape(trim(body, 1500))}\n\n🔗 <a href="{link}">По материалам @{html.escape(name)}</a>{tail}',
                title or trim(body, 90))
    title = translate(item["title"])
    if kind == "gh":
        title = f"{name}: новая версия {item['title']}"
    text = translate(trim(item["text"], 500))
    flag = "🔥 <b>СРОЧНО</b>\n" if item.get("breaking") else ""
    parts = [f'{flag}{ICON[kind]} <b>{html.escape(title)}</b>']
    if text:
        parts.append(html.escape(trim(text, 420)))
    parts.append(f'🔗 <a href="{link}">Источник: {html.escape(name)}</a>')
    return "\n\n".join(parts) + tail, title


# ---------------- Telegram / VK ----------------
def tg(method, **params):
    params = {k: v for k, v in params.items() if v is not None}
    return get(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", urllib.parse.urlencode(params).encode())


def keyboard():
    rows = []
    if CHANNEL.startswith("@"):
        share = "https://t.me/share/url?" + urllib.parse.urlencode(
            {"url": f"https://t.me/{CHANNEL[1:]}", "text": "🔥 Канал про хакеров, даркнет, взломы и кибербезопасность"},
            quote_via=urllib.parse.quote)
        rows.append({"text": "📤 Поделиться каналом", "url": share})
    sug = os.environ.get("SUGGEST_URL")
    if sug:
        rows.append({"text": "💡 Предложить тему", "url": sug})
    return json.dumps({"inline_keyboard": [rows]}) if rows else None


def is_night():
    h = now_msk().hour
    return h >= 23 or h < 8


def send(item, kind, msg):
    msg = trim(msg, 4090) if len(msg) > 4090 else msg
    silent = "true" if is_night() else None   # ночью — без звука
    for chat in TARGETS:
        try:
            if item and item.get("image") and kind == "rss" and len(msg) <= 1024:
                try:
                    tg("sendPhoto", chat_id=chat, photo=item["image"], caption=msg, parse_mode="HTML",
                       reply_markup=keyboard(), disable_notification=silent)
                    continue
                except Exception as e:
                    print("photo fail, text instead:", e, file=sys.stderr)
            tg("sendMessage", chat_id=chat, text=msg, parse_mode="HTML", reply_markup=keyboard(),
               disable_notification=silent)
        except Exception as e:
            if chat == CHANNEL:
                raise
            print(f"mirror {chat} fail:", e, file=sys.stderr)
    vk_post(msg, item["link"] if item else None)


def send_poll(q, options, correct, expl):
    for chat in TARGETS:
        try:
            tg("sendPoll", chat_id=chat, question=q[:290],
               options=json.dumps([{"text": o[:95]} for o in options], ensure_ascii=False),
               type="quiz", correct_option_id=correct, explanation=expl[:195], is_anonymous="true",
               disable_notification="true" if is_night() else None)
        except Exception as e:
            if chat == CHANNEL:
                raise
            print(f"mirror poll {chat} fail:", e, file=sys.stderr)


def vk_post(msg, link):
    tok, gid = os.environ.get("VK_TOKEN"), os.environ.get("VK_GROUP_ID")
    if not (tok and gid):
        return
    text = html.unescape(re.sub(r"<[^>]+>", "", msg))
    data = {"owner_id": "-" + gid.lstrip("-"), "from_group": 1, "message": text[:3900],
            "access_token": tok, "v": "5.199"}
    if link:
        data["attachments"] = link
    try:
        get("https://api.vk.com/method/wall.post", urllib.parse.urlencode(data).encode())
    except Exception as e:
        print("vk fail:", e, file=sys.stderr)


def members():
    try:
        return json.loads(tg("getChatMemberCount", chat_id=CHANNEL))["result"]
    except Exception:
        return None


def alert_admin(text):
    admin = os.environ.get("ADMIN_CHAT_ID")
    if admin:
        try:
            tg("sendMessage", chat_id=admin, text=text)
        except Exception:
            pass


# ---------------- Состояние ----------------
def load_state():
    try:
        s = json.load(open(STATE_FILE))
    except Exception:
        s = {}
    if isinstance(s, list):
        s = {"seen": s}
    for k, v in (("seen", []), ("last_post", None), ("n", 0), ("yt_ids", {}), ("recent", []), ("rubrics", {})):
        s.setdefault(k, v)
    return s


def record(state, item, kind, tags, title):
    state["recent"].append({"t": datetime.now(timezone.utc).isoformat(), "title": title, "link": item["link"],
                            "score": item.get("score", 0), "tags": tags, "kind": kind,
                            "tok": sorted(toks(item_key(item)))[:40],
                            "cve": re.findall(r"cve-\d{4}-\d+", (item["title"] + " " + item["text"]).lower())})
    cut = datetime.now(timezone.utc) - timedelta(days=8)
    state["recent"] = [r for r in state["recent"] if datetime.fromisoformat(r["t"]) >= cut][-600:]


# ---------------- Сбор ----------------
def collect(state, seen):
    now = datetime.now(timezone.utc)

    def fresh_of(items, age, limit):
        f = [i for i in items if i["id"] and i["id"] not in seen and i["date"] >= now - timedelta(days=age)]
        f.sort(key=lambda i: i["date"], reverse=True)
        return f[:limit]

    def job_news(src):
        name, url, kind, tags, age = src
        raw = get(url)
        items = parse_kev(raw) if kind == "kev" else parse_feed(raw)
        return [(i, kind, name, tags) for i in fresh_of(items, age, 3 if kind == "kev" else 2)]

    def job_tg(src):
        ch, tags = src
        last = None
        for base in ("https://t.me/s/", "https://telegram.me/s/"):
            try:
                items = parse_tg(get(base + ch), ch)
                return [(i, "tg", ch, tags) for i in fresh_of(items, TG_AGE_DAYS, 2)]
            except Exception as e:
                last = e
        raise last

    def job_vid(h):
        cid = resolve_channel(h, state["yt_ids"])
        items = parse_feed(get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
        return [(i, "yt", h, "#видео #хакинг #YouTube") for i in fresh_of(items, VIDEO_AGE_DAYS, 2)]

    pools = {"news": [], "tg": [], "video": []}
    jobs = [(job_news, s, "news") for s in NEWS] + [(job_tg, s, "tg") for s in TG_CHANNELS] + \
           [(job_vid, h, "video") for h in VIDEO_HANDLES]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [(ex.submit(f, a), pool, a) for f, a, pool in jobs]
        for fut, pool, a in futs:
            try:
                pools[pool] += fut.result()
            except Exception as e:
                print(f"skip {pool} {a if isinstance(a, str) else a[0]}: {e}", file=sys.stderr)
    for pool in ("news", "tg"):
        for it, kind, name, tags in pools[pool]:
            it["score"] = score_item(it, kind)
            age_h = (now - it["date"]).total_seconds() / 3600
            it["breaking"] = kind in ("rss", "kev") and it["score"] >= 10 and age_h <= 4
        pools[pool].sort(key=lambda x: x[0]["score"], reverse=True)   # важное — первым
    random.shuffle(pools["video"])
    return pools


# ---------------- Рубрики ----------------
def lines_digest(rows):
    out = []
    for i, r in enumerate(rows, 1):
        out.append(f'{i}. <a href="{html.escape(r["link"])}">{html.escape(trim(r["title"], 110))}</a>')
    return "\n".join(out)


def top_recent(state, hours, n, tagfilter=None):
    cut = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = [r for r in state["recent"] if r["kind"] in ("rss", "kev", "tg") and datetime.fromisoformat(r["t"]) >= cut
            and (not tagfilter or any(t in r["tags"] for t in tagfilter))]
    rows.sort(key=lambda r: r["score"], reverse=True)
    seen_l, out = set(), []
    for r in rows:
        if r["link"] not in seen_l:
            seen_l.add(r["link"]); out.append(r)
    return out[:n]


def members_line():
    n = members()
    return f"\n\n👥 Нас уже {n:,}".replace(",", " ") + " — перешли канал другу, пусть тоже будет в курсе 🔥" if n else ""


def run_rubric(key, state):
    """True если что-то опубликовано."""
    day = now_msk().toordinal()
    tail = " #DEVILNETWORK"
    if key == "tip":
        t, x = content.TIPS[day % len(content.TIPS)]
        send(None, "rss", f"🛡 <b>Совет дня: {html.escape(t)}</b>\n\n{html.escape(x)}\n\n#совет #защита #безопасность{tail}")
    elif key == "term":
        t, x = content.TERMS[day % len(content.TERMS)]
        send(None, "rss", f"📖 <b>Словарь хакера: {html.escape(t)}</b>\n\n{html.escape(x)}\n\n#словарь #основы{tail}")
    elif key == "tool":
        t, x = content.TOOLS[now_msk().isocalendar()[1] % len(content.TOOLS)]
        send(None, "rss", f"🛠 <b>Инструмент недели: {html.escape(t)}</b>\n\n{html.escape(x)}\n\n"
                          f"⚠️ Используй только на своих системах или с письменного разрешения владельца.\n\n#инструменты #pentest{tail}")
    elif key == "quiz":
        q, opts, c, e = content.QUIZ[day % len(content.QUIZ)]
        send_poll("🧠 Квиз дня: " + q, opts, c, e)
    elif key == "top_day":
        rows = top_recent(state, 24, 5)
        if len(rows) < 3:
            return False
        send(None, "rss", f"🏆 <b>Топ-5 событий за сутки</b>\n\n{lines_digest(rows)}{members_line()}\n\n#итоги{tail}")
    elif key == "top_week":
        rows = top_recent(state, 24 * 7, 7)
        if len(rows) < 3:
            return False
        send(None, "rss", f"📊 <b>Итоги недели: главное за 7 дней</b>\n\n{lines_digest(rows)}{members_line()}\n\n#итоги{tail}")
    elif key == "thefts":
        rows = top_recent(state, 24 * 7, 5, ("#крипта", "#DeFi", "#кражи", "#расследование"))
        if len(rows) < 2:
            return False
        send(None, "rss", f"💸 <b>Кражи и расследования недели</b>\n\n{lines_digest(rows)}\n\n"
                          f"Как не стать жертвой — смотри рубрику «Совет дня» 🛡\n\n#крипта #расследование{tail}")
    else:
        print("unknown rubric", key)
        return False
    return True


def due_rubric(state):
    m = now_msk()
    today = m.date().isoformat()
    for key, days, hour in RUBRICS:
        if (days is None or m.weekday() in days) and hour <= m.hour < hour + 6 and state["rubrics"].get(key) != today:
            return key, today
    return None, None


# ---------------- Главный цикл ----------------
def main():
    state = load_state()
    seen = set(state["seen"])
    now = datetime.now(timezone.utc)
    forced = os.environ.get("RUBRIC", "").strip()
    if forced:
        run_rubric(forced, state)
        return
    key, today = due_rubric(state)
    if key:
        try:
            run_rubric(key, state)
        except Exception as e:
            print("rubric fail:", key, e, file=sys.stderr)
        state["rubrics"][key] = today   # помечаем в любом случае, чтобы не зациклиться
        time.sleep(3)
    if state["last_post"] is None or os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        due = 1
    else:
        mins = (now - datetime.fromisoformat(state["last_post"])).total_seconds() / 60
        due = min(MAX_CATCHUP, int(mins // INTERVAL_MIN))
    posted = 0
    if due > 0:
        pools = collect(state, seen)
        while posted < due and any(pools.values()):
            want = PATTERN[state["n"] % len(PATTERN)]
            order = [want] + [k for k in ("news", "tg", "video") if k != want]
            pool = next(k for k in order if pools[k])
            item, kind, name, tags = pools[pool].pop(0)
            if kind != "yt" and is_dup(item, state["recent"]):
                seen.add(item["id"]); continue
            try:
                msg, title = build(item, kind, name, tags)
                send(item, kind, msg)
            except Exception as e:
                print("send fail:", e, file=sys.stderr); continue
            seen.add(item["id"]); posted += 1; state["n"] += 1
            record(state, item, kind, tags, title)
            state["last_post"] = datetime.now(timezone.utc).isoformat()
            time.sleep(3)
        if posted == 0:
            alert_admin("⚠️ DEVIL NETWORK: пост должен был выйти, но не вышел. Проверь Actions → логи.")
    state["seen"] = sorted(seen)[-6000:]
    json.dump(state, open(STATE_FILE, "w"), ensure_ascii=False, indent=0)
    print(f"posted {posted}/{due}; rubric={key}")


if __name__ == "__main__":
    main()
