import os
import json
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

TOKEN = os.environ["BOT_TOKEN"]
FD_KEY = os.environ["FD_API_KEY"]
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
# Бесплатные модели Gemini: если у одной кончился лимит, пробуем следующую
GEMINI_MODELS = [
    m
    for m in [
        os.environ.get("GEMINI_MODEL"),
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
    ]
    if m
]
# Telegram ID Артура (секрет ALLOWED_ID). Пока он пустой, любой, кто напишет /start,
# увидит в ответ свой ID.
ALLOWED_ID = (os.environ.get("ALLOWED_ID") or "").strip()
# Telegram ID тестировщика (секрет TESTER_ID). Это отдельное место, оно не занимает место Артура.
TESTER_ID = (os.environ.get("TESTER_ID") or "").strip()
TZ = ZoneInfo("Asia/Yerevan")  # армянское время
TG = f"https://api.telegram.org/bot{TOKEN}"
MAX_QUESTIONS_PER_RUN = 5
BIRTHDAY = (11, 19)  # (месяц, день)
# Ночью (с 23:00 до 08:00 по времени TZ) напоминания не отправляются
QUIET_START = 23
QUIET_END = 8

# Этапы напоминаний: за сутки, за 4 часа, за 1 час
STAGES = [timedelta(days=1), timedelta(hours=4), timedelta(hours=1)]

LANG_NAMES = {"ru": "русский", "hy": "армянский", "en": "английский"}

TEXTS = {
    "ru": {
        "left_h": "через {n} ч",
        "left_m": "через {n} мин",
        "title": "⚽ Матч {w}!",
        "at": "{c}, {d} в {t}",
        "set": "Язык: русский 🇷🇺",
        "quiet_on": "Спокойная ночка 🌙 С 23:00 до 08:00 я не буду отправлять напоминания.",
        "quiet_off": "Неспокойная ночка 🔔 Напоминания будут приходить и ночью.",
    },
    "hy": {
        "left_h": "{n} ժամից",
        "left_m": "{n} րոպեից",
        "title": "⚽ Խաղը սկսվում է {w}!",
        "at": "{c}, {d}՝ ժամը {t}",
        "set": "Լեզուն՝ հայերեն 🇦🇲",
        "quiet_on": "Հանգիստ գիշեր 🌙 23:00-ից 08:00-ն ես հիշեցումներ չեմ ուղարկի։",
        "quiet_off": "Անհանգիստ գիշեր 🔔 Հիշեցումները կգան նաև գիշերը։",
    },
    "en": {
        "left_h": "in {n} h",
        "left_m": "in {n} min",
        "title": "⚽ Match starts {w}!",
        "at": "{c}, {d} at {t}",
        "set": "Language: English 🇬🇧",
        "quiet_on": "Quiet night 🌙 No reminders between 23:00 and 08:00.",
        "quiet_off": "Noisy night 🔔 Reminders will also come at night.",
    },
}

GREETING_BIRTHDAY = (
    "Привет, Артур, с днём рождения! 🎉🎂\n"
    "Я буду напоминать тебе о матчах Манчестер Юнайтед ⚽🔴 "
    "и отвечать на любые вопросы о клубе!\n\n"
    "Բարև, Արթուր, շնորհավոր ծնունդդ։ 🎉🎂\n"
    "Ես կհիշեցնեմ քեզ Մանչեսթեր Յունայթեդի խաղերի մասին ⚽🔴 "
    "և կպատասխանեմ ակումբի մասին ցանկացած հարցի։\n\n"
    "Hi Artur, happy birthday! 🎉🎂\n"
    "I'll remind you about Manchester United matches ⚽🔴 "
    "and answer any questions about the club!\n\n"
    "🌐 /ru · /hy · /en\n"
    "🌙 /quiet · 🔔 /noisy"
)

GREETING = (
    "Привет, Артур! 👋\n"
    "Я буду напоминать тебе о матчах Манчестер Юнайтед ⚽🔴 "
    "и отвечать на любые вопросы о клубе!\n\n"
    "Բարև, Արթուր։ 👋\n"
    "Ես կհիշեցնեմ քեզ Մանչեսթեր Յունայթեդի խաղերի մասին ⚽🔴 "
    "և կպատասխանեմ ակումբի մասին ցանկացած հարցի։\n\n"
    "Hi Artur! 👋\n"
    "I'll remind you about Manchester United matches ⚽🔴 "
    "and answer any questions about the club!\n\n"
    "🌐 /ru · /hy · /en\n"
    "🌙 /quiet · 🔔 /noisy"
)

TEST_PREFIX = (
    "🧪 Тестовый режим / Test mode\n"
    "Команда /bday покажет поздравление с днём рождения.\n\n"
)

# Меню команд (кнопка «Меню» рядом с полем ввода). Увеличь MENU_VERSION, если поменяешь список.
MENU_VERSION = 1
MENU = {
    "en": [
        ("start", "Start"),
        ("ru", "Русский"),
        ("hy", "Հայերեն"),
        ("en", "English"),
        ("quiet", "Quiet night 🌙 (no night reminders)"),
        ("noisy", "Noisy night 🔔 (reminders at night too)"),
    ],
    "ru": [
        ("start", "Запуск бота"),
        ("ru", "Русский язык"),
        ("hy", "Հայերեն (армянский)"),
        ("en", "English (английский)"),
        ("quiet", "Спокойная ночка 🌙 без ночных сообщений"),
        ("noisy", "Неспокойная ночка 🔔 сообщения и ночью"),
    ],
    "hy": [
        ("start", "Մեկնարկ"),
        ("ru", "Русский"),
        ("hy", "Հայերեն"),
        ("en", "English"),
        ("quiet", "Հանգիստ գիշեր 🌙"),
        ("noisy", "Անհանգիստ գիշեր 🔔"),
    ],
}

SYSTEM_PROMPT = (
    "Ты — Telegram-бот, фанат и эксперт по футбольному клубу Манчестер Юнайтед. "
    "Ты знаешь историю клуба, игроков, тренеров, трофеи, рекорды, Олд Траффорд и трансферы. "
    "Отвечай дружелюбно и коротко (до 8 предложений). "
    "Человек написал на языке: {lang}. Обязательно отвечай на этом же языке. "
    "Если не уверен в факте или вопрос про свежие события, честно скажи об этом "
    "и ничего не выдумывай. "
    "Если вопрос не про МЮ и не про футбол, мягко скажи, что ты бот про Манчестер Юнайтед."
)


def load():
    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}
    state.setdefault("offset", 0)
    state.setdefault("chat_id", None)  # чат Артура
    state.setdefault("tester_chat_id", None)  # чат тестировщика
    state.setdefault("notified", [])
    state.setdefault("langs", {})  # язык для каждого чата
    state.setdefault("quiet", {})  # спокойная ночка для каждого чата (по умолчанию включена)
    return state


def send(chat_id, text):
    requests.post(
        f"{TG}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4000]},
        timeout=20,
    )


def set_commands(items, language_code=None, chat_id=None):
    payload = {"commands": [{"command": c, "description": d} for c, d in items]}
    if language_code:
        payload["language_code"] = language_code
    if chat_id:
        payload["scope"] = {"type": "chat", "chat_id": chat_id}
    try:
        r = requests.post(f"{TG}/setMyCommands", json=payload, timeout=20)
        return r.status_code == 200
    except Exception as e:
        print(f"setMyCommands error: {e}")
        return False


def update_menu():
    """Ставим меню команд. Повторно только если список поменялся."""
    if state.get("menu_version") != MENU_VERSION:
        ok = all(
            [
                set_commands(MENU["en"]),
                set_commands(MENU["ru"], "ru"),
                set_commands(MENU["hy"], "hy"),
            ]
        )
        if ok:
            state["menu_version"] = MENU_VERSION
            state["menu_tester"] = None
    # У тестировщика в меню есть ещё команда /bday
    tc = state.get("tester_chat_id")
    if tc and state.get("menu_tester") != tc:
        items = MENU["en"] + [("bday", "Birthday greeting test 🎂")]
        if set_commands(items, chat_id=tc):
            state["menu_tester"] = tc


def role_of(user_id):
    uid = str(user_id)
    if ALLOWED_ID and uid == ALLOWED_ID:
        return "artur"
    if TESTER_ID and uid == TESTER_ID:
        return "tester"
    return None


def get_lang(chat_id):
    return state["langs"].get(str(chat_id), "ru")


def is_quiet(chat_id):
    return state["quiet"].get(str(chat_id), True)


def detect_lang(text):
    """Определяем язык по буквам: армянские, кириллица или латиница."""
    counts = {
        "hy": sum("\u0531" <= ch <= "\u058f" for ch in text),
        "ru": sum("\u0400" <= ch <= "\u04ff" for ch in text),
        "en": sum(ch.isascii() and ch.isalpha() for ch in text),
    }
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else None


def human_left(left, tx):
    """Сколько осталось до матча: минуты (если меньше полутора часов) или часы."""
    minutes = round(left.total_seconds() / 60)
    if minutes < 90:
        return tx["left_m"].format(n=max(minutes, 1))
    return tx["left_h"].format(n=round(minutes / 60))


def ask_gemini(question, context, lang):
    prompt = SYSTEM_PROMPT.format(lang=LANG_NAMES[lang]) + "\n" + context
    body = {
        "system_instruction": {"parts": [{"text": prompt}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
    }
    for model in GEMINI_MODELS:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
                json=body,
                timeout=60,
            )
            if r.status_code != 200:
                print(f"Gemini {model}: {r.status_code} {r.text[:200]}")
                continue
            parts = r.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
        except Exception as e:
            print(f"Gemini {model} error: {e}")
    return "🙈 Error / Սխալ / Ошибка"


state = load()
questions = []
now = datetime.now(timezone.utc)
birthday_today = (now.astimezone(TZ).month, now.astimezone(TZ).day) == BIRTHDAY

# 1. Читаем новые сообщения
updates = requests.get(
    f"{TG}/getUpdates",
    params={"offset": state["offset"], "timeout": 0},
    timeout=20,
).json()

for u in updates.get("result", []):
    state["offset"] = u["update_id"] + 1
    msg = u.get("message", {})
    text = msg.get("text", "")
    if not text:
        continue
    chat_id = msg["chat"]["id"]
    user_id = msg.get("from", {}).get("id")
    cmd = text.split()[0].split("@")[0].lower()
    role = role_of(user_id)
    phrase = text.strip().lower().strip("!.?, ")

    # Чужие: пока место Артура свободно, на /start показываем им их ID
    if role is None:
        if cmd == "/start" and not ALLOWED_ID:
            send(chat_id, f"Твой Telegram ID / Your Telegram ID: {user_id}")
        continue

    if cmd == "/start":
        if role == "artur":
            state["chat_id"] = chat_id
            send(chat_id, GREETING_BIRTHDAY if birthday_today else GREETING)
        else:
            state["tester_chat_id"] = chat_id
            send(chat_id, TEST_PREFIX + (GREETING_BIRTHDAY if birthday_today else GREETING))
    elif cmd == "/bday" and role == "tester":
        send(chat_id, TEST_PREFIX + GREETING_BIRTHDAY)
    elif cmd in ("/ru", "/hy", "/en"):
        state["langs"][str(chat_id)] = cmd[1:]
        send(chat_id, TEXTS[cmd[1:]]["set"])
    elif cmd == "/quiet" or phrase == "спокойная ночка":
        state["quiet"][str(chat_id)] = True
        send(chat_id, TEXTS[get_lang(chat_id)]["quiet_on"])
    elif cmd == "/noisy" or phrase == "неспокойная ночка":
        state["quiet"][str(chat_id)] = False
        send(chat_id, TEXTS[get_lang(chat_id)]["quiet_off"])
    elif cmd.startswith("/"):
        continue  # неизвестные команды игнорируем
    else:
        qlang = detect_lang(text) or get_lang(chat_id)
        state["langs"][str(chat_id)] = qlang  # напоминания идут на языке последнего сообщения
        questions.append((chat_id, text, qlang))

# Меню команд
update_menu()

# 2. Календарь матчей
recipients = [c for c in (state["chat_id"], state["tester_chat_id"]) if c]
matches = []
if recipients:
    resp = requests.get(
        "https://api.football-data.org/v4/teams/66/matches",
        params={"status": "SCHEDULED,TIMED"},
        headers={"X-Auth-Token": FD_KEY},
        timeout=20,
    ).json()
    matches = sorted(resp.get("matches", []), key=lambda m: m["utcDate"])

# 3. Напоминания о матчах (ночью только тем, у кого выключена «спокойная ночка»)
local_now = now.astimezone(TZ)
night = local_now.hour >= QUIET_START or local_now.hour < QUIET_END
for match in matches:
    start = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
    left = start - now
    if left <= timedelta(0):
        continue

    # Самый близкий этап, в который матч уже попал
    stage = None
    for i, delta in enumerate(STAGES):
        if left <= delta:
            stage = i
    if stage is None:
        continue

    local = start.astimezone(TZ)
    for rc in recipients:
        if night and is_quiet(rc):
            continue  # подождём до утра
        key = f"{match['id']}:{stage}:{rc}"
        if key in state["notified"]:
            continue
        tx = TEXTS[get_lang(rc)]
        send(
            rc,
            tx["title"].format(w=human_left(left, tx)) + "\n"
            f"{match['homeTeam']['name']} — {match['awayTeam']['name']}\n"
            + tx["at"].format(
                c=match["competition"]["name"],
                d=local.strftime("%d.%m"),
                t=local.strftime("%H:%M"),
            ),
        )
        state["notified"].append(key)

state["notified"] = state["notified"][-200:]

# 4. Ответы на вопросы (Артуру и тестировщику)
if GEMINI_KEY and questions:
    next_games = "; ".join(
        f"{m['homeTeam']['name']} — {m['awayTeam']['name']} "
        f"({datetime.fromisoformat(m['utcDate'].replace('Z', '+00:00')).astimezone(TZ).strftime('%d.%m %H:%M')})"
        for m in matches[:3]
    )
    context = f"Сегодня {now.astimezone(TZ).strftime('%d.%m.%Y')}. Ближайшие матчи МЮ: {next_games or 'нет данных'}."
    for chat_id, text, qlang in questions[:MAX_QUESTIONS_PER_RUN]:
        send(chat_id, ask_gemini(text, context, qlang))

with open("state.json", "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False)
import os
from aiohttp import web

async def handle(request):
    return web.Response(text="OK")

app = web.Application
app.add_routes([web.get('/handle)])

if __name__ == '__main__'
    port = int(os.environ.get("PORT", 10000)
    web.run_app(app, host='0.0.0.0', port=port)

