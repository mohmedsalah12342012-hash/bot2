import asyncio
import random
import re
import sqlite3
import time
import os

import discord

# ======================= الإعدادات =======================
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 1511661628394049617          # الشخص الوحيد المسموح له بالأوامر الخطيرة
CHANNEL_ID = 1558869670428414087        # الروم الوحيد اللي البوت بيشتغل فيه
CURRENCY = "🪙"
START_BALANCE = 500
MIN_BET = 10
MAX_BET = 100000
PRICE_INTERVAL = 3 * 60   # كل كام ثانية أسعار المتجر تتغير (3 دقايق)
PAGE_SIZE = 10            # عدد المنتجات في كل صفحة من المتجر
DB_FILE = "coinbot.db"
GOLD = discord.Color.gold()

# مدة الانتظار بالثواني
COOLDOWNS = {
    "عمل": 24 * 3600,
    "يومي": 24 * 3600,
    "بخشيش": 3600,
    "استثمار": 4 * 60,
    "سرقة": 24 * 3600,
    "جريمة": 10 * 3600,
    "بحث": 5 * 60,
    "صيد": 10 * 60,
    "تعدين": 15 * 60,
}

# أسماء المنتجات اللي ليها تأثير
SHIELD, ROD, PICK, LAPTOP, GUN = "درع الحماية", "سنارة", "فأس التعدين", "لابتوب", "مسدس"

DEFAULT_ITEMS = [
    # منتجات ليها تأثير
    (SHIELD, "🛡️", 5000, "بيحميك من سرقة واحدة (بيتستهلك)"),
    (ROD, "🎣", 1500, "بتضاعف أرباح الصيد"),
    (PICK, "⛏️", 3000, "بيضاعف أرباح التعدين"),
    (LAPTOP, "💻", 4000, "بيزود أرباح العمل 50%"),
    (GUN, "🔫", 8000, "بيزود فرصة نجاح السرقة"),
    # أكل ومشروبات
    ("قهوة", "☕", 25, "فنجان قهوة للتفاخر"),
    ("برجر", "🍔", 40, "وجبة سريعة"),
    ("بيتزا", "🍕", 60, "وجبة إيطالي"),
    ("كرة قدم", "⚽", 300, "للهواة"),
    # حيوانات أليفة
    ("قطة", "🐱", 700, "صاحب وفي"),
    ("كلب", "🐶", 900, "حارس البيت"),
    ("ببغاء", "🦜", 1100, "بيرد عليك الكلام"),
    ("حصان", "🐎", 6000, "للفروسية"),
    ("أسد", "🦁", 30000, "ملك الغابة"),
    ("تنين", "🐉", 120000, "أسطورة نادرة"),
    # إلكترونيات
    ("سماعات", "🎧", 900, "صوت نقي"),
    ("هاتف", "📱", 1200, "آخر موديل"),
    ("ساعة ذكية", "⌚", 1800, "بتتابع خطواتك"),
    ("جيتار", "🎸", 2000, "للموسيقيين"),
    ("كاميرا", "📷", 2200, "لقطات احترافية"),
    ("تلفزيون", "📺", 2500, "شاشة سينما"),
    ("بلايستيشن", "🎮", 3500, "للاعبين"),
    ("بيانو", "🎹", 12000, "ألحان فخمة"),
    ("روبوت", "🤖", 45000, "مساعد شخصي"),
    # مواصلات
    ("دراجة", "🚲", 1500, "رياضة وتوفير"),
    ("تذكرة سفر", "🎫", 3000, "رحلة الأحلام"),
    ("دراجة نارية", "🏍️", 9000, "للسرعة"),
    ("سيارة", "🚗", 25000, "للتفاخر بس 😎"),
    ("سيارة رياضية", "🏎️", 60000, "سرعة جنونية"),
    ("هليكوبتر", "🚁", 220000, "فوق الزحمة"),
    ("يخت", "🛥️", 150000, "على البحر"),
    ("طيارة خاصة", "✈️", 400000, "رفاهية مطلقة"),
    ("صاروخ", "🚀", 350000, "رحلة للفضاء"),
    # عقارات
    ("شقة", "🏢", 40000, "في قلب المدينة"),
    ("فيلا", "🏰", 75000, "للتفاخر بس 😎"),
    ("قصر", "🏯", 200000, "قصر ملكي"),
    ("جزيرة", "🏝️", 500000, "جزيرة خاصة بيك"),
    # كماليات ونفائس
    ("كتاب نادر", "📖", 5000, "نسخة قديمة"),
    ("عقد لؤلؤ", "📿", 7000, "أناقة"),
    ("كأس البطولة", "🏆", 15000, "للأبطال"),
    ("خاتم ألماس", "💍", 18000, "فخامة"),
    ("ساعة فخمة", "🕰️", 22000, "تحفة نادرة"),
    ("لوحة فنية", "🖼️", 35000, "عمل فني أصلي"),
    ("ألماسة", "💎", 80000, "حجر نادر"),
    ("تاج الملوك", "👑", 250000, "أغلى حاجة في السيرفر"),
]

# ======================= قاعدة البيانات =======================
db = sqlite3.connect(DB_FILE)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY, wallet INTEGER DEFAULT 0, bank INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0, last_daily REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS cooldowns(uid INTEGER, cmd TEXT, ts REAL, PRIMARY KEY(uid, cmd));
CREATE TABLE IF NOT EXISTS items(name TEXT PRIMARY KEY, emoji TEXT, price INTEGER, descr TEXT, base INTEGER, prev INTEGER);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS inventory(uid INTEGER, item TEXT, qty INTEGER, PRIMARY KEY(uid, item));
CREATE TABLE IF NOT EXISTS donations(uid INTEGER PRIMARY KEY, total INTEGER DEFAULT 0);
""")
# ترقية قاعدة بيانات قديمة (لو كانت موجودة من نسخة سابقة)
_cols = [r["name"] for r in db.execute("PRAGMA table_info(items)")]
if "base" not in _cols:
    db.execute("ALTER TABLE items ADD COLUMN base INTEGER")
    db.execute("UPDATE items SET base=price")
if "prev" not in _cols:
    db.execute("ALTER TABLE items ADD COLUMN prev INTEGER")
    db.execute("UPDATE items SET prev=price")
# إضافة المنتجات الافتراضية مرة واحدة بس (عشان لو مسحت منتج ميرجعش)
if not db.execute("SELECT 1 FROM meta WHERE k='seeded_v2'").fetchone():
    for n, e_, pr, d in DEFAULT_ITEMS:
        db.execute("INSERT OR IGNORE INTO items VALUES(?,?,?,?,?,?)", (n, e_, pr, d, pr, pr))
    db.execute("INSERT INTO meta VALUES('seeded_v2','1')")
db.commit()


def meta_get(k, default=0):
    r = db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return float(r["v"]) if r else default


def meta_set(k, v):
    db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(v)))
    db.commit()


def update_prices():
    """يغير أسعار كل المنتجات: ممكن تزيد أو تقل أو تثبت، مع ميل خفيف للرجوع للسعر الأساسي"""
    for it in db.execute("SELECT * FROM items").fetchall():
        base, price = it["base"] or it["price"], it["price"]
        if random.random() < 0.15:          # أحياناً السعر بيثبت
            new = price
        else:
            new = price * (1 + random.uniform(-0.15, 0.20))
            new += (base - new) * 0.10
            new = max(base * 0.4, min(base * 2.5, new))
        new = max(1, int(round(new)))
        db.execute("UPDATE items SET prev=?, price=? WHERE name=?", (price, new, it["name"]))
    db.commit()


async def price_loop():
    while True:
        wait = PRICE_INTERVAL - (time.time() - meta_get("last_update", 0))
        if wait > 0:
            await asyncio.sleep(wait)
        update_prices()
        meta_set("last_update", time.time())


def get_user(uid):
    r = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.execute("INSERT INTO users(id, wallet) VALUES(?,?)", (uid, START_BALANCE))
        db.commit()
        r = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return r


def change(uid, wallet=0, bank=0):
    get_user(uid)
    db.execute("UPDATE users SET wallet=wallet+?, bank=bank+? WHERE id=?", (wallet, bank, uid))
    db.commit()


def remove_money(uid, amount):
    """يشيل من الكاش الأول وبعدين البنك، ومينزلش عن صفر. بيرجع المبلغ اللي اتشال فعلاً"""
    u = get_user(uid)
    from_wallet = min(u["wallet"], amount)
    from_bank = min(u["bank"], amount - from_wallet)
    change(uid, -from_wallet, -from_bank)
    return from_wallet + from_bank


def cooldown_left(uid, cmd):
    r = db.execute("SELECT ts FROM cooldowns WHERE uid=? AND cmd=?", (uid, cmd)).fetchone()
    if r:
        left = COOLDOWNS[cmd] - (time.time() - r["ts"])
        return left if left > 0 else 0
    return 0


def set_cooldown(uid, cmd):
    db.execute("INSERT OR REPLACE INTO cooldowns VALUES(?,?,?)", (uid, cmd, time.time()))
    db.commit()


def inv_get(uid, item):
    r = db.execute("SELECT qty FROM inventory WHERE uid=? AND item=?", (uid, item)).fetchone()
    return r["qty"] if r else 0


def inv_add(uid, item, n):
    q = inv_get(uid, item) + n
    if q <= 0:
        db.execute("DELETE FROM inventory WHERE uid=? AND item=?", (uid, item))
    else:
        db.execute("INSERT OR REPLACE INTO inventory VALUES(?,?,?)", (uid, item, q))
    db.commit()


# ======================= أدوات مساعدة =======================
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def money(n):
    return f"**{int(n):,}** {CURRENCY}"


def fmt_time(sec):
    sec = int(sec)
    h, mi, s = sec // 3600, (sec % 3600) // 60, sec % 60
    parts = []
    if h:
        parts.append(f"{h} ساعة")
    if mi:
        parts.append(f"{mi} دقيقة")
    if s or not parts:
        parts.append(f"{s} ثانية")
    return " و ".join(parts)


def parse_amount(tok, available):
    t = tok.strip().replace(",", "").translate(AR_DIGITS)
    if t in ("الكل", "كل", "all", "max"):
        return available
    if t in ("نص", "نصف"):
        return available // 2
    return int(t) if t.isdigit() else None


def emb(title, desc="", color=GOLD):
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Coinbot 🪙")
    return e


async def say(m, e):
    await m.reply(embed=e, mention_author=False)


def err(text):
    return emb("❌ تنبيه", text, discord.Color.red())


def clean_args(args):
    return [a for a in args if not re.fullmatch(r"<@!?\d+>", a)]


def get_target(m):
    for u in m.mentions:
        if not u.bot:
            return u
    return None


def is_owner(m):
    return m.author.id == OWNER_ID


async def owner_only(m):
    if is_owner(m):
        return True
    await say(m, err("الأمر ده للمالك بس 🚫"))
    return False


async def cd_check(m, cmd):
    left = cooldown_left(m.author.id, cmd)
    if left > 0:
        await say(m, emb("⏳ استنى شوية", f"تقدر تستخدم **{cmd}** تاني بعد **{fmt_time(left)}**",
                         discord.Color.orange()))
        return False
    return True


async def get_bet(m, args):
    u = get_user(m.author.id)
    if not args:
        await say(m, err("اكتب المبلغ، مثال: `{} 100`".format(m.content.split()[0])))
        return None
    amt = parse_amount(args[0], u["wallet"])
    if amt is None or amt < MIN_BET:
        await say(m, err(f"المبلغ لازم يكون رقم، وأقل رهان {MIN_BET} {CURRENCY}"))
        return None
    if amt > u["wallet"]:
        await say(m, err(f"رصيدك الكاش مش كفاية! معاك {money(u['wallet'])}"))
        return None
    if amt > MAX_BET:
        await say(m, err(f"أقصى رهان {MAX_BET:,} {CURRENCY}"))
        return None
    return amt


async def name_of(client, uid):
    try:
        u = client.get_user(uid) or await client.fetch_user(uid)
        return u.display_name
    except Exception:
        return f"مستخدم {uid}"


# ======================= أوامر الحساب =======================
async def cmd_balance(m, args):
    target = get_target(m) or m.author
    u = get_user(target.id)
    total = u["wallet"] + u["bank"]
    rank = db.execute("SELECT COUNT(*)+1 AS r FROM users WHERE wallet+bank > ?", (total,)).fetchone()["r"]
    items = db.execute("SELECT COALESCE(SUM(qty),0) AS c FROM inventory WHERE uid=?", (target.id,)).fetchone()["c"]
    e = emb(f"💳 حساب {target.display_name}")
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="💵 الكاش", value=money(u["wallet"]))
    e.add_field(name="🏦 البنك", value=money(u["bank"]))
    e.add_field(name="💰 الإجمالي", value=money(total))
    e.add_field(name="🏆 الترتيب", value=f"#{rank}")
    e.add_field(name="🎒 المقتنيات", value=f"{items} قطعة")
    e.add_field(name="🔥 أيام اليومي", value=str(u["streak"]))
    await say(m, e)


async def cmd_deposit(m, args):
    u = get_user(m.author.id)
    if not args:
        return await say(m, err("اكتب المبلغ، مثال: `إيداع 500` أو `إيداع الكل`"))
    amt = parse_amount(args[0], u["wallet"])
    if not amt or amt <= 0:
        return await say(m, err("المبلغ غلط"))
    if amt > u["wallet"]:
        return await say(m, err("معاكش كاش كفاية"))
    change(m.author.id, -amt, amt)
    await say(m, emb("🏦 إيداع", f"اتحط {money(amt)} في البنك", discord.Color.green()))


async def cmd_withdraw(m, args):
    u = get_user(m.author.id)
    if not args:
        return await say(m, err("اكتب المبلغ، مثال: `سحب 500` أو `سحب الكل`"))
    amt = parse_amount(args[0], u["bank"])
    if not amt or amt <= 0:
        return await say(m, err("المبلغ غلط"))
    if amt > u["bank"]:
        return await say(m, err("البنك مفيهوش فلوس كفاية"))
    change(m.author.id, amt, -amt)
    await say(m, emb("🏧 سحب", f"سحبت {money(amt)} من البنك", discord.Color.green()))


async def cmd_transfer(m, args):
    target = get_target(m)
    rest = clean_args(args)
    if not target or not rest:
        return await say(m, err("الاستخدام: `تحويل @الشخص المبلغ`"))
    if target.id == m.author.id:
        return await say(m, err("متقدرش تحول لنفسك 😅"))
    u = get_user(m.author.id)
    amt = parse_amount(rest[0], u["wallet"])
    if not amt or amt <= 0:
        return await say(m, err("المبلغ غلط"))
    if amt > u["wallet"]:
        return await say(m, err("رصيدك الكاش مش كفاية"))
    change(m.author.id, -amt)
    change(target.id, amt)
    e = emb("💸 تحويل ناجح", f"{m.author.mention} حوّل {money(amt)} إلى {target.mention}", discord.Color.green())
    e.set_thumbnail(url=target.display_avatar.url)
    await say(m, e)


async def cmd_donate(m, args):
    u = get_user(m.author.id)
    if not args:
        return await say(m, err("الاستخدام: `تبرع المبلغ` (بيروح للصندوق الخيري)"))
    amt = parse_amount(args[0], u["wallet"])
    if not amt or amt <= 0 or amt > u["wallet"]:
        return await say(m, err("المبلغ غلط أو رصيدك مش كفاية"))
    change(m.author.id, -amt)
    db.execute("INSERT INTO donations VALUES(?,?) ON CONFLICT(uid) DO UPDATE SET total=total+?",
               (m.author.id, amt, amt))
    db.commit()
    await say(m, emb("💝 شكراً على تبرعك", f"{m.author.mention} تبرع بـ {money(amt)} للصندوق الخيري، ربنا يكرمك!",
                     discord.Color.magenta()))


async def cmd_fund(m, args):
    total = db.execute("SELECT COALESCE(SUM(total),0) AS t FROM donations").fetchone()["t"]
    top = db.execute("SELECT uid, total FROM donations ORDER BY total DESC LIMIT 3").fetchall()
    lines = []
    for i, r in enumerate(top):
        lines.append(f"{['🥇', '🥈', '🥉'][i]} {await name_of(client, r['uid'])} — {money(r['total'])}")
    await say(m, emb("💝 الصندوق الخيري", f"إجمالي التبرعات: {money(total)}\n\n" + ("\n".join(lines) or "لسه مفيش تبرعات")))


async def cmd_leaderboard(m, args):
    rows = db.execute("SELECT id, wallet+bank AS total FROM users ORDER BY total DESC LIMIT 10").fetchall()
    if not rows:
        return await say(m, err("لسه مفيش حد عنده فلوس"))
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
    lines = [f"{medals[i]} **{await name_of(client, r['id'])}** — {money(r['total'])}" for i, r in enumerate(rows)]
    e = emb("🏆 أغنى 10 في السيرفر", "\n".join(lines))
    try:
        top = client.get_user(rows[0]["id"]) or await client.fetch_user(rows[0]["id"])
        e.set_thumbnail(url=top.display_avatar.url)
    except Exception:
        pass
    await say(m, e)


# ======================= أوامر الكسب =======================
async def cmd_work(m, args):
    if not await cd_check(m, "عمل"):
        return
    jobs = ["مبرمج 💻", "طبيب 🩺", "نجار 🪚", "سواق 🚕", "طباخ 👨‍🍳", "مهندس 👷", "مدرس 📚", "ميكانيكي 🔧"]
    amt = random.randint(300, 800)
    bonus = ""
    if inv_get(m.author.id, LAPTOP):
        amt = int(amt * 1.5)
        bonus = "\n💻 زيادة 50% بسبب اللابتوب"
    change(m.author.id, amt)
    set_cooldown(m.author.id, "عمل")
    await say(m, emb("💼 شغل النهارده", f"اشتغلت **{random.choice(jobs)}** وكسبت {money(amt)}{bonus}", discord.Color.green()))


async def cmd_daily(m, args):
    if not await cd_check(m, "يومي"):
        return
    u = get_user(m.author.id)
    now = time.time()
    streak = u["streak"] + 1 if now - u["last_daily"] < 48 * 3600 else 1
    amt = 200 + 50 * min(streak, 30)
    change(m.author.id, amt)
    db.execute("UPDATE users SET streak=?, last_daily=? WHERE id=?", (streak, now, m.author.id))
    set_cooldown(m.author.id, "يومي")
    await say(m, emb("🎁 المكافأة اليومية", f"استلمت {money(amt)}\n🔥 عدد الأيام المتتالية: **{streak}**", discord.Color.green()))


async def cmd_tip(m, args):
    if not await cd_check(m, "بخشيش"):
        return
    amt = random.randint(20, 100)
    change(m.author.id, amt)
    set_cooldown(m.author.id, "بخشيش")
    await say(m, emb("🤲 بخشيش", f"واحد كريم ادّاك بخشيش {money(amt)}", discord.Color.green()))


async def cmd_search(m, args):
    if not await cd_check(m, "بحث"):
        return
    places = ["🗑️ الزبالة", "🛋️ تحت الكنبة", "🚗 العربية", "🌳 الحديقة", "👖 جيب بنطلون قديم", "🏖️ الشاطئ", "🏚️ بيت مهجور"]
    place = random.choice(places)
    set_cooldown(m.author.id, "بحث")
    if random.random() < 0.2:
        return await say(m, emb("🔎 بحث", f"دورت في {place} ومالقيتش حاجة 😅", discord.Color.orange()))
    amt = random.randint(10, 120)
    change(m.author.id, amt)
    await say(m, emb("🔎 بحث", f"دورت في {place} ولقيت {money(amt)}", discord.Color.green()))


async def cmd_fish(m, args):
    if not await cd_check(m, "صيد"):
        return
    catches = [("🐟 سمكة", 30, 60), ("🐠 سمكة ملونة", 50, 100), ("🦈 قرش", 150, 300),
               ("🦀 سلطعون", 40, 80), ("👢 جزمة قديمة", 0, 0)]
    name, lo, hi = random.choice(catches)
    amt = random.randint(lo, hi) if hi else 0
    note = ""
    if amt and inv_get(m.author.id, ROD):
        amt *= 2
        note = "\n🎣 الأرباح اتضاعفت بالسنارة"
    set_cooldown(m.author.id, "صيد")
    change(m.author.id, amt)
    await say(m, emb("🎣 صيد", f"اصطدت **{name}** وبعتها بـ {money(amt)}{note}",
                     discord.Color.green() if amt else discord.Color.orange()))


async def cmd_mine(m, args):
    if not await cd_check(m, "تعدين"):
        return
    ores = [("🪨 حجر", 20, 60), ("⛓️ حديد", 60, 140), ("🥇 ذهب", 150, 300), ("💎 ألماس", 300, 600)]
    name, lo, hi = random.choices(ores, weights=[45, 30, 18, 7])[0]
    amt = random.randint(lo, hi)
    note = ""
    if inv_get(m.author.id, PICK):
        amt *= 2
        note = "\n⛏️ الأرباح اتضاعفت بالفأس"
    set_cooldown(m.author.id, "تعدين")
    change(m.author.id, amt)
    await say(m, emb("⛏️ تعدين", f"طلّعت **{name}** وبعته بـ {money(amt)}{note}", discord.Color.green()))


async def cmd_invest(m, args):
    if not await cd_check(m, "استثمار"):
        return
    amt = await get_bet(m, args)
    if amt is None:
        return
    set_cooldown(m.author.id, "استثمار")
    if random.random() < 0.55:
        gain = int(amt * random.uniform(0.1, 0.7))
        change(m.author.id, gain)
        await say(m, emb("📈 استثمار ناجح", f"استثمرت {money(amt)} وكسبت {money(gain)} 🎉", discord.Color.green()))
    else:
        loss = int(amt * random.uniform(0.1, 0.5))
        change(m.author.id, -loss)
        await say(m, emb("📉 استثمار فاشل", f"السوق وقع وخسرت {money(loss)} 😢", discord.Color.red()))


async def cmd_crime(m, args):
    if not await cd_check(m, "جريمة"):
        return
    crimes = ["سرقة بنك 🏦", "تهريب 📦", "نصب إلكتروني 💻", "سرقة معرض سيارات 🚗", "سرقة متحف 🖼️"]
    crime = random.choice(crimes)
    set_cooldown(m.author.id, "جريمة")
    if random.random() < 0.5:
        amt = random.randint(800, 3000)
        change(m.author.id, amt)
        await say(m, emb("🦹 جريمة ناجحة", f"نفذت **{crime}** وهربت بـ {money(amt)}", discord.Color.green()))
    else:
        fine = remove_money(m.author.id, random.randint(300, 1500))
        await say(m, emb("🚔 اتمسكت!", f"حاولت **{crime}** والبوليس مسكك ودفعت غرامة {money(fine)}", discord.Color.red()))


async def cmd_rob(m, args):
    target = get_target(m)
    if not target:
        return await say(m, err("الاستخدام: `سرقة @الشخص`"))
    if target.id == m.author.id:
        return await say(m, err("هتسرق نفسك؟ 😂"))
    if not await cd_check(m, "سرقة"):
        return
    victim = get_user(target.id)
    if victim["wallet"] < 200:
        return await say(m, err("الشخص ده كاشه قليل (أقل من 200)، مش هتستاهل المخاطرة"))
    set_cooldown(m.author.id, "سرقة")
    if inv_get(target.id, SHIELD):
        inv_add(target.id, SHIELD, -1)
        fine = remove_money(m.author.id, random.randint(100, 400))
        change(target.id, fine)
        return await say(m, emb("🛡️ الدرع حماه!", f"{target.mention} كان معاه درع حماية، وانت اتغرمت {money(fine)} ودرعه اتكسر.",
                                discord.Color.red()))
    chance = 0.4 + (0.15 if inv_get(m.author.id, GUN) else 0)
    if random.random() < chance:
        amt = max(1, int(victim["wallet"] * random.uniform(0.1, 0.3)))
        change(target.id, -amt)
        change(m.author.id, amt)
        e = emb("🥷 سرقة ناجحة", f"{m.author.mention} سرق {money(amt)} من {target.mention}", discord.Color.green())
    else:
        fine = remove_money(m.author.id, random.randint(100, 500))
        change(target.id, fine)
        e = emb("🚨 فشلت السرقة", f"{m.author.mention} اتمسك واتغرم {money(fine)} راحت لـ {target.mention}", discord.Color.red())
    e.set_thumbnail(url=target.display_avatar.url)
    await say(m, e)


# ======================= ألعاب الحظ =======================
async def cmd_gamble(m, args):
    amt = await get_bet(m, args)
    if amt is None:
        return
    if random.random() < 0.45:
        change(m.author.id, amt)
        await say(m, emb("🎰 قمار", f"كسبت! ربحت {money(amt)} 🎉", discord.Color.green()))
    else:
        change(m.author.id, -amt)
        await say(m, emb("🎰 قمار", f"خسرت {money(amt)} 😢", discord.Color.red()))


async def cmd_coin(m, args):
    if len(args) < 2 or args[1] not in ("صورة", "كتابة"):
        return await say(m, err("الاستخدام: `عملة المبلغ صورة` أو `عملة المبلغ كتابة`"))
    amt = await get_bet(m, args)
    if amt is None:
        return
    result = random.choice(["صورة", "كتابة"])
    if result == args[1]:
        change(m.author.id, amt)
        await say(m, emb("🪙 رمي العملة", f"طلعت **{result}** وكسبت {money(amt)} 🎉", discord.Color.green()))
    else:
        change(m.author.id, -amt)
        await say(m, emb("🪙 رمي العملة", f"طلعت **{result}** وخسرت {money(amt)} 😢", discord.Color.red()))


async def cmd_dice(m, args):
    amt = await get_bet(m, args)
    if amt is None:
        return
    mine, theirs = random.randint(1, 6), random.randint(1, 6)
    if mine > theirs:
        change(m.author.id, amt)
        res, col = f"كسبت {money(amt)} 🎉", discord.Color.green()
    elif mine < theirs:
        change(m.author.id, -amt)
        res, col = f"خسرت {money(amt)} 😢", discord.Color.red()
    else:
        res, col = "تعادل، فلوسك رجعتلك 🤝", discord.Color.orange()
    await say(m, emb("🎲 نرد", f"نردك: **{mine}** | نرد البوت: **{theirs}**\n{res}", col))


async def cmd_slots(m, args):
    amt = await get_bet(m, args)
    if amt is None:
        return
    sym = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
    r = [random.choice(sym) for _ in range(3)]
    line = " | ".join(r)
    if r[0] == r[1] == r[2]:
        change(m.author.id, amt * 4)
        res, col = f"جاكبوت!! ربحت {money(amt * 4)} 🤑", discord.Color.green()
    elif len(set(r)) == 2:
        win = amt // 2
        change(m.author.id, win)
        res, col = f"اتنين متشابهين، ربحت {money(win)} 🎉", discord.Color.green()
    else:
        change(m.author.id, -amt)
        res, col = f"خسرت {money(amt)} 😢", discord.Color.red()
    await say(m, emb("🎰 سلوتس", f"**{line}**\n{res}", col))


# ======================= المتجر =======================
def shop_items():
    return db.execute("SELECT * FROM items ORDER BY base, name").fetchall()


def find_item(q):
    items = shop_items()
    q = q.strip()
    if q.isdigit() and 1 <= int(q) <= len(items):
        return items[int(q) - 1]
    for it in items:
        if q == it["name"]:
            return it
    for it in items:
        if q and q in it["name"]:
            return it
    return None


def trend(it):
    prev = it["prev"] or it["price"]
    if it["price"] > prev:
        return f"📈 +{(it['price'] - prev) / prev * 100:.1f}%"
    if it["price"] < prev:
        return f"📉 -{(prev - it['price']) / prev * 100:.1f}%"
    return "➖ ثابت"


async def cmd_shop(m, args):
    items = shop_items()
    if not items:
        return await say(m, err("المتجر فاضي"))
    pages = (len(items) - 1) // PAGE_SIZE + 1
    page = 1
    if args and args[0].translate(AR_DIGITS).isdigit():
        page = min(max(1, int(args[0].translate(AR_DIGITS))), pages)
    start = (page - 1) * PAGE_SIZE
    lines = [f"**{i}.** {it['emoji']} **{it['name']}** — {money(it['price'])} {trend(it)}\n└ {it['descr']}"
             for i, it in enumerate(items[start:start + PAGE_SIZE], start + 1)]
    left = PRICE_INTERVAL - (time.time() - meta_get("last_update", 0))
    e = emb("🛒 المتجر", "\n".join(lines))
    e.add_field(name="🔄 تحديث الأسعار",
                value=f"الأسعار بتتغير كل {PRICE_INTERVAL // 60} دقايق، التحديث الجاي بعد **{fmt_time(max(0, left))}**",
                inline=False)
    e.add_field(name="💡 نصيحة", value="اشتري وهو رخيص وبيع وهو غالي، البيع بالسعر الحالي كامل!", inline=False)
    e.set_footer(text=f"صفحة {page}/{pages} • المتجر 2 للصفحة التانية • شراء الاسم/الرقم")
    await say(m, e)


async def cmd_buy(m, args):
    if not args:
        return await say(m, err("الاستخدام: `شراء الاسم` أو `شراء الرقم`"))
    qty = 1
    if len(args) > 1 and args[-1].translate(AR_DIGITS).isdigit():
        qty = max(1, int(args[-1].translate(AR_DIGITS)))
        args = args[:-1]
    item = find_item(" ".join(args))
    if not item:
        return await say(m, err("المنتج ده مش موجود في المتجر"))
    cost = item["price"] * qty
    u = get_user(m.author.id)
    if u["wallet"] < cost:
        return await say(m, err(f"محتاج {money(cost)} كاش وانت معاك {money(u['wallet'])}"))
    change(m.author.id, -cost)
    inv_add(m.author.id, item["name"], qty)
    await say(m, emb("✅ تم الشراء", f"اشتريت {qty} × {item['emoji']} **{item['name']}** بـ {money(cost)}", discord.Color.green()))


async def cmd_sell(m, args):
    if not args:
        return await say(m, err("الاستخدام: `بيع الاسم`"))
    item = find_item(" ".join(args))
    if not item or inv_get(m.author.id, item["name"]) < 1:
        return await say(m, err("معكش المنتج ده"))
    price = item["price"]
    inv_add(m.author.id, item["name"], -1)
    change(m.author.id, price)
    await say(m, emb("💰 تم البيع", f"بعت {item['emoji']} **{item['name']}** بالسعر الحالي {money(price)} {trend(item)}",
                     discord.Color.green()))


async def cmd_inventory(m, args):
    target = get_target(m) or m.author
    rows = db.execute("SELECT i.item, i.qty, s.emoji FROM inventory i LEFT JOIN items s ON s.name=i.item WHERE i.uid=?",
                      (target.id,)).fetchall()
    desc = "\n".join(f"{r['emoji'] or '📦'} **{r['item']}** × {r['qty']}" for r in rows) or "الحقيبة فاضية 🎒"
    e = emb(f"🎒 حقيبة {target.display_name}", desc)
    e.set_thumbnail(url=target.display_avatar.url)
    await say(m, e)


# ======================= أوامر المالك =======================
class ConfirmView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=45)
        self.author_id, self.value = author_id, None

    async def interaction_check(self, i):
        if i.user.id != self.author_id:
            await i.response.send_message("الزر ده مش ليك", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تأكيد", style=discord.ButtonStyle.danger, emoji="✅")
    async def ok(self, i, b):
        self.value = True
        await i.response.edit_message(content="✅ تم التأكيد", view=None)
        self.stop()

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary, emoji="❌")
    async def no(self, i, b):
        self.value = False
        await i.response.edit_message(content="❌ تم الإلغاء", view=None)
        self.stop()


async def confirm(m, text):
    view = ConfirmView(m.author.id)
    await m.reply(f"⚠️ {text}\nمتأكد؟", view=view, mention_author=False)
    await view.wait()
    return bool(view.value)


async def cmd_give(m, args):
    if not await owner_only(m):
        return
    target = get_target(m)
    rest = clean_args(args)
    amt = parse_amount(rest[0], 0) if rest else None
    if not target or not amt or amt <= 0:
        return await say(m, err("الاستخدام: `اعطاء @الشخص المبلغ`"))
    change(target.id, amt)
    e = emb("🎁 إضافة رصيد", f"تم إعطاء {target.mention} مبلغ {money(amt)}", discord.Color.green())
    e.set_thumbnail(url=target.display_avatar.url)
    await say(m, e)


async def cmd_take(m, args):
    if not await owner_only(m):
        return
    target = get_target(m)
    rest = clean_args(args)
    amt = parse_amount(rest[0], 0) if rest else None
    if not target or not amt or amt <= 0:
        return await say(m, err("الاستخدام: `ازالة @الشخص المبلغ`"))
    removed = remove_money(target.id, amt)
    e = emb("➖ خصم رصيد", f"تم خصم {money(removed)} من {target.mention}", discord.Color.red())
    e.set_thumbnail(url=target.display_avatar.url)
    await say(m, e)


async def cmd_reset_user(m, args):
    if not await owner_only(m):
        return
    target = get_target(m)
    if not target:
        return await say(m, err("الاستخدام: `تصفير @الشخص`"))
    if not await confirm(m, f"هتصفّر كل فلوس {target.display_name}"):
        return
    db.execute("UPDATE users SET wallet=0, bank=0, streak=0 WHERE id=?", (target.id,))
    db.commit()
    await say(m, emb("🧹 تصفير", f"تم تصفير حساب {target.mention}", discord.Color.red()))


async def cmd_reset_all(m, args):
    if not await owner_only(m):
        return
    if not await confirm(m, "هتصفّر فلوس **كل** الأعضاء ومقتنياتهم!"):
        return
    db.execute("UPDATE users SET wallet=0, bank=0, streak=0")
    db.execute("DELETE FROM inventory")
    db.commit()
    await say(m, emb("🧹 تصفير شامل", "تم تصفير اقتصاد السيرفر بالكامل", discord.Color.red()))


async def cmd_add_item(m, args):
    """اضافة_منتج الاسم السعر [إيموجي]"""
    if not await owner_only(m):
        return
    if len(args) < 2 or not args[-1].translate(AR_DIGITS).isdigit():
        return await say(m, err("الاستخدام: `اضافة_منتج الاسم السعر`"))
    price = int(args[-1].translate(AR_DIGITS))
    name = " ".join(args[:-1])
    db.execute("INSERT OR REPLACE INTO items VALUES(?,?,?,?,?,?)", (name, "📦", price, "منتج جديد", price, price))
    db.commit()
    await say(m, emb("✅ تمت الإضافة", f"المنتج **{name}** بسعر {money(price)}", discord.Color.green()))


async def cmd_del_item(m, args):
    if not await owner_only(m):
        return
    item = find_item(" ".join(args)) if args else None
    if not item:
        return await say(m, err("الاستخدام: `حذف_منتج الاسم`"))
    db.execute("DELETE FROM items WHERE name=?", (item["name"],))
    db.commit()
    await say(m, emb("🗑️ تم الحذف", f"اتحذف المنتج **{item['name']}**", discord.Color.red()))


async def cmd_force_prices(m, args):
    if not await owner_only(m):
        return
    update_prices()
    meta_set("last_update", time.time())
    await say(m, emb("🔄 تحديث الأسعار", "تم تحديث أسعار المتجر دلوقتي", discord.Color.green()))


async def cmd_clear(m, args):
    if not await owner_only(m):
        return
    await m.channel.purge(limit=None)
    await m.channel.send("🧹 تم مسح الشات", delete_after=5)


async def cmd_help(m, args):
    e = emb("📜 أوامر Coinbot", "كل الأوامر بالكلمة بس من غير `/` ولا `!`")
    e.add_field(name="💳 الحساب", value="`الرصيد [@شخص]` • `إيداع` • `سحب` • `تحويل @شخص مبلغ` • `تبرع` • `الصندوق` • `الأثرياء`", inline=False)
    e.add_field(name="💼 الكسب", value="`عمل` (24س) • `يومي` (24س) • `بخشيش` (ساعة) • `بحث` (5د) • `صيد` (10د) • `تعدين` (15د) • `استثمار مبلغ` (4د)", inline=False)
    e.add_field(name="🦹 المخاطرة", value="`سرقة @شخص` (24س) • `جريمة` (10س)", inline=False)
    e.add_field(name="🎰 ألعاب الحظ", value="`قمار مبلغ` • `عملة مبلغ صورة/كتابة` • `نرد مبلغ` • `سلوتس مبلغ`", inline=False)
    e.add_field(name="🛒 المتجر", value="`المتجر [رقم الصفحة]` (الأسعار بتتغير كل 3 دقايق) • `شراء الاسم/الرقم [الكمية]` • `بيع الاسم` (بالسعر الحالي) • `حقيبتي`", inline=False)
    if is_owner(m):
        e.add_field(name="👑 أوامر المالك", value="`اعطاء @شخص مبلغ` • `ازالة @شخص مبلغ` • `تصفير @شخص` • `تصفير_الكل` • `اضافة_منتج الاسم السعر` • `حذف_منتج الاسم` • `تحديث_المتجر` • `مسح`", inline=False)
    e.set_thumbnail(url=m.guild.me.display_avatar.url)
    await say(m, e)


COMMANDS = {}
for names, fn in [
    (("الرصيد", "رصيد", "فلوسي", "بروفايل"), cmd_balance),
    (("إيداع", "ايداع"), cmd_deposit),
    (("سحب",), cmd_withdraw),
    (("تحويل",), cmd_transfer),
    (("تبرع",), cmd_donate),
    (("الصندوق",), cmd_fund),
    (("الأثرياء", "الاثرياء", "المتصدرين"), cmd_leaderboard),
    (("عمل",), cmd_work),
    (("يومي",), cmd_daily),
    (("بخشيش",), cmd_tip),
    (("بحث",), cmd_search),
    (("صيد",), cmd_fish),
    (("تعدين",), cmd_mine),
    (("استثمار",), cmd_invest),
    (("جريمة",), cmd_crime),
    (("سرقة",), cmd_rob),
    (("قمار",), cmd_gamble),
    (("عملة",), cmd_coin),
    (("نرد",), cmd_dice),
    (("سلوتس",), cmd_slots),
    (("المتجر", "متجر", "الاسعار", "الأسعار"), cmd_shop),
    (("شراء",), cmd_buy),
    (("بيع",), cmd_sell),
    (("حقيبتي", "الحقيبة"), cmd_inventory),
    (("اعطاء", "إعطاء"), cmd_give),
    (("ازالة", "إزالة"), cmd_take),
    (("تصفير",), cmd_reset_user),
    (("تصفير_الكل",), cmd_reset_all),
    (("اضافة_منتج",), cmd_add_item),
    (("حذف_منتج",), cmd_del_item),
    (("تحديث_المتجر",), cmd_force_prices),
    (("مسح",), cmd_clear),
    (("الاوامر", "الأوامر", "اوامر", "مساعدة"), cmd_help),
]:
    for n in names:
        COMMANDS[n] = fn


# ======================= البوت =======================
intents = discord.Intents.default()
intents.message_content = True


class Coinbot(discord.Client):
    async def setup_hook(self):
        self.price_task = asyncio.create_task(price_loop())

    async def on_ready(self):
        print(f"Coinbot شغال باسم {self.user}")
        await self.change_presence(activity=discord.Game(name="اكتب: الاوامر"))

    async def on_message(self, message):
        if message.author.bot or not message.guild or message.channel.id != CHANNEL_ID:
            return
        parts = message.content.strip().split()
        if not parts or parts[0] not in COMMANDS:
            return
        try:
            await COMMANDS[parts[0]](message, parts[1:])
        except discord.Forbidden:
            await message.channel.send("❌ البوت معندوش صلاحية كافية هنا")
        except Exception as e:
            print("خطأ في الأمر", parts[0], e)
            await message.channel.send("❌ حصل خطأ غير متوقع، جرب تاني")


client = Coinbot(intents=intents)
client.run(TOKEN)