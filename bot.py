import discord
from discord.ext import commands, tasks
import os
import asyncio
import random
from datetime import datetime, timedelta
import aiosqlite
import pytz
import re

TOKEN = os.getenv("TOKEN")
اسم_روم_الترحيب = "شات-العام"
اسم_روم_اللوق = "المخالفات"
اسم_روم_الوداع = "شات-العام"
اسم_روم_اللفل = "لفل-اب"
اسم_روم_توب_الاسبوع = "توب-الاسبوع"
رول_الاعضاء_الجدد = ["الأعضاء الجدد", 0x95a5a6]
رول_غير_موثق = ["غير موثق", 0xe74c3c]
رولات_اللفل = {1: ["مبتدئ", 0x95a5a6], 5: ["نشيط", 0x3498db], 10: ["متفاعل", 0x2ecc71], 20: ["أسطورة", 0xf1c40f], 50: ["VIP", 0xe74c3c]}
الكلمات_المسيئة = ["سب1", "سب2", "كلمة_ممنوعة", "يا حيوان", "ياحيوان", "يا كلب", "ياكلب", "يامريض", "كس امك", "كسامك", "كل زق", "كلزق"]
التحذيرات = {}
كولداون_xp = {}
رسائل_السبام = {}

async def init_db():
    async with aiosqlite.connect('levels.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS levels (guild_id TEXT, user_id TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0, weekly_xp INTEGER DEFAULT 0, last_reset TEXT, PRIMARY KEY (guild_id, user_id))')
        await db.commit()

async def جلب_بيانات_العضو(guild_id, user_id):
    async with aiosqlite.connect('levels.db') as db:
        async with db.execute('SELECT xp, level, weekly_xp FROM levels WHERE guild_id =? AND user_id =?', (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row: return {"xp": row[0], "level": row[1], "weekly_xp": row[2]}
            return {"xp": 0, "level": 0, "weekly_xp": 0}

async def تحديث_بيانات_العضو(guild_id, user_id, xp, level, weekly_xp):
    async with aiosqlite.connect('levels.db') as db:
        await db.execute('INSERT INTO levels (guild_id, user_id, xp, level, weekly_xp, last_reset) VALUES (?,?,?,?,?,?) ON CONFLICT(guild_id, user_id) DO UPDATE SET xp =?, level =?, weekly_xp =?', (guild_id, user_id, xp, level, weekly_xp, datetime.now().strftime("%Y-%m-%d"), xp, level, weekly_xp))
        await db.commit()

async def جلب_التوب(guild_id, limit=10):
    async with aiosqlite.connect('levels.db') as db:
        async with db.execute('SELECT user_id, xp, level FROM levels WHERE guild_id =? ORDER BY xp DESC LIMIT?', (guild_id, limit)) as cursor:
            return await cursor.fetchall()

async def جلب_توب_الاسبوع(guild_id, limit=10):
    async with aiosqlite.connect('levels.db') as db:
        async with db.execute('SELECT user_id, weekly_xp, level FROM levels WHERE guild_id =? AND weekly_xp > 0 ORDER BY weekly_xp DESC LIMIT?', (guild_id, limit)) as cursor:
            return await cursor.fetchall()

async def تصفير_الاسبوعي(guild_id):
    async with aiosqlite.connect('levels.db') as db:
        await db.execute('UPDATE levels SET weekly_xp = 0 WHERE guild_id =?', (guild_id,))
        await db.commit()

def حساب_xp_اللفل(xp):
    lvl = 0
    while xp >= (50 * (lvl ** 2) + 50 * lvl): lvl += 1
    return lvl - 1

def حساب_xp_للفل_التالي(lvl): return 50 * (lvl ** 2) + 50 * lvl

async def تحديث_رول_اللفل(member, lvl_جديد):
    رولات_للحذف = []
    for lvl, role_data in رولات_اللفل.items():
        role_name = role_data[0]
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role and role in member.roles: رولات_للحذف.append(role)
    if رولات_للحذف: await member.remove_roles(*رولات_للحذف, reason="تحديث رول اللفل")
    رول_مناسب = None
    اعلى_لفل = 0
    for lvl, role_data in رولات_اللفل.items():
        if lvl_جديد >= lvl and lvl > اعلى_لفل: اعلى_لفل = lvl; رول_مناسب = role_data
    if رول_مناسب:
        role_name, role_color = رول_مناسب
        role = discord.utils.get(member.guild.roles, name=role_name)
        if not role: role = await member.guild.create_role(name=role_name, color=role_color, reason="رول لفل تلقائي")
        await member.add_roles(role, reason=f"وصل لفل {lvl_جديد}")
        return role
    return None

async def ميوت_مؤقت(member, المدة_ثواني, السبب):
    role = discord.utils.get(member.guild.roles, name="Muted")
    if not role:
        role = await member.guild.create_role(name="Muted")
        for ch in member.guild.channels: await ch.set_permissions(role, send_messages=False, add_reactions=False)
    await member.add_roles(role, reason=السبب)
    await asyncio.sleep(المدة_ثواني)
    try: await member.remove_roles(role, reason="انتهاء الميوت المؤقت")
    except: pass

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@tasks.loop(time=datetime.strptime("12:00", "%H:%M").time())
async def نشر_توب_الاسبوع():
    if datetime.now(pytz.timezone('Asia/Riyadh')).weekday()!= 4: return
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name=اسم_روم_توب_الاسبوع)
        if not channel: continue
        top_users = await جلب_توب_الاسبوع(str(guild.id), 10)
        if not top_users:
            await channel.send("مافي أحد تفاعل هذا الأسبوع 😴")
            await تصفير_الاسبوعي(str(guild.id))
            continue
        embed = discord.Embed(title="🏆 توب 10 لهذا الأسبوع", description="أكثر 10 أشخاص جمعوا XP خلال 7 أيام", color=0xf1c40f)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        desc = ""
        for i, (user_id, weekly_xp, level) in enumerate(top_users, 1):
            try:
                user = await bot.fetch_user(int(user_id))
                desc += f"**{i}.** {user.mention} - `{weekly_xp} XP` - لفل `{level}`\n"
            except: continue
        embed.description = desc if desc else "مافي بيانات"
        embed.set_footer(text=f"يتصفر كل يوم جمعة الساعة 12 الظهر")
        await channel.send(embed=embed)
        await تصفير_الاسبوعي(str(guild.id))

@bot.event
async def on_ready():
    await init_db()
    print(f'تم تسجيل الدخول باسم {bot.user}')
    await bot.change_presence(activity=discord.Game(name="!مساعدة | حماية 24/7"))
    نشر_توب_الاسبوع.start()

@bot.event
async def on_member_join(member):
    عمر_الحساب = (datetime.utcnow() - member.created_at).days
    if عمر_الحساب < 7:
        role_name, role_color = رول_غير_موثق
        role = discord.utils.get(member.guild.roles, name=role_name)
        if not role:
            role = await member.guild.create_role(name=role_name, color=role_color, reason="رول الحسابات الجديدة")
            for ch in member.guild.channels: await ch.set_permissions(role, send_messages=False, add_reactions=False)
        await member.add_roles(role)
        روم_اللوق = discord.utils.get(member.guild.channels, name=اسم_روم_اللوق)
        if روم_اللوق:
            embed = discord.Embed(title="⚠️ دخل حساب جديد", color=0xe67e22, timestamp=datetime.utcnow())
            embed.add_field(name="العضو", value=member.mention, inline=True)
            embed.add_field(name="عمر الحساب", value=f"`{عمر_الحساب} يوم`", inline=True)
            embed.add_field(name="الحالة", value="تم إعطاؤه ميوت تلقائي", inline=False)
            await روم_اللوق.send(embed=embed)
        return
    role_name, role_color = رول_الاعضاء_الجدد
    role = discord.utils.get(member.guild.roles, name=role_name)
    if not role: role = await member.guild.create_role(name=role_name, color=role_color, reason="رول تلقائي للأعضاء الجدد")
    await member.add_roles(role)
    channel = discord.utils.get(member.guild.channels, name=اسم_روم_الترحيب)
    if channel:
        embed = discord.Embed(title="عضو جديد نورتنا 🌟", description=f'حياك الله {member.mention} في **{member.guild.name}**\nتم إعطائك رول {role.mention}', color=0x2ecc71)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="أنت العضو رقم", value=f'`{member.guild.member_count}`', inline=True)
        embed.set_footer(text="لا تنسى تقرأ القوانين")
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.channels, name=اسم_روم_الوداع)
    if channel:
        embed = discord.Embed(title="عضو غادرنا 💔", description=f'**{member.name}** طلع من السيرفر\nالله يستر عليه وين ما راح', color=0xe74c3c)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="عدد الأعضاء الآن", value=f'`{member.guild.member_count}`', inline=True)
        await channel.send(embed=embed)
    روم_اللوق = discord.utils.get(member.guild.channels, name=اسم_روم_اللوق)
    if روم_اللوق:
        embed = discord.Embed(title="سجل مغادرة 📤", color=0x95a5a6, timestamp=datetime.utcnow())
        embed.add_field(name="العضو", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="الأيدي", value=f"`{member.id}`", inline=True)
        embed.add_field(name="دخل السيرفر", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "غير معروف", inline=False)
        await روم_اللوق.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if re.search(r'discord\.gg/|discord\.com/invite/|discordapp\.com/invite/', message.content.lower()):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ممنوع نشر روابط السيرفرات 🚫 ميوت 5 دقايق", delete_after=5)
            asyncio.create_task(ميوت_مؤقت(message.author, 300, "نشر رابط"))
            روم_اللوق = discord.utils.get(message.guild.channels, name=اسم_روم_اللوق)
            if روم_اللوق:
                embed = discord.Embed(title="تم حذف رابط 🚫", color=0xe74c3c, timestamp=datetime.utcnow())
                embed.add_field(name="العضو", value=message.author.mention, inline=True)
                embed.add_field(name="القناة", value=message.channel.mention, inline=True)
                embed.add_field(name="الرابط", value=f"||{message.content}||", inline=False)
                await روم_اللوق.send(embed=embed)
            return
    if message.mention_everyone:
        if not message.author.guild_permissions.mention_everyone:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ممنوع منشن @everyone 🚫 ميوت 10 دقايق")
            asyncio.create_task(ميوت_مؤقت(message.author, 600, "منشن everyone"))
            return
    if len(message.mentions) >= 5:
        if not message.author.guild_permissions.mention_everyone:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ممنوع تمنشن أكثر من 5 أشخاص 🚫", delete_after=5)
            return
    if message.author.id not in رسائل_السبام: رسائل_السبام[message.author.id] = []
    رسائل_السبام[message.author.id].append(message.content)
    if len(رسائل_السبام[message.author.id]) > 5: رسائل_السبام[message.author.id].pop(0)
    if رسائل_السبام[message.author.id].count(message.content) >= 4:
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.channel.send(f"{message.author.mention} لا تكرر الرسالة 🚫", delete_after=5)
            return
    user_id = str(message.author.id)
    guild_id = str(message.guild.id)
    if user_id in كولداون_xp:
        if (datetime.utcnow() - كولداون_xp[user_id]).seconds < 60: pass
        else: كولداون_xp[user_id] = datetime.utcnow()
    else: كولداون_xp[user_id] = datetime.utcnow()
    بيانات = await جلب_بيانات_العضو(guild_id, user_id)
    xp_قديم = بيانات["xp"]
    lvl_قديم = بيانات["level"]
    weekly_xp_قديم = بيانات["weekly_xp"]
    xp_جديد = xp_قديم + 1
    weekly_xp_جديد = weekly_xp_قديم + 1
    lvl_جديد = حساب_xp_اللفل(xp_جديد)
    await تحديث_بيانات_العضو(guild_id, user_id, xp_جديد, lvl_جديد, weekly_xp_جديد)
    if lvl_جديد > lvl_قديم:
        channel = discord.utils.get(message.guild.channels, name=اسم_روم_اللفل)
        if channel:
            embed = discord.Embed(title="🎉 لفل اب!", description=f"{message.author.mention} وصل لفل **{lvl_جديد}**", color=0xf1c40f)
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.add_field(name="XP الحالي", value=f"`{xp_جديد}`", inline=True)
            embed.add_field(name="اللفل الجديد", value=f"`{lvl_جديد}`", inline=True)
            embed.add_field(name="لللفل الجاي", value=f"`{حساب_xp_للفل_التالي(lvl_جديد) - xp_جديد} XP`", inline=True)
            embed.set_footer(text=f"{message.guild.name}", icon_url=message.guild.icon.url if message.guild.icon else None)
            await channel.send(embed=embed)
        new_role = await تحديث_رول_اللفل(message.author, lvl_جديد)
        if new_role: await message.channel.send(f"مبروك {message.author.mention} حصلت على رول {new_role.mention} 🌟")
    for كلمة in الكلمات_المسيئة:
        if كلمة in message.content.lower():
            await message.delete()
            user_id_int = message.author.id
            if user_id_int not in التحذيرات: التحذيرات[user_id_int] = 0
            التحذيرات[user_id_int] += 1
            if التحذيرات[user_id_int] >= 3:
                role = discord.utils.get(message.guild.roles, name="Muted")
                if not role:
                    role = await message.guild.create_role(name="Muted")
                    for ch in message.guild.channels: await ch.set_permissions(role, send_messages=False)
                await message.author.add_roles(role)
                await message.channel.send(f"{message.author.mention} اخذت ميوت ساعة بسبب السب المتكرر 🔇")
                التحذيرات[user_id_int] = 0
                await asyncio.sleep(3600)
                await message.author.remove_roles(role)
            else: await message.channel.send(f"{message.author.mention} تحذير {التحذيرات[user_id_int]}/3 لا تسب 🚫", delete_after=5)
            روم_اللوق = discord.utils.get(message.guild.channels, name=اسم_روم_اللوق)
            if روم_اللوق:
                embed = discord.Embed(title="تم حذف رسالة سيئة 🚫", color=0xff0000, timestamp=message.created_at)
                embed.add_field(name="العضو", value=f"{message.author.mention}", inline=True)
                embed.add_field(name="تحذيراته", value=f"{التحذيرات[user_id_int]}/3", inline=True)
                embed.add_field(name="الكلمة", value=f"||{كلمة}||", inline=False)
                embed.add_field(name="الرسالة", value=f"```{message.content}```", inline=False)
                await روم_اللوق.send(embed=embed)
            return
    msg = message.content.lower()
    if msg == "السلام عليكم": await message.channel.send(f"وعليكم السلام ورحمة الله وبركاته {message.author.mention}")
    elif msg == "صباح الخير": await message.channel.send(f"صباح النور {message.author.mention} ☀️")
    elif msg == "مساء الخير": await message.channel.send(f"مساء النور {message.author.mention} 🌙")
    await bot.process_commands(message)

@bot.command()
async def هلا(ctx): await ctx.send(f"هلا والله {ctx.author.mention} 👋")

@bot.command()
async def بنق(ctx): await ctx.send(f"البنق: `{round(bot.latency * 1000)}ms` 🏓")

@bot.command()
async def سيرفر(ctx):
    embed = discord.Embed(title=f"معلومات {ctx.guild.name}", color=0x3498db)
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.add_field(name="الأعضاء", value=f"`{ctx.guild.member_count}`", inline=True)
    embed.add_field(name="البوتات", value=f"`{len([m for m in ctx.guild.members if m.bot])}`", inline=True)
    embed.add_field(name="الرولات", value=f"`{len(ctx.guild.roles)}`", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def يوزر(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"معلومات {member.name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="دخل السيرفر", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="تحذيراته", value=f"`{التحذيرات.get(member.id, 0)}`", inline=True)
    بيانات = await جلب_بيانات_العضو(str(ctx.guild.id), str(member.id))
    if بيانات["xp"] > 0:
        embed.add_field(name="اللفل", value=f"`{بيانات['level']}`", inline=True)
        embed.add_field(name="XP", value=f"`{بيانات['xp']}/{حساب_xp_للفل_التالي(بيانات['level'])}`", inline=True)
        embed.add_field(name="XP الأسبوع", value=f"`{بيانات['weekly_xp']}`", inline=True)
    roles = [role.mention for role in member.roles if role.name!= "@everyone"]
    embed.add_field(name="الرولات", value=" ".join(roles) if roles else "لا يوجد", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="لفل")
async def لفل(ctx, member: discord.Member = None):
    member = member or ctx.author
    بيانات = await جلب_بيانات_العضو(str(ctx.guild.id), str(member.id))
    if بيانات["xp"] == 0: await ctx.send(f"{member.mention} ما عنده XP لحد الحين"); return
    xp = بيانات["xp"]
    lvl = بيانات["level"]
    xp_التالي = حساب_xp_للفل_التالي(lvl)
    embed = discord.Embed(title=f"لفل {member.name}", color=0x3498db)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="اللفل", value=f"`{lvl}`", inline=True)
    embed.add_field(name="XP", value=f"`{xp}/{xp_التالي}`", inline=True)
    embed.add_field(name="باقي", value=f"`{xp_التالي - xp} XP`", inline=True)
    embed.add_field(name="XP الأسبوع", value=f"`{بيانات['weekly_xp']}`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="توب")
async def توب(ctx):
    top_users = await جلب_التوب(str(ctx.guild.id), 10)
    if not top_users: await ctx.send("مافي أحد عنده XP"); return
    embed = discord.Embed(title=f"🏆 توب 10 في {ctx.guild.name}", color=0xf1c40f)
    desc = ""
    for i, (user_id, xp, level) in enumerate(top_users, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            desc += f"**{i}.** {user.name} - لفل `{level}` - `{xp} XP`\n"
        except: continue
    embed.description = desc if desc else "مافي بيانات"
    await ctx.send(embed=embed)

@bot.command(name="توب_اسبوع")
async def توب_اسبوع(ctx):
    top_users = await جلب_توب_الاسبوع(str(ctx.guild.id), 10)
    if not top_users: await ctx.send("مافي أحد تفاعل هذا الأسبوع 😴"); return
    embed = discord.Embed(title=f"🏆 توب 10 لهذا الأسبوع", color=0xf1c40f)
    desc = ""
    for i, (user_id, weekly_xp, level) in enumerate(top_users, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            desc += f"**{i}.** {user.name} - `{weekly_xp} XP` - لفل `{level}`\n"
        except: continue
    embed.description = desc if desc else "مافي بيانات"
    embed.set_footer(text="يتصفر كل يوم جمعة الساعة 12 الظهر")
    await ctx.send(embed=embed)

@bot.command(name="عط")
@commands.has_permissions(manage_messages=True)
async def عط(ctx, member: discord.Member, amount: int):
    if amount <= 0: await ctx.send("الكمية لازم أكبر من صفر ❌"); return
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    بيانات = await جلب_بيانات_العضو(guild_id, user_id)
    xp_قديم = بيانات["xp"]
    lvl_قديم = بيانات["level"]
    weekly_xp_قديم = بيانات["weekly_xp"]
    xp_جديد = xp_قديم + amount
    weekly_xp_جديد = weekly_xp_قديم + amount
    lvl_جديد = حساب_xp_اللفل(xp_جديد)
    await تحديث_بيانات_العضو(guild_id, user_id, xp_جديد, lvl_جديد, weekly_xp_جديد)
    if lvl_جديد!= lvl_قديم:
        if lvl_جديد > lvl_قديم:
            channel = discord.utils.get(ctx.guild.channels, name=اسم_روم_اللفل)
            if channel:
                embed = discord.Embed(title="🎉 لفل اب!", description=f"{member.mention} وصل لفل **{lvl_جديد}**", color=0xf1c40f)
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="XP الحالي", value=f"`{xp_جديد}`", inline=True)
                embed.add_field(name="اللفل الجديد", value=f"`{lvl_جديد}`", inline=True)
                embed.add_field(name="لللفل الجاي", value=f"`{حساب_xp_للفل_التالي(lvl_جديد) - xp_جديد} XP`", inline=True)
                await channel.send(embed=embed)
        new_role = await تحديث_رول_اللفل(member, lvl_جديد)
        if new_role and lvl_جديد > lvl_قديم: await ctx.channel.send(f"مبروك {member.mention} حصلت على رول {new_role.mention} 🌟")
    await ctx.send(f"✅ تم إعطاء {member.mention} **{amount} XP**\nلفله الحين: `{lvl_جديد}` | XP: `{xp_جديد}`")

@bot.command(name="خصم")
@commands.has_permissions(administrator=True)
async def خصم(ctx, member: discord.Member, amount: int):
    if amount <= 0: await ctx.send("الكمية لازم أكبر من صفر ❌"); return
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    بيانات = await جلب_بيانات_العضو(guild_id, user_id)
    if بيانات["xp"] == 0: await ctx.send(f"{member.mention} ما عنده XP أصلاً ❌"); return
    xp_قديم = بيانات["xp"]
    lvl_قديم = بيانات["level"]
    weekly_xp_قديم = بيانات["weekly_xp"]
    xp_جديد = max(0, xp_قديم - amount)
    weekly_xp_جديد = max(0, weekly_xp_قديم - amount)
    lvl_جديد = حساب_xp_اللفل(xp_جديد)
    await تحديث_بيانات_العضو(guild_id, user_id, xp_جديد, lvl_جديد, weekly_xp_جديد)
    if lvl_جديد!= lvl_قديم: await تحديث_رول_اللفل(member, lvl_جديد)
    await ctx.send(f"✅ تم خصم **{amount} XP** من {member.mention}\nلفله الحين: `{lvl_جديد}` | XP: `{xp_جديد}`")

@عط.error
@خصم.error
async def xp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions): await ctx.send("ما عندك صلاحية ❌ تحتاج إدارة الرسائل للأمر `عط` وأدمن للأمر `خصم`")
    elif isinstance(error, commands.MissingRequiredArgument): await ctx.send("الاستخدام: `!عط @عضو 100` أو `!خصم @عضو 100`")
    elif isinstance(error, commands.BadArgument): await ctx.send("تأكد أنك منشنت العضو وكتبت رقم صحيح")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def مسح(ctx, عدد: int):
    await ctx.channel.purge(limit=عدد + 1)
    await ctx.send(f"تم مسح `{عدد}` رسالة ✅", delete_after=3)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def ميوت(ctx, member: discord.Member, وقت: int, *, السبب="مافي سبب"):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for ch in ctx.guild.channels: await ch.set_permissions(role, send_messages=False)
    await member.add_roles(role)
    await ctx.send(f"تم اعطاء {member.mention} ميوت لمدة {وقت} دقيقة | السبب: {السبب} 🔇")
    await asyncio.sleep(وقت * 60)
    await member.remove_roles(role)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def فك(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(role)
    await ctx.send(f"تم فك الميوت عن {member.mention} ✅")

@bot.command()
@commands.has_permissions(kick_members=True)
async def طرد(ctx, member: discord.Member, *, السبب="مافي سبب"):
    await member.kick(reason=السبب)
    await ctx.send(f"تم طرد {member.mention} | السبب: {السبب} 👢")

@bot.command()
@commands.has_permissions(ban_members=True)
async def باند(ctx, member: discord.Member, *, السبب="مافي سبب"):
    await member.ban(reason=السبب)
    await ctx.send(f"تم تبنيد {member.mention} | السبب: {السبب} 🔨")

@bot.command()
@commands.has_permissions(administrator=True)
async def قفل(ctx):
    for channel in ctx.guild.text_channels: await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 تم قفل السيرفر كامل | للفتح استخدم `!فتح`")
    روم_اللوق = discord.utils.get(ctx.guild.channels, name=اسم_روم_اللوق)
    if روم_اللوق:
        embed = discord.Embed(title="🔒 تم تفعيل القفل", color=0xe74c3c, timestamp=datetime.utcnow())
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        await روم_اللوق.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def فتح(ctx):
    for channel in ctx.guild.text_channels: await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 تم فتح السيرفر كامل")
    روم_اللوق = discord.utils.get(ctx.guild.channels, name=اسم_روم_اللوق)
    if روم_اللوق:
        embed = discord.Embed(title="🔓 تم فك القفل", color=0x2ecc71, timestamp=datetime.utcnow())
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        await روم_اللوق.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def توثيق(ctx, member: discord.Member):
    role_name, _ = رول_غير_موثق
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ تم توثيق {member.mention}")
        role_name_new, role_color_new = رول_الاعضاء_الجدد
        role_new = discord.utils.get(ctx.guild.roles, name=role_name_new)
        if not role_new: role_new = await ctx.guild.create_role(name=role_name_new, color=role_color_new)
        await member.add_roles(role_new)
    else: await ctx.send("❌ العضو موثق أصلاً أو ما عليه رول غير موثق")

@bot.command()
@commands.has_permissions(kick_members=True)
async def تحذير(ctx, member: discord.Member, *, السبب="مافي سبب"):
    user_id = member.id
    if user_id not in التحذيرات: التحذيرات[user_id] = 0
    التحذيرات[user_id] += 1
    await ctx.send(f"تم تحذير {member.mention} | {التحذيرات[user_id]}/3 | السبب: {السبب} ⚠️")

@bot.command()
async def تحذيراتي(ctx): await ctx.send(f"عندك `{التحذيرات.get(ctx.author.id, 0)}` تحذير ⚠️")

@bot.command()
@commands.has_permissions(administrator=True)
async def مسح_تحذيرات(ctx, member: discord.Member):
    التحذيرات[member.id] = 0
    await ctx.send(f"تم مسح تحذيرات {member.mention} ✅")

@bot.command(name="سوي_رول")
@commands.has_permissions(administrator=True)
async def سوي_رول(ctx, اسم: str, لون: str = "ابيض"):
    الوان = {"احمر": 0xff0000, "اخضر": 0x00ff00, "ازرق": 0x0000ff, "اصفر": 0xffff00, "بنفسجي": 0x9b59b6, "برتقالي": 0xe67e22, "وردي": 0xff69b4, "ابيض": 0xffffff, "اسود": 0x000000, "رمادي": 0x95a5a6}
    لون_الرول = الوان.get(لون, 0x99aab5)
    رول = await ctx.guild.create_role(name=اسم, color=لون_الرول)
    await ctx.send(f"تم إنشاء رول {رول.mention} باللون {لون} ✅")

@bot.command(name="رول")
@commands.has_permissions(manage_roles=True)
async def رول(ctx, member: discord.Member, *, اسم_الرول):
    role = discord.utils.get(ctx.guild.roles, name=اسم_الرول)
    if not role: await ctx.send("❌ الرول مو موجود"); return
    if role in member.roles: await ctx.send(f"❌ {member.mention} عنده الرول أصلاً"); return
    await member.add_roles(role)
    await ctx.send(f"تم إعطاء {member.mention} رول {role.mention} ✅")

@bot.command(name="شيل_رول")
@commands.has_permissions(manage_roles=True)
async def شيل_رول(ctx, member: discord.Member, *, اسم_الرول):
    role = discord.utils.get(ctx.guild.roles, name=اسم_الرول)
    if not role: await ctx.send("❌ الرول مو موجود"); return
    if role not in member.roles: await ctx.send(f"❌ {member.mention} ما عنده الرول أصلاً"); return
    await member.remove_roles(role)
    await ctx.send(f"تم إزالة رول {role.mention} من {member.mention} ✅")

@bot.command(name="رولات")
async def رولات(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name!= "@everyone"]
    embed = discord.Embed(title=f"رولات {member.name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="الرولات", value=" ".join(roles) if roles else "لا يوجد", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def نسخة(ctx):
    embed = discord.Embed(title="معلومات البوت", color=0x3498db)
    embed.add_field(name="الإصدار", value="`v2.0`", inline=True)
    embed.add_field(name="المكتبة", value="`discord.py`", inline=True)
    embed.add_field(name="المميزات", value="XP + حماية + رولات تلقائية + توب أسبوعي", inline=False)
    embed.set_footer(text="بوت متكامل للسيرفرات العربية")
    await ctx.send(embed=embed)

@bot.command()
async def مساعدة(ctx):
    embed = discord.Embed(title="📋 أوامر البوت", color=0x3498db, description="البادئة: `!`")
    embed.add_field(name="🔹 أوامر عامة", value="`هلا` `بنق` `سيرفر` `يوزر` `تحذيراتي` `نسخة`", inline=False)
    embed.add_field(name="⭐ أوامر اللفل", value="`لفل` `توب` `توب_اسبوع` `عط @عضو رقم` `خصم @عضو رقم`", inline=False)
    embed.add_field(name="🛡️ أوامر الإدارة", value="`مسح` `ميوت` `فك` `طرد` `باند` `تحذير` `مسح_تحذيرات` `قفل` `فتح` `توثيق`", inline=False)
    embed.add_field(name="🎭 أوامر الرولات", value="`سوي_رول` `رول @عضو اسم` `شيل_رول @عضو اسم` `رولات`", inline=False)
    embed.add_field(name="⚙️ الحماية التلقائية", value="• حذف روابط الديسكورد + ميوت 5د\n• منع @everyone + ميوت 10د\n• منع سبام المكرر\n• منع منشن 5+ أشخاص\n• ميوت الحسابات الجديدة أقل من 7 أيام\n• فلتر سب + 3 تحذيرات = ميوت ساعة", inline=False)
    embed.add_field(name="📊 نظام اللفل", value="• +1 XP كل رسالة مع كولداون 60ث\n• رولات تلقائية: مبتدئ لفل1، نشيط لفل5، متفاعل لفل10، أسطورة لفل20، VIP لفل50\n• توب أسبوعي كل جمعة 12 الظهر", inline=False)
    embed.add_field(name="💬 ردود تلقائية", value="`السلام عليكم` `صباح الخير` `مساء الخير`", inline=False)
    embed.set_footer(text="كل المخالفات تتسجل في روم المخالفات")
    await ctx.send(embed=embed)

bot.run(TOKEN)
