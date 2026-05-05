import discord, os, asyncio, re
from discord.ext import commands, tasks
from datetime import datetime, timezone
import aiosqlite, pytz

TOKEN = os.getenv("TOKEN")
CFG = {
    "welcome": "شات-العام", "log": "المخالفات", "bye": "شات-العام",
    "lvl_up": "لفل-اب", "weekly": "توب-الاسبوع",
    "new_role": ["الأعضاء الجدد", 0x95a5a6], "bad_role": ["غير موثق", 0xe74c3c],
    "lvl_roles": {1: ["مبتدئ", 0x95a5a6], 5: ["نشيط", 0x3498db], 10: ["متفاعل", 0x2ecc71], 20: ["أسطورة", 0xf1c40f], 50: ["VIP", 0xe74c3c]},
    "bad_words": ["سب1", "سب2", "يا حيوان", "ياحيوان", "يا كلب", "ياكلب", "يامريض", "كس امك", "كسامك", "كل زق", "كلزق"],
    "owner_id": 763363479960682506 # <<< حط آيدي حسابك هنا عشان النسخة التلقائية
}
warns, xp_cd, spam = {}, {}, {}

async def db_init():
    async with aiosqlite.connect('levels.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS levels (guild_id TEXT, user_id TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0, weekly_xp INTEGER DEFAULT 0, PRIMARY KEY (guild_id, user_id))')
        await db.commit()

async def get_data(g, u):
    async with aiosqlite.connect('levels.db') as db:
        async with db.execute('SELECT xp,level,weekly_xp FROM levels WHERE guild_id=? AND user_id=?', (g,u)) as c:
            r = await c.fetchone()
            return {"xp":r[0],"level":r[1],"weekly_xp":r[2]} if r else {"xp":0,"level":0,"weekly_xp":0}

async def save_data(g, u, xp, lvl, weekly):
    async with aiosqlite.connect('levels.db') as db:
        await db.execute('INSERT INTO levels VALUES (?,?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET xp=?,level=?,weekly_xp=?', (g,u,xp,lvl,weekly,xp,lvl,weekly))
        await db.commit()

def calc_lvl(xp): l=0; [l:=l+1 for _ in range(100) if xp>=(50*(l**2)+50*l)]; return l-1
def next_xp(l): return 50*(l**2)+50*l

def make_progress_bar(xp, lvl, bar_len=10):
    if lvl == 0: return "█" * bar_len, 100
    prev_xp = next_xp(lvl-1)
    needed = next_xp(lvl) - prev_xp
    have = xp - prev_xp
    prog = int((have / needed) * bar_len) if needed > 0 else bar_len
    bar = "█"*prog + "░"*(bar_len-prog)
    percent = int((have / needed) * 100) if needed > 0 else 100
    return bar, percent

async def update_role(m, lvl):
    for r in [discord.utils.get(m.guild.roles, name=d[0]) for d in CFG["lvl_roles"].values() if discord.utils.get(m.guild.roles, name=d[0]) in m.roles]:
        await m.remove_roles(r)
    for lv, (n, c) in sorted(CFG["lvl_roles"].items(), reverse=True):
        if lvl >= lv:
            r = discord.utils.get(m.guild.roles, name=n) or await m.guild.create_role(name=n, color=c)
            await m.add_roles(r); return r

async def temp_mute(m, s, reason):
    r = discord.utils.get(m.guild.roles, name="Muted") or await m.guild.create_role(name="Muted")
    for ch in m.guild.channels: await ch.set_permissions(r, send_messages=False, add_reactions=False)
    await m.add_roles(r, reason=reason); await asyncio.sleep(s); await m.remove_roles(r)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@tasks.loop(time=datetime.strptime("12:00", "%H:%M").time())
async def weekly_top():
    if datetime.now(pytz.timezone('Asia/Riyadh')).weekday()!=4: return
    for g in bot.guilds:
        ch = discord.utils.get(g.channels, name=CFG["weekly"])
        if not ch: continue
        async with aiosqlite.connect('levels.db') as db:
            async with db.execute('SELECT user_id,weekly_xp,level FROM levels WHERE guild_id=? AND weekly_xp>0 ORDER BY weekly_xp DESC LIMIT 10', (str(g.id),)) as c:
                top = await c.fetchall()
        if not top: await ch.send(embed=discord.Embed(title="😴 لا يوجد متفاعلين", description="مافي أحد جمع XP هذا الأسبوع", color=0x95a5a6))
        else:
            e = discord.Embed(title="🏆 توب 10 لهذا الأسبوع", description="**أكثر 10 أعضاء تفاعلاً خلال 7 أيام**", color=0xf1c40f)
            e.set_thumbnail(url=g.icon.url if g.icon else None)
            medals = ["🥇", "🥈", "🥉"]
            desc = ""
            for i,(u,x,l) in enumerate(top,1):
                medal = medals[i-1] if i<=3 else f"**{i}.**"
                desc += f"{medal} <@{u}>\n└ `{x:,} XP` • لفل `{l}`\n\n"
            e.description = desc
            e.set_footer(text="يتصفر كل جمعة الساعة 12 ظهراً", icon_url=bot.user.avatar.url if bot.user.avatar else None)
            e.timestamp = datetime.now(timezone.utc)
            await ch.send(embed=e)
        async with aiosqlite.connect('levels.db') as db: await db.execute('UPDATE levels SET weekly_xp=0 WHERE guild_id=?', (str(g.id),)); await db.commit()

# === نسخة احتياطية تلقائية كل 12 ساعة ===
@tasks.loop(hours=12)
async def auto_backup():
    if not CFG["owner_id"] or not os.path.exists("levels.db"): return
    try:
        user = await bot.fetch_user(CFG["owner_id"])
        file = discord.File("levels.db")
        e = discord.Embed(title="📦 نسخة احتياطية تلقائية", description=f"تم حفظ نسخة من قاعدة البيانات", color=0x3498db)
        e.add_field(name="الحجم", value=f"`{os.path.getsize('levels.db')/1024:.1f} KB`", inline=True)
        e.add_field(name="التاريخ", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", inline=True)
        e.set_footer(text="احتفظ بالملف عشان تقدر تسوي!استعادة")
        await user.send(embed=e, file=file)
    except Exception as err: print(f"Auto backup error: {err}")

@bot.event
async def on_ready():
    await db_init();
    print(f'{bot.user}');
    weekly_top.start()
    auto_backup.start() # تشغيل النسخ التلقائي

@bot.event
async def on_member_join(m):
    if (datetime.now(timezone.utc)-m.created_at).days < 7:
        r = discord.utils.get(m.guild.roles, name=CFG["bad_role"][0]) or await m.guild.create_role(name=CFG["bad_role"][0], color=CFG["bad_role"][1])
        for ch in m.guild.channels: await ch.set_permissions(r, send_messages=False)
        await m.add_roles(r)
        if log:=discord.utils.get(m.guild.channels, name=CFG["log"]):
            e=discord.Embed(title="⚠️ حساب جديد مشبوه", color=0xe67e22, timestamp=datetime.now(timezone.utc))
            e.add_field(name="العضو", value=m.mention, inline=True)
            e.add_field(name="عمر الحساب", value=f"`{(datetime.now(timezone.utc)-m.created_at).days} يوم`", inline=True)
            e.add_field(name="الإجراء", value="تم إعطاؤه ميوت تلقائي", inline=False)
            e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
            await log.send(embed=e)
        return
    r = discord.utils.get(m.guild.roles, name=CFG["new_role"][0]) or await m.guild.create_role(name=CFG["new_role"][0], color=CFG["new_role"][1])
    await m.add_roles(r)
    if ch:=discord.utils.get(m.guild.channels, name=CFG["welcome"]):
        e=discord.Embed(title="🌟 عضو جديد نورتنا", description=f'**أهلاً وسهلاً {m.mention}**\nنورت **{m.guild.name}**\n\nتم إعطائك رول {r.mention}', color=0x2ecc71)
        e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
        e.add_field(name="رقم العضو", value=f'`#{m.guild.member_count}`', inline=True)
        e.add_field(name="تاريخ الإنضمام", value=f'<t:{int(m.joined_at.timestamp())}:R>', inline=True)
        e.set_footer(text="لا تنسى تقرأ القوانين 📜")
        e.timestamp = datetime.now(timezone.utc)
        await ch.send(embed=e)

@bot.event
async def on_member_remove(m):
    if ch:=discord.utils.get(m.guild.channels, name=CFG["bye"]):
        e=discord.Embed(title="💔 عضو غادرنا", description=f'**{m.name}** طلع من السيرفر\n\nالله يستر عليه وين ما راح', color=0xe74c3c)
        e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
        e.add_field(name="عدد الأعضاء الآن", value=f'`{m.guild.member_count}`', inline=True)
        e.add_field(name="مدة البقاء", value=f'<t:{int(m.joined_at.timestamp())}:R>' if m.joined_at else "غير معروف", inline=True)
        e.timestamp = datetime.now(timezone.utc)
        await ch.send(embed=e)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    if re.search(r'discord.(gg|com/invite)', msg.content.lower()) and not msg.author.guild_permissions.manage_messages:
        await msg.delete(); asyncio.create_task(temp_mute(msg.author, 300, "نشر رابط")); return
    if msg.mention_everyone and not msg.author.guild_permissions.mention_everyone:
        await msg.delete(); asyncio.create_task(temp_mute(msg.author, 600, "منشن everyone")); return
    if len(msg.mentions) >= 5 and not msg.author.guild_permissions.mention_everyone: await msg.delete(); return

    spam.setdefault(msg.author.id, []).append(msg.content)
    if len(spam[msg.author.id]) > 5: spam[msg.author.id].pop(0)
    if spam[msg.author.id].count(msg.content) >= 4 and not msg.author.guild_permissions.manage_messages: await msg.delete(); return

    gid, uid = str(msg.guild.id), str(msg.author.id)
    if uid not in xp_cd or (datetime.now(timezone.utc)-xp_cd[uid]).seconds>=60:
        xp_cd[uid] = datetime.now(timezone.utc)
        d = await get_data(gid, uid); xp,lvl,wxp = d["xp"]+1, d["level"], d["weekly_xp"]+1
        new_lvl = calc_lvl(xp)
        await save_data(gid, uid, xp, new_lvl, wxp)
        if new_lvl > lvl:
            if ch:=discord.utils.get(msg.guild.channels, name=CFG["lvl_up"]):
                bar, percent = make_progress_bar(xp, new_lvl, 10)
                e=discord.Embed(title="🎉 LEVEL UP!", description=f'**{msg.author.mention}** وصل **لفل {new_lvl}** 🚀', color=0xf1c40f)
                e.set_thumbnail(url=msg.author.display_avatar.url)
                e.add_field(name="📊 XP الحالي", value=f'`{xp:,}`', inline=True)
                e.add_field(name="⭐ اللفل الجديد", value=f'`{new_lvl}`', inline=True)
                e.add_field(name="🎯 لللفل الجاي", value=f'`{next_xp(new_lvl)-xp:,} XP`', inline=True)
                e.add_field(name="التقدم", value=f'`{bar}` {percent}%', inline=False)
                e.set_footer(text=msg.guild.name, icon_url=msg.guild.icon.url if msg.guild.icon else None)
                e.timestamp = datetime.now(timezone.utc)
                await ch.send(embed=e)
            if r:=await update_role(msg.author, new_lvl):
                await msg.channel.send(f"🎊 مبروك {msg.author.mention} حصلت على رول {r.mention}")

    for w in CFG["bad_words"]:
        if w in msg.content.lower():
            await msg.delete(); warns[msg.author.id] = warns.get(msg.author.id, 0) + 1
            if warns[msg.author.id] >= 3:
                asyncio.create_task(temp_mute(msg.author, 3600, "سب")); warns[msg.author.id] = 0
                await msg.channel.send(f"🔇 {msg.author.mention} ميوت ساعة بسبب السب المتكرر")
            else: await msg.channel.send(f"⚠️ {msg.author.mention} تحذير {warns[msg.author.id]}/3", delete_after=5)
            if log:=discord.utils.get(msg.guild.channels, name=CFG["log"]):
                e=discord.Embed(title="🚫 تم حذف رسالة سيئة", color=0xff0000, timestamp=msg.created_at)
                e.add_field(name="العضو", value=msg.author.mention, inline=True)
                e.add_field(name="التحذيرات", value=f"`{warns[msg.author.id]}/3`", inline=True)
                e.add_field(name="الكلمة المحظورة", value=f"||{w}||", inline=False)
                e.add_field(name="الرسالة", value=f"```{msg.content[:500]}```", inline=False)
                await log.send(embed=e)
            return

    if msg.content.lower() == "السلام عليكم": await msg.channel.send(f"وعليكم السلام ورحمة الله وبركاته {msg.author.mention} 🌹")
    elif msg.content.lower() == "صباح الخير": await msg.channel.send(f"صباح النور والسرور {msg.author.mention} ☀️")
    elif msg.content.lower() == "مساء الخير": await msg.channel.send(f"مساء الورد {msg.author.mention} 🌙")
    await bot.process_commands(msg)

@bot.command()
async def هلا(ctx): await ctx.send(f"هلا والله {ctx.author.mention} 👋")

@bot.command()
async def بنق(ctx):
    e=discord.Embed(title="🏓 البنق", description=f'**`{round(bot.latency*1000)}ms`**', color=0x2ecc71 if bot.latency<0.1 else 0xe67e22)
    await ctx.send(embed=e)

@bot.command()
async def يوزر(ctx, m: discord.Member=None):
    m=m or ctx.author; d=await get_data(str(ctx.guild.id), str(m.id))
    e=discord.Embed(title=f"📋 معلومات {m.name}", color=m.color if m.color.value else 0x3498db)
    e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
    e.add_field(name="👤 العضو", value=m.mention, inline=True)
    e.add_field(name="📅 دخل السيرفر", value=f'<t:{int(m.joined_at.timestamp())}:R>', inline=True)
    e.add_field(name="⚠️ التحذيرات", value=f'`{warns.get(m.id, 0)}/3`', inline=True)
    if d["xp"]>0:
        e.add_field(name="⭐ اللفل", value=f'`{d["level"]}`', inline=True)
        e.add_field(name="💎 XP الكلي", value=f'`{d["xp"]:,}/{next_xp(d["level"]):,}`', inline=True)
        e.add_field(name="📈 XP الأسبوع", value=f'`{d["weekly_xp"]:,}`', inline=True)
        bar, percent = make_progress_bar(d["xp"], d["level"], 10)
        e.add_field(name="التقدم للفل الجاي", value=f'`{bar}` {percent}%', inline=False)
    roles = [r.mention for r in m.roles if r.name!="@everyone"]
    e.add_field(name="🎭 الرولات", value=" ".join(roles) if roles else "لا يوجد", inline=False)
    e.set_footer(text=f"ID: {m.id}")
    e.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=e)

@bot.command()
async def لفل(ctx, m: discord.Member=None):
    m=m or ctx.author; d=await get_data(str(ctx.guild.id), str(m.id))
    if not d["xp"]: return await ctx.send(embed=discord.Embed(description=f"❌ {m.mention} ما عنده XP لحد الحين", color=0xe74c3c))
    e=discord.Embed(title=f"⭐ لفل {m.display_name}", color=0x3498db)
    e.set_thumbnail(url=m.display_avatar.url)
    e.add_field(name="اللفل", value=f'`{d["level"]}`', inline=True)
    e.add_field(name="XP", value=f'`{d["xp"]:,}/{next_xp(d["level"]):,}`', inline=True)
    e.add_field(name="باقي", value=f'`{next_xp(d["level"])-d["xp"]:,} XP`', inline=True)
    e.add_field(name="XP الأسبوع", value=f'`{d["weekly_xp"]:,}`', inline=True)
    bar, percent = make_progress_bar(d["xp"], d["level"], 15)
    e.add_field(name="التقدم", value=f'`{bar}` {percent}%', inline=False)
    e.set_footer(text=f"استخدم!توب لرؤية المتصدرين")
    await ctx.send(embed=e)

@bot.command()
async def توب(ctx):
    async with aiosqlite.connect('levels.db') as db:
        async with db.execute('SELECT user_id,xp,level FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT 10', (str(ctx.guild.id),)) as c: top=await c.fetchall()
    if not top: return await ctx.send(embed=discord.Embed(description="❌ مافي أحد عنده XP", color=0xe74c3c))
    e=discord.Embed(title=f"🏆 توب 10 في {ctx.guild.name}", description="**أكثر 10 أعضاء جمعوا XP**", color=0xf1c40f)
    e.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    medals = ["🥇", "🥈", "🥉"]
    desc = ""
    for i,(u,x,l) in enumerate(top,1):
        medal = medals[i-1] if i<=3 else f"**{i}.**"
        desc += f"{medal} <@{u}>\n└ لفل `{l}` • `{x:,} XP`\n\n"
    e.description = desc
    e.set_footer(text=f"استخدم!لفل @عضو لرؤية تفاصيل أي شخص")
    e.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=e)

@bot.command(name="توب_اسبوع")
async def توب_اسبوع(ctx):
    async with aiosqlite.connect('levels.db') as db:
        async with db.execute('SELECT user_id,weekly_xp,level FROM levels WHERE guild_id=? AND weekly_xp>0 ORDER BY weekly_xp DESC LIMIT 10', (str(ctx.guild.id),)) as c: top=await c.fetchall()
    if not top: return await ctx.send(embed=discord.Embed(title="😴 لا يوجد متفاعلين", description="مافي أحد جمع XP هذا الأسبوع", color=0x95a5a6))
    e=discord.Embed(title="🏆 توب 10 لهذا الأسبوع", description="**أكثر 10 أعضاء تفاعلاً خلال 7 أيام**", color=0xf1c40f)
    e.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    medals = ["🥇", "🥈", "🥉"]
    desc = ""
    for i,(u,x,l) in enumerate(top,1):
        medal = medals[i-1] if i<=3 else f"**{i}.**"
        desc += f"{medal} <@{u}>\n└ `{x:,} XP` • لفل `{l}`\n\n"
    e.description = desc
    e.set_footer(text="يتصفر كل جمعة الساعة 12 ظهراً")
    e.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def عط(ctx, m:discord.Member, a:int):
    if a<=0: return await ctx.send(embed=discord.Embed(description="❌ الكمية لازم أكبر من صفر", color=0xe74c3c))
    d=await get_data(str(ctx.guild.id), str(m.id)); xp,lvl,wxp=d["xp"]+a,d["level"],d["weekly_xp"]+a; new_lvl=calc_lvl(xp)
    await save_data(str(ctx.guild.id), str(m.id), xp, new_lvl, wxp)
    if new_lvl!=lvl: await update_role(m, new_lvl)
    e=discord.Embed(title="✅ تم إعطاء XP", description=f"تم إعطاء {m.mention} **{a:,} XP**", color=0x2ecc71)
    e.add_field(name="اللفل الحالي", value=f'`{new_lvl}`', inline=True)
    e.add_field(name="XP الكلي", value=f'`{xp:,}`', inline=True)
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(administrator=True)
async def خصم(ctx, m:discord.Member, a:int):
    if a<=0: return await ctx.send(embed=discord.Embed(description="❌ الكمية لازم أكبر من صفر", color=0xe74c3c))
    d=await get_data(str(ctx.guild.id), str(m.id))
    if not d["xp"]: return await ctx.send(embed=discord.Embed(description=f"❌ {m.mention} ما عنده XP أصلاً", color=0xe74c3c))
    xp,lvl,wxp=max(0,d["xp"]-a),d["level"],max(0,d["weekly_xp"]-a); new_lvl=calc_lvl(xp)
    await save_data(str(ctx.guild.id), str(m.id), xp, new_lvl, wxp)
    if new_lvl!=lvl: await update_role(m, new_lvl)
    e=discord.Embed(title="✅ تم خصم XP", description=f"تم خصم **{a:,} XP** من {m.mention}", color=0xe67e22)
    e.add_field(name="اللفل الحالي", value=f'`{new_lvl}`', inline=True)
    e.add_field(name="XP الكلي", value=f'`{xp:,}`', inline=True)
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def مسح(ctx, n:int): await ctx.channel.purge(limit=n+1); await ctx.send(embed=discord.Embed(description=f"✅ تم مسح `{n}` رسالة", color=0x2ecc71), delete_after=3)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def ميوت(ctx, m:discord.Member, t:int, *, reason="مافي سبب"):
    await temp_mute(m, t*60, reason)
    await ctx.send(embed=discord.Embed(title="🔇 تم إعطاء ميوت", description=f"{m.mention} لمدة `{t}` دقيقة\n**السبب:** {reason}", color=0xe74c3c))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def فك(ctx, m:discord.Member):
    r=discord.utils.get(ctx.guild.roles, name="Muted")
    if r: await m.remove_roles(r)
    await ctx.send(embed=discord.Embed(description=f"✅ تم فك الميوت عن {m.mention}", color=0x2ecc71))

@bot.command()
@commands.has_permissions(kick_members=True)
async def طرد(ctx, m:discord.Member, *, reason="مافي سبب"): await m.kick(reason=reason); await ctx.send(embed=discord.Embed(description=f"👢 تم طرد {m.mention}\n**السبب:** {reason}", color=0xe74c3c))

@bot.command()
@commands.has_permissions(ban_members=True)
async def باند(ctx, m:discord.Member, *, reason="مافي سبب"): await m.ban(reason=reason); await ctx.send(embed=discord.Embed(description=f"🔨 تم تبنيد {m.mention}\n**السبب:** {reason}", color=0x992d22))

@bot.command()
@commands.has_permissions(administrator=True)
async def قفل(ctx):
    for ch in ctx.guild.text_channels: await ch.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=discord.Embed(title="🔒 تم قفل السيرفر", description="للفتح استخدم `!فتح`", color=0xe74c3c))

@bot.command()
@commands.has_permissions(administrator=True)
async def فتح(ctx):
    for ch in ctx.guild.text_channels: await ch.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=discord.Embed(title="🔓 تم فتح السيرفر", color=0x2ecc71))

@bot.command()
@commands.has_permissions(kick_members=True)
async def تحذير(ctx, m:discord.Member, *, reason="مافي سبب"):
    warns[m.id]=warns.get(m.id,0)+1
    await ctx.send(embed=discord.Embed(description=f"⚠️ تم تحذير {m.mention} | `{warns[m.id]}/3`\n**السبب:** {reason}", color=0xe67e22))

@bot.command()
async def تحذيراتي(ctx): await ctx.send(embed=discord.Embed(description=f"⚠️ عندك `{warns.get(ctx.author.id,0)}` تحذير", color=0xe67e22))

@bot.command()
@commands.has_permissions(administrator=True)
async def مسح_تحذيرات(ctx, m:discord.Member):
    warns[m.id]=0
    await ctx.send(embed=discord.Embed(description=f"✅ تم مسح تحذيرات {m.mention}", color=0x2ecc71))

# === أوامر النسخة الاحتياطية ===
@bot.command()
@commands.has_permissions(administrator=True)
async def نسخة(ctx):
    """يرفع ملف levels.db كنسخة احتياطية"""
    try:
        if not os.path.exists("levels.db"):
            return await ctx.send(embed=discord.Embed(description="❌ ملف قاعدة البيانات ما انشئ لحد الحين", color=0xe74c3c))
        await ctx.send("📤 **جاري رفع النسخة الاحتياطية...**", file=discord.File("levels.db"))
        e=discord.Embed(title="✅ تم الرفع بنجاح", description="احفظ هذا الملف عندك.\n**للاستعادة:** ارفع الملف مع أمر `!استعادة`", color=0x2ecc71)
        e.add_field(name="حجم الملف", value=f"`{os.path.getsize('levels.db')/1024:.1f} KB`", inline=True)
        e.add_field(name="التاريخ", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", inline=True)
        await ctx.send(embed=e)
    except Exception as err:
        await ctx.send(embed=discord.Embed(description=f"❌ صار خطأ: `{err}`", color=0xe74c3c))

@bot.command()
@commands.has_permissions(administrator=True)
async def استعادة(ctx):
    """استرجع النسخة - ارفق ملف levels.db مع الأمر"""
    if not ctx.message.attachments:
        return await ctx.send(embed=discord.Embed(description="❌ لازم ترفق ملف `levels.db` مع الرسالة", color=0xe74c3c))
    attachment = ctx.message.attachments[0]
    if attachment.filename!= "levels.db":
        return await ctx.send(embed=discord.Embed(description="❌ اسم الملف لازم يكون `levels.db` بالضبط", color=0xe74c3c))
    await attachment.save("levels.db")
    await ctx.send(embed=discord.Embed(title="✅ تم الاستعادة", description="تم استرجاع النسخة الاحتياطية...\n🔄 جاري إعادة تشغيل البوت الحين", color=0x2ecc71))
    await asyncio.sleep(2)
    await bot.close() # Railway بيشغله تلقائي

@bot.command()
@commands.has_permissions(administrator=True)
async def نسخة_خاص(ctx):
    """يرسل نسخة احتياطية على الخاص فوراً"""
    try:
        if not os.path.exists("levels.db"):
            return await ctx.send(embed=discord.Embed(description="❌ ملف قاعدة البيانات ما انشئ لحد الحين", color=0xe74c3c))
        file = discord.File("levels.db")
        e = discord.Embed(title="📦 نسخة احتياطية", description="هذي نسخة من قاعدة البيانات", color=0x3498db)
        e.add_field(name="الحجم", value=f"`{os.path.getsize('levels.db')/1024:.1f} KB`", inline=True)
        await ctx.author.send(embed=e, file=file)
        await ctx.send(embed=discord.Embed(description="✅ تم الإرسال على الخاص", color=0x2ecc71))
    except: await ctx.send(embed=discord.Embed(description="❌ ما قدرت أرسل على الخاص. تأكد إنك فاتح الخاص", color=0xe74c3c))

@bot.command()
async def مساعدة(ctx):
    e=discord.Embed(title="📋 أوامر البوت", description="البادئة: `!`", color=0x3498db)
    e.add_field(name="🔹 عامة", value="`هلا` `بنق` `يوزر` `تحذيراتي`", inline=False)
    e.add_field(name="⭐ اللفل", value="`لفل` `توب_اسبوع` `عط @عضو رقم` `خصم @عضو رقم`", inline=False)
    e.add_field(name="🛡️ الإدارة", value="`مسح` `ميوت` `فك` `طرد` `باند` `تحذير` `قفل` `فتح` `مسح_تحذيرات`", inline=False)
    e.add_field(name="💾 النسخ الاحتياطي", value="`نسخة` `استعادة` `نسخة_خاص`", inline=False)
    e.add_field(name="⚙️ الحماية التلقائية", value="• حذف روابط + ميوت 5د\n• منع @everyone + ميوت 10د\n• فلتر سب + 3 تحذيرات = ميوت ساعة\n• منع السبام والمنشن الجماعي\n• نسخة تلقائية كل 12 ساعة بالخاص", inline=False)
    e.set_footer(text="بوت متكامل للحماية واللفل")
    e.timestamp = datetime.now(timezone.utc)
    await ctx.send(embed=e)

bot.run(TOKEN)
