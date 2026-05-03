import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")
اسم_روم_الترحيب = "شات-عام"
اسم_روم_اللوق = "اللوق"

الكلمات_المسيئة = ["سب1", "سب2", "كلمة_ممنوعة", "يا حيوان"]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
async def on_message(message):
    if message.author.bot:
        return

    for كلمة in الكلمات_المسيئة:
        if كلمة in message.content.lower():
            await message.delete()
            try:
                await message.channel.send(f"{message.author.mention} لا تستخدم كلمات سيئة 🚫", delete_after=5)
            except:
                pass
            
            روم_اللوق = discord.utils.get(message.guild.channels, name=اسم_روم_اللوق)
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
            return

    msg = message.content.lower()
    if msg == "السلام عليكم":
        await message.channel.send(f" وعليكم السلام ورحمة الله وبركاته {message.author.mention}")
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

    await bot.process_commands(message)

@bot.command()
async def هلا(ctx):
    await ctx.send(f"هلا والله {ctx.author.mention} 👋")

@bot.event
async def on_ready():
    print(f'تم تسجيل الدخول باسم {bot.user}')
    print('البوت جاهز ✅')

bot.run(TOKEN)
