import discord
from discord.ext import commands
import random
from datetime import datetime
import os

# --- الإعدادات ---
اسم_روم_الشات_العام = "شات-العام"
اسم_روم_المخالفات = "المخالفات"
اسم_روم_اللفل = "لفل-اب"
اسم_روم_اوامر_البوت = "اوامر-البوت"

كلمات_ممنوعة = ["سب1", "سب2", "يا حمار", "كلب"]
ايدي_المالك = 123456789012345678 # حط ايدي حسابك هنا

رولات_اللفل = {
    1: ["مبتدئ", 0x95a5a6],
    5: ["نشيط", 0x3498db],
    10: ["متفاعل", 0x2ecc71],
    20: ["أسطورة", 0xf1c40f],
    50: ["VIP", 0xe74c3c]
}

# --- الردود التلقائية ---
الردود_التلقائية = {
    "السلام عليكم": ["وعليكم السلام ورحمة الله", "هلا والله وعليكم السلام"],
    "كيفك": ["بخير دامك بخير", "الحمدلله تمام", "بخير يا وحش"],
    "بوت": ["نعم يا قلبي؟", "عيون البوت", "آمرني"],
    "تصبح على خير": ["وانت من اهله", "تلاقي الخير", "نوم العوافي"]
}

# --- تخزين البيانات ---
التحذيرات = {} # {user_id: عدد_التحذيرات}
المستخدمين_XP = {} # {user_id: {"xp": 0, "level": 0}}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- دالة حساب اللفل ---
def احسب_لفل(xp):
    return int(xp ** (1/3.5))

def احسب_الاكس_بي_المطلوب(level):
    return int((level + 1) ** 3.5)

# --- دالة التحقق من اللفل اب + انشاء الرول ---
async def check_level_up(ctx, user_id):
    user_data = المستخدمين_XP.get(user_id, {"xp": 0, "level": 0})
    old_level = user_data["level"]
    new_level = احسب_لفل(user_data["xp"])

    if new_level > old_level:
        المستخدمين_XP[user_id]["level"] = new_level
        روم_اللفل = discord.utils.get(ctx.guild.channels, name=اسم_روم_اللفل)
        if not روم_اللفل:
            روم_اللفل = ctx.channel

        embed = discord.Embed(title="لفل اب! 🎉", color=0x00ff00)
        embed.description = f"{ctx.author.mention} وصل لفل **{new_level}**"
        await روم_اللفل.send(embed=embed)

        # --- إعطاء الرول أو إنشاؤه ---
        for level, (role_name, color) in sorted(رولات_اللفل.items(), reverse=True):
            if new_level >= level:
                رول = discord.utils.get(ctx.guild.roles, name=role_name)

                if not رول:
                    try:
                        رول = await ctx.guild.create_role(name=role_name, color=color, reason="رول لفل تلقائي")
                        await روم_اللفل.send(f"✨ تم إنشاء رول {رول.mention} تلقائياً")
                    except discord.Forbidden:
                        return await روم_اللفل.send("❌ ما عندي صلاحية أنشئ رولات. فعل صلاحية `إدارة الأدوار` للبوت")
                    except Exception as e:
                        return await روم_اللفل.send(f"❌ خطأ بإنشاء الرول: {e}")

                if رول not in ctx.author.roles:
                    try:
                        await ctx.author.add_roles(رول)
                        await روم_اللفل.send(f"🎊 {ctx.author.mention} حصل على رول {رول.mention}")
                    except discord.Forbidden:
                        await روم_اللفل.send("❌ ما عندي صلاحية أعطي رولات. تأكد أن رولي فوق رولات اللفل")
                    except Exception as e:
                        await روم_اللفل.send(f"❌ صار خطأ بإعطاء الرول: {e}")
                break

# --- Events ---
@bot.event
async def on_ready():
    print(f'تم تسجيل الدخول باسم {bot.user}')
    print('------')

@bot.event
async def on_member_join(member):
    روم_المخالفات = discord.utils.get(member.guild.channels, name=اسم_روم_المخالفات)
    if روم_المخالفات:
        embed = discord.Embed(title="سجل دخول عضو جديد 📥", color=0x2ecc71, timestamp=datetime.utcnow())
        embed.add_field(name="العضو", value=f"{member.mention}", inline=True)
        embed.add_field(name="الأيدي", value=f"`{member.id}`", inline=True)
        embed.add_field(name="تاريخ إنشاء الحساب", value=member.created_at.strftime("%Y-%m-%d"), inline=False)
        await روم_المخالفات.send(embed=embed)

@bot.event
async def on_member_remove(member):
    روم_المخالفات = discord.utils.get(member.guild.channels, name=اسم_روم_المخالفات)
    if روم_المخالفات:
        embed = discord.Embed(title="سجل مغادرة 📤", color=0x95a5a6, timestamp=datetime.utcnow())
        embed.add_field(name="العضو", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="الأيدي", value=f"`{member.id}`", inline=True)
        embed.add_field(name="دخل السيرفر", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "غير معروف", inline=False)
        await روم_المخالفات.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # --- نظام اللفل ---
    user_id_int = message.author.id
    if user_id_int not in المستخدمين_XP:
        المستخدمين_XP[user_id_int] = {"xp": 0, "level": 0}

    المستخدمين_XP[user_id_int]["xp"] += random.randint(5, 15)
    await check_level_up(message, user_id_int)

    # --- فلتر السب ---
    محتوى_الرسالة = message.content.lower()
    for كلمة in كلمات_ممنوعة:
        if كلمة in محتوى_الرسالة:
            await message.delete()

            التحذيرات[user_id_int] = التحذيرات.get(user_id_int, 0) + 1

            await message.channel.send(f"{message.author.mention} لا تسب! تم تحذيرك. ({التحذيرات[user_id_int]}/3)", delete_after=10)

            روم_المخالفات = discord.utils.get(message.guild.channels, name=اسم_روم_المخالفات)
            if روم_المخالفات:
                embed = discord.Embed(title="تم حذف رسالة سيئة 🚫", color=0xff0000, timestamp=message.created_at)
                embed.add_field(name="العضو", value=f"{message.author.mention}", inline=True)
                embed.add_field(name="تحذيراته", value=f"{التحذيرات[user_id_int]}/3", inline=True)
                embed.add_field(name="الكلمة", value=f"||{كلمة}||", inline=False)
                embed.add_field(name="الرسالة", value=f"```{message.content}```", inline=False)
                embed.add_field(name="الروم", value=f"{message.channel.mention}", inline=True)
                await روم_المخالفات.send(embed=embed)

            if التحذيرات[user_id_int] >= 3:
                await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=10), reason="تكرار السب")
                await message.channel.send(f"{message.author.mention} تم إعطائك ميوت 10 دقائق لتكرار المخالفة.", delete_after=10)
                التحذيرات[user_id_int] = 0
            return # نوقف هنا عشان ما يرد على السب

    # --- الرد التلقائي ---
    for الكلمة, قائمة_الردود in الردود_التلقائية.items():
        if الكلمة in محتوى_الرسالة:
            await message.channel.send(random.choice(قائمة_الردود))
            break # يرد مرة وحدة بس

    await bot.process_commands(message)

# --- أوامر البوت ---
@bot.command(name='لفل')
async def لفل(ctx, member: discord.Member = None):
    if ctx.channel.name!= اسم_روم_اوامر_البوت and ctx.channel.name!= اسم_روم_الشات_العام:
        return await ctx.send(f"استخدم الأمر في روم {اسم_روم_اوامر_البوت}", delete_after=5)

    if member is None:
        member = ctx.author

    user_data = المستخدمين_XP.get(member.id, {"xp": 0, "level": 0})
    xp = user_data["xp"]
    level = user_data["level"]
    xp_needed = احسب_الاكس_بي_المطلوب(level)

    embed = discord.Embed(title=f"لفل {member.display_name}", color=0x3498db)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="اللفل", value=f"**{level}**", inline=True)
    embed.add_field(name="الخبرة XP", value=f"**{xp} / {xp_needed}**", inline=True)

    await ctx.send(embed=embed)

@bot.command(name='توب')
async def توب(ctx):
    if ctx.channel.name!= اسم_روم_اوامر_البوت:
        return await ctx.send(f"استخدم الأمر في روم {اسم_روم_اوامر_البوت}", delete_after=5)

    sorted_users = sorted(المستخدمين_XP.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]

    embed = discord.Embed(title="🏆 توب 10 بالسيرفر", color=0xf1c40f)

    description = ""
    for i, (user_id, data) in enumerate(sorted_users):
        user = bot.get_user(user_id)
        if user:
            description += f"**{i+1}.** {user.mention} - لفل **{data['level']}** | `{data['xp']} XP`\n"

    embed.description = description
    await ctx.send(embed=embed)

@bot.command(name='عط')
@commands.has_permissions(administrator=True)
async def عط(ctx, member: discord.Member, amount: int):
    user_id = member.id
    if user_id not in المستخدمين_XP:
        المستخدمين_XP[user_id] = {"xp": 0, "level": 0}

    المستخدمين_XP[user_id]["xp"] += amount
    await ctx.send(f"✅ تم إضافة {amount} XP لـ {member.mention}")
    await check_level_up(ctx, user_id)

@bot.command(name='اخصم')
@commands.has_permissions(administrator=True)
async def اخصم(ctx, member: discord.Member, amount: int):
    user_id = member.id
    if user_id not in المستخدمين_XP:
        return await ctx.send("العضو ما عنده XP")

    المستخدمين_XP[user_id]["xp"] = max(0, المستخدمين_XP[user_id]["xp"] - amount)
    المستخدمين_XP[user_id]["level"] = احسب_لفل(المستخدمين_XP[user_id]["xp"])
    await ctx.send(f"✅ تم خصم {amount} XP من {member.mention}\nلفله الحين: {المستخدمين_XP[user_id]['level']} | XP: {المستخدمين_XP[user_id]['xp']}")

# --- تشغيل البوت ---
bot.run(os.environ['TOKEN'])
