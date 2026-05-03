import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")
اسم_روم_الترحيب = "شات-عام"
اسم_روم_اللوق = "اللوق"

الكلمات_المسيئة = ["سب1", "سب2", "كلمة_ممنوعة", "يا حيوان", "ياحيوان", "يا كلب", "ياكلب", "يامريض", "كس امك", "كسامك", "كل زق", "كلزق"]

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
                embed
