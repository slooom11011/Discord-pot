import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import json
import os

TOKEN = os.getenv("TOKEN")  # ياخذ التوكن من Railway
اسم_روم_الترحيب = "شات-عام"
اسم_روم_اللوق = "اللوق"
ملف_التذكيرات = "reminders.json"

# الكلمات الممنوعة - عدلها براحتك
الكلمات_المسيئة = ["سب1", "سب2", "كلمة_ممنوعة", "يا حيوان"]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 1. الترحيب بالاعضاء الجدد =====
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name=اسم_روم_الترحيب)
    if channel:
        embed = discord.Embed(
            title="عضو جديد نورتنا 🌟",
            description=f'حياك الله {member.mention} في **{member.guild.name}**',
            color=0x2ecc71
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="أنت العضو رقم", value=f'`{member.guild.member_count}`', inline=True)
        embed.set_footer(text="لا تنسى تقرأ القوانين")
        await channel.send(embed=embed)

# ===== 2. مسح الرسائل المسيئة =====
@bot.event
async def on_message(message):
    # 1. لا يرد على نفسه أو على البوتات الثانية
    if message.author.bot:
        return

    # 2. حذف الكلمات المسيئة + لوق
    for كلمة in الكلمات_المسيئة:
        if كلمة in message.content.lower():
            await message.delete()
            
            # رسالة تحذير في نفس الروم تنحذف بعد 5 ثواني
            await message.channel.send(f"{message.author.mention} لا تستخدم كلمات سيئة 🚫", delete_after=5)
            
            # يرسل تقرير في روم اللوق
            روم_اللوق = bot.get_channel(1500455892032946196)  # ← حط اي دي روم اللوق هنا
            if روم_اللوق:
                embed = discord.Embed(
                    title="تم حذف رسالة سيئة 🚫",
                    color=0xff0000,
                    timestamp=message.created_at
                )
                embed.add_field(name="العضو", value=f"{message.author.mention}", inline=True)
                embed.add_field(name="الروم", value=message.channel.mention, inline=True)
                embed.add_field(name="الكلمة", value=f"||{كلمة}||", inline=False)
                embed.add_field(name="الرسالة كاملة", value=f"```{message.content}```", inline=False)
                embed.set_footer(text=f"ID: {message.author.id}")
                await روم_اللوق.send(embed=embed)
            
            return  # يوقف هنا ولا يكمل للردود

    msg = message.content.lower()

    # 3. ردود السلام والصباح والمساء
    if msg == "السلام عليكم":
        await message.channel.send(f"وعليكم السلام ورحمة الله {message.author.mention}")
    
    elif msg == "صباح الخير":
        await message.channel.send(f"صباح النور {message.author.mention} ☀️")
    
    elif msg == "صباح النور":
        await message.channel.send(f"صباح الورد {message.author.mention} 🌹")
    
    elif msg == "صباح الورد":
        await message.channel.send(f"صباح العسل {message.author.mention} 🍯")

    elif msg == "مساء الخير":
        await message.channel.send(f"مساء النور {message.author.mention} 🌙")
    
    elif msg == "مساء النور":
        await message.channel.send(f"مساء الورد {message.author.mention} 🌸")
    
    elif msg == "مساء الورد":
        await message.channel.send(f"مساء العسل {message.author.mention} 🍯")

    # 4. مهم عشان أوامر !هلا و !ذكرني تشتغل
    await bot.process_commands(message)

# ===== 3. نظام التذكير =====
def تحميل_التذكيرات():
    if os.path.exists(ملف_التذكيرات):
        with open(ملف_التذكيرات, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def حفظ_التذكيرات(التذكيرات):
    with open(ملف_التذكيرات, 'w', encoding='utf-8') as f:
        json.dump(التذكيرات, f, ensure_ascii=False, indent=4)

@bot.command()
@commands.has_permissions(administrator=True)
async def ذكرني(ctx, وقت: str, *, الرسالة):
    """
    استخدام: !ذكرني 10m اجتماع الادارة
    الوقت: s=ثواني, m=دقايق, h=ساعات, d=ايام
    """
    try:
        if وقت[-1] == 's': ثواني = int(وقت[:-1])
        elif وقت[-1] == 'm': ثواني = int(وقت[:-1]) * 60
        elif وقت[-1] == 'h': ثواني = int(وقت[:-1]) * 3600
        elif وقت[-1] == 'd': ثواني = int(وقت[:-1]) * 86400
        else: 
            await ctx.send("صيغة الوقت غلط. استخدم: 10s أو 5m أو 2h أو 1d")
            return
        
        وقت_التذكير = datetime.now() + timedelta(seconds=ثواني)
        
        التذكيرات = تحميل_التذكيرات()
        التذكيرات.append({
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "وقت": وقت_التذكير.isoformat(),
            "الرسالة": الرسالة
        })
        حفظ_التذكيرات(التذكيرات)
        
        await ctx.send(f'تمام {ctx.author.mention} ✅\nبذكرك بـ **{الرسالة}** بعد **{وقت}**')
        
    except:
        await ctx.send("فيه خطأ. تأكد تكتب كذا: `!ذكرني 30m شرب موية`")

@tasks.loop(seconds=10)
async def شيك_التذكيرات():
    التذكيرات = تحميل_التذكيرات()
    التذكيرات_الباقية = []
    
    for تذكير in التذكيرات:
        if datetime.now() >= datetime.fromisoformat(تذكير["وقت"]):
            channel = bot.get_channel(تذكير["channel_id"])
            user = bot.get_user(تذكير["user_id"])
            if channel and user:
                await channel.send(f'🔔 تذكير لـ {user.mention}\n**{تذكير["الرسالة"]}**')
        else:
            التذكيرات_الباقية.append(تذكير)
    
    حفظ_التذكيرات(التذكيرات_الباقية)

@bot.event
async def on_ready():
    print(f'البوت شغال: {bot.user}')
    شيك_التذكيرات.start()

@bot.command()
async def هلا(ctx):
    await ctx.send(f'هلا والله {ctx.author.mention} منورنا 👋')

@bot.event


bot.run(TOKEN)
