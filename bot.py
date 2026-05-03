import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
اسم_روم_الترحيب = "شات-العام"
اسم_روم_اللوق = "اللوق"
اسم_روم_الوداع = "شات-العام"

الكلمات_المسيئة = ["سب1", "سب2", "كلمة_ممنوعة", "يا حيوان", "ياحيوان", "يا كلب", "ياكلب", "يامريض", "كس امك", "كسامك", "كل زق", "كلزق"]

# نظام التحذيرات
التحذيرات = {}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'تم تسجيل الدخول باسم {bot.user}')
    await bot.change_presence(activity=discord.Game(name="!مساعدة | فلترة 24/7"))

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

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.channels, name=اسم_روم_الوداع)
    if channel:
        embed = discord.Embed(
            title="عضو غادرنا 💔",
            description=f'**{member.name}** طلع من السيرفر\nالله يستر عليه وين ما راح',
            color=0xe74c3c
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="عدد الأعضاء الآن", value=f'`{member.guild.member_count}`', inline=True)
        embed.set_footer(text=f"ID: {member.id}")
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
    if message.author.bot:
        return

    for كلمة in الكلمات_المسيئة:
        if كلمة in message.content.lower():
            await message.delete()
            
            user_id = message.author.id
            if user_id not in التحذيرات:
                التحذيرات[user_id] = 0
            التحذيرات[user_id] += 1
            
            if التحذيرات[user_id] >= 3:
                role = discord.utils.get(message.guild.roles, name="Muted")
                if not role:
                    role = await message.guild.create_role(name="Muted")
                    for ch in message.guild.channels:
                        await ch.set_permissions(role, send_messages=False)
                await message.author.add_roles(role)
                await message.channel.send(f"{message.author.mention} اخذت ميوت ساعة بسبب السب المتكرر 🔇")
                التحذيرات[user_id] = 0
                await asyncio.sleep(3600)
                await message.author.remove_roles(role)
            else:
                await message.channel.send(f"{message.author.mention} تحذير {التحذيرات[user_id]}/3 لا تسب 🚫", delete_after=5)

            روم_اللوق = discord.utils.get(message.guild.channels, name=اسم_روم_اللوق)
            if روم_اللوق:
                embed = discord.Embed(title="تم حذف رسالة سيئة 🚫", color=0xff0000, timestamp=message.created_at)
                embed.add_field(name="العضو", value=f"{message.author.mention}", inline=True)
                embed.add_field(name="تحذيراته", value=f"{التحذيرات[user_id]}/3", inline=True)
                embed.add_field(name="الكلمة", value=f"||{كلمة}||", inline=False)
                embed.add_field(name="الرسالة", value=f"```{message.content}```", inline=False)
                await روم_اللوق.send(embed=embed)
            return

    msg = message.content.lower()
    if msg == "السلام عليكم":
        await message.channel.send(f"وعليكم السلام ورحمة الله وبركاته {message.author.mention}")
    elif msg == "صباح الخير":
        await message.channel.send(f"صباح النور {message.author.mention} ☀️")
    elif msg == "مساء الخير":
        await message.channel.send(f"مساء النور {message.author.mention} 🌙")

    await bot.process_commands(message)

# ===== 1. أوامر عامة =====
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
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed.add_field(name="الرولات", value=" ".join(roles) if roles else "لا يوجد", inline=False)
    await ctx.send(embed=embed)

# ===== 2. أوامر الإدارة =====
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
        for ch in ctx.guild.channels:
            await ch.set_permissions(role, send_messages=False)
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

# ===== 3. نظام التحذيرات اليدوي =====
@bot.command()
@commands.has_permissions(kick_members=True)
async def تحذير(ctx, member: discord.Member, *, السبب="مافي سبب"):
    user_id = member.id
    if user_id not in التحذيرات: التحذيرات[user_id] = 0
    التحذيرات[user_id] += 1
    await ctx.send(f"تم تحذير {member.mention} | {التحذيرات[user_id]}/3 | السبب: {السبب} ⚠️")

@bot.command()
async def تحذيراتي(ctx):
    await ctx.send(f"عندك `{التحذيرات.get(ctx.author.id, 0)}` تحذير ⚠️")

@bot.command()
@commands.has_permissions(administrator=True)
async def مسح_تحذيرات(ctx, member: discord.Member):
    التحذيرات[member.id] = 0
    await ctx.send(f"تم مسح تحذيرات {member.mention} ✅")

# ===== 4. أوامر الرولات الجديدة =====
@bot.command(name="سوي_رول", description="يسوي رول جديد | مثال: !سوي_رول مشرف ازرق")
@commands.has_permissions(administrator=True)
async def سوي_رول(ctx, اسم: str, لون: str = "ابيض"):
    الوان = {
        "احمر": 0xff0000, "اخضر": 0x00ff00, "ازرق": 0x0000ff,
        "اصفر": 0xffff00, "بنفسجي": 0x9b59b6, "برتقالي": 0xe67e22,
        "وردي": 0xff69b4, "ابيض": 0xffffff, "اسود": 0x000000, "رمادي": 0x95a5a6
    }
    
    لون_الرول = الوان.get(لون, 0x99aab5)
    رول = await ctx.guild.create_role(name=اسم, color=لون_الرول)
    await ctx.send(f"تم إنشاء رول {رول.mention} باللون {لون} ✅")

@bot.command(name="رول", description="يعطي رول لعضو | مثال: !رول @عضو مشرف")
@commands.has_permissions(manage_roles=True)
async def رول(ctx, member: discord.Member, *, اسم_الرول):
    role = discord.utils.get(ctx.guild.roles, name=اسم_الرول)
    if not role:
        await ctx.send("❌ الرول مو موجود. سوه بالأمر `!سوي_رول`")
        return
    if role in member.roles:
        await ctx.send(f"❌ {member.mention} عنده الرول أصلاً")
        return
    await member.add_roles(role)
    await ctx.send(f"تم إعطاء {member.mention} رول {role.mention} ✅")

@bot.command(name="شيل_رول", description="يشيل رول من عضو | مثال: !شيل_رول @عضو مشرف")
@commands.has_permissions(manage_roles=True)
async def شيل_رول(ctx, member: discord.Member, *, اسم_الرول):
    role = discord.utils.get(ctx.guild.roles, name=اسم_الرول)
    if not role:
        await ctx.send("❌ الرول مو موجود")
        return
    if role not in member.roles:
        await ctx.send(f"❌ {member.mention} ما عنده الرول أصلاً")
        return
    await member.remove_roles(role)
    await ctx.send(f"تم إزالة رول {role.mention} من {member.mention} ✅")

@bot.command(name="رولات", description="يعرض كل الرولات في السيرفر")
async def رولات(ctx):
    roles = [role.mention for role in ctx.guild.roles if role.name != "@everyone"]
    embed = discord.Embed(title=f"رولات {ctx.guild.name}", color=0x3498db)
    embed.description = "\n".join(roles) if roles else "مافي رولات"
    embed.set_footer(text=f"العدد: {len(roles)}")
    await ctx.send(embed=embed)

# ===== 5. أمر المساعدة =====
@bot.command()
async def مساعدة(ctx):
    embed = discord.Embed(title="أوامر البوت", description="البريفكس: `!`", color=0x9b59b6)
    embed.add_field(name="🎯 عامة", value="`هلا` `بنق` `سيرفر` `يوزر` `تحذيراتي` `رولات`", inline=False)
    embed.add_field(name="⚙️ إدارة", value="`مسح` `ميوت` `فك` `طرد` `باند` `تحذير` `مسح_تحذيرات`", inline=False)
    embed.add_field(name="👑 رولات", value="`سوي_رول` `رول` `شيل_رول`", inline=False)
    embed.add_field(name="🛡️ تلقائي", value="ترحيب + وداع + حذف السب + ميوت بعد 3 تحذيرات + لوق + ردود", inline=False)
    await ctx.send(embed=embed)

bot.run(TOKEN)
