import discord, os, asyncio, re, aiosqlite, pytz
from discord.ext import commands, tasks
from datetime import datetime, timezone

TOKEN = os.getenv("TOKEN")
CFG = {
    "welcome": "شات-العام",
    "log": "المخالفات",
    "bye": "شات-العام",
    "lvl_up": "لفل-اب", # تأكد اسم الروم مطابق 100%
    "weekly": "توب-الاسبوع",
    "rules": 1500607707806433460,
    "new_role": ["الأعضاء الجدد", 0x95a5a6],
    "bad_role": ["غير موثق", 0xe74c3c],
    "lvl_roles": {1: ["مبتدئ", 0x95a5a6], 5: ["نشيط", 0x3498db], 10: ["متفاعل", 0x2ecc71], 20: ["أسطورة", 0xf1c40f], 50: ["VIP", 0xe74c3c]},
    "bad_words": ["سب1","سب2","يا حيوان","ياحيوان","يا كلب","ياكلب","يامريض","كس امك","كسامك","كل زق","كلزق"],
    "owner_id": 763363479960682506
}
warns, xp_cd, spam = {}, {}, {}
DB = 'levels.db'

def calc_lvl(xp): return int(((-50 + (2500 + 200*xp)**0.5) // 100))
def next_xp(l): return 50*(l**2)+50*l
def progress(xp,l,bl=10):
    if l==0: return "█"*bl,100
    prev,nxt=next_xp(l-1),next_xp(l)
    need,have=nxt-prev,xp-prev
    prog=int((have/need)*bl) if need else bl
    return "█"*prog+"░"*(bl-prog),int((have/need)*100) if need else 100

async def db(): return aiosqlite.connect(DB)
async def db_init():
    async with await db() as c: await c.execute('CREATE TABLE IF NOT EXISTS levels (guild_id TEXT, user_id TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0, weekly_xp INTEGER DEFAULT 0, PRIMARY KEY (guild_id, user_id))'); await c.commit()

async def get_data(g,u):
    async with await db() as c:
        r=await(await c.execute('SELECT xp,level,weekly_xp FROM levels WHERE guild_id=? AND user_id=?',(g,u))).fetchone()
        return {"xp":r[0],"level":r[1],"weekly_xp":r[2]} if r else {"xp":0,"level":0,"weekly_xp":0}

async def save_data(g,u,xp,lvl,wxp):
    async with await db() as c: await c.execute('INSERT INTO levels VALUES (?,?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET xp=?,level=?,weekly_xp=?',(g,u,xp,lvl,wxp,xp,lvl,wxp)); await c.commit()

async def get_role(g,n,c=None):
    role = discord.utils.get(g.roles,name=n)
    if not role and c:
        try: role = await g.create_role(name=n,color=c,reason="رول لفل تلقائي")
        except Exception as e: print(f"[ROLE ERROR] ما قدرت اسوي رول {n}: {e}")
    return role

async def update_role(m,lvl):
    try:
        old_roles = [r for r in m.roles if r.name in [d[0] for d in CFG["lvl_roles"].values()]]
        if old_roles: await m.remove_roles(*old_roles,reason="تحديث رول اللفل")
        for lv,(n,c) in sorted(CFG["lvl_roles"].items(),reverse=True):
            if lvl>=lv:
                role = await get_role(m.guild,n,c)
                if role:
                    await m.add_roles(role,reason=f"وصل لفل {lvl}")
                    return role
        return None
    except Exception as e:
        print(f"[ROLE UPDATE ERROR] {m}: {e}")
        return None

async def temp_mute(m,s,reason):
    r=await get_role(m.guild,"Muted")
    [await ch.set_permissions(r,send_messages=False,add_reactions=False) for ch in m.guild.channels]
    await m.add_roles(r,reason=reason); await asyncio.sleep(s); await m.remove_roles(r)

async def log_send(g,title,color,**f):
    if ch:=discord.utils.get(g.channels,name=CFG["log"]):
        e=discord.Embed(title=title,color=color,timestamp=datetime.now(timezone.utc))
        [e.add_field(name=k,value=v,inline=i) for k,v,i in f.get("fields",[])]
        if t:=f.get("thumb"): e.set_thumbnail(url=t)
        try: await ch.send(embed=e)
        except: print(f"[LOG ERROR] ما قدرت ارسل اللوق")

bot=commands.Bot(command_prefix="!",intents=discord.Intents.all())

@tasks.loop(time=datetime.strptime("12:00","%H:%M").time())
async def weekly_top():
    if datetime.now(pytz.timezone('Asia/Riyadh')).weekday()!=4: return
    for g in bot.guilds:
        if not (ch:=discord.utils.get(g.channels,name=CFG["weekly"])): continue
        async with await db() as c: top=await(await c.execute('SELECT user_id,weekly_xp,level FROM levels WHERE guild_id=? AND weekly_xp>0 ORDER BY weekly_xp DESC LIMIT 10',(str(g.id),))).fetchall()
        if not top: await ch.send(embed=discord.Embed(title="😴 لا يوجد متفاعلين",description="مافي أحد جمع XP هذا الأسبوع",color=0x95a5a6)); continue
        e=discord.Embed(title="🏆 توب 10 لهذا الأسبوع",color=0xf1c40f,timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=g.icon.url if g.icon else None)
        medals=["🥇","🥈","🥉"]
        e.description="".join([f"{medals[i] if i<3 else f'**{i+1}.**'} <@{u}>\n└ `{x:,} XP` • لفل `{l}`\n\n" for i,(u,x,l) in enumerate(top)])
        e.set_footer(text="يتصفر كل جمعة الساعة 12 ظهراً",icon_url=bot.user.avatar.url if bot.user.avatar else None)
        await ch.send(embed=e)
        async with await db() as c: await c.execute('UPDATE levels SET weekly_xp=0 WHERE guild_id=?',(str(g.id),)); await c.commit()

@tasks.loop(hours=12)
async def auto_backup():
    if not CFG["owner_id"] or not os.path.exists(DB): return
    try:
        u=await bot.fetch_user(CFG["owner_id"])
        e=discord.Embed(title="📦 نسخة احتياطية تلقائية",color=0x3498db)
        e.add_field(name="الحجم",value=f"`{os.path.getsize(DB)/1024:.1f} KB`",inline=True)
        e.add_field(name="التاريخ",value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>",inline=True)
        await u.send(embed=e,file=discord.File(DB))
    except Exception as err: print(f"Auto backup error: {err}")

@bot.event
async def on_ready():
    await db_init()
    print(f'[READY] {bot.user}')
    print(f'[READY] روم اللفل اب: {CFG["lvl_up"]}')
    weekly_top.start()
    auto_backup.start()

@bot.event
async def on_member_join(m):
    if (datetime.now(timezone.utc)-m.created_at).days<7:
        r=await get_role(m.guild,CFG["bad_role"][0],CFG["bad_role"][1])
        [await ch.set_permissions(r,send_messages=False) for ch in m.guild.channels]; await m.add_roles(r)
        await log_send(m.guild,"⚠️ حساب جديد مشبوه",0xe67e22,fields=[("العضو",m.mention,True),("عمر الحساب",f"`{(datetime.now(timezone.utc)-m.created_at).days} يوم`",True),("الإجراء","تم إعطاؤه ميوت تلقائي",False)],thumb=m.avatar.url if m.avatar else m.default_avatar.url); return
    r=await get_role(m.guild,CFG["new_role"][0],CFG["new_role"][1]); await m.add_roles(r)
    if ch:=discord.utils.get(m.guild.channels,name=CFG["welcome"]):
        e=discord.Embed(title="🌟 عضو جديد نورتنا",description=f'**أهلاً وسهلاً {m.mention}**\nنورت **{m.guild.name}**\n\nتم إعطائك رول {r.mention}',color=0x2ecc71,timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
        e.add_field(name="رقم العضو",value=f'`#{m.guild.member_count}`',inline=True)
        e.add_field(name="تاريخ الإنضمام",value=f'<t:{int(m.joined_at.timestamp())}:R>',inline=True)
        e.add_field(name="📜 القوانين",value=f"قبل ما تبدأ تأكد تقرأ <#{CFG['rules']}>",inline=False)
        e.set_footer(text="حياك الله معنا")
        await ch.send(embed=e)

@bot.event
async def on_member_remove(m):
    if ch:=discord.utils.get(m.guild.channels,name=CFG["bye"]):
        e=discord.Embed(title="💔 عضو غادرنا",description=f'**{m.name}** طلع من السيرفر\n\nالله يستر عليه وين ما راح',color=0xe74c3c,timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
        e.add_field(name="عدد الأعضاء الآن",value=f'`{m.guild.member_count}`',inline=True)
        e.add_field(name="مدة البقاء",value=f'<t:{int(m.joined_at.timestamp())}:R>' if m.joined_at else "غير معروف",inline=True)
        await ch.send(embed=e)

@bot.event
async def on_member_ban(g,u): await log_send(g,"🔨 تم تبنيد عضو",0x992d22,fields=[("العضو",f"{u.mention}\n`{u.name}`",True),("ID",f"`{u.id}`",True)],thumb=u.avatar.url if u.avatar else u.default_avatar.url)

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    if re.search(r'discord.(gg|com/invite)',msg.content.lower()) and not msg.author.guild_permissions.manage_messages: await msg.delete(); asyncio.create_task(temp_mute(msg.author,300,"نشر رابط")); return
    if msg.mention_everyone and not msg.author.guild_permissions.mention_everyone: await msg.delete(); asyncio.create_task(temp_mute(msg.author,600,"منشن everyone")); return
    if len(msg.mentions)>=5 and not msg.author.guild_permissions.mention_everyone: await msg.delete(); return
    spam.setdefault(msg.author.id,[]).append(msg.content)
    if len(spam[msg.author.id])>5: spam[msg.author.id].pop(0)
    if spam[msg.author.id].count(msg.content)>=4 and not msg.author.guild_permissions.manage_messages: await msg.delete(); return

    gid,uid=str(msg.guild.id),str(msg.author.id)
    if uid not in xp_cd or (datetime.now(timezone.utc)-xp_cd[uid]).seconds>=60:
        xp_cd[uid]=datetime.now(timezone.utc); d=await get_data(gid,uid)
        xp_gain=min(len(msg.content)//10,5) if len(msg.content)>5 else 1
        xp,lvl,wxp=d["xp"]+xp_gain,d["level"],d["weekly_xp"]+xp_gain; new_lvl=calc_lvl(xp)
        await save_data(gid,uid,xp,new_lvl,wxp)

        if new_lvl>lvl:
            print(f"[LEVEL UP] {msg.author} | {lvl} -> {new_lvl}")
            ch = discord.utils.get(msg.guild.channels,name=CFG["lvl_up"])

            if not ch:
                print(f"[LEVEL UP ERROR] روم {CFG['lvl_up']} مو موجود")
            else:
                bar,percent=progress(xp,new_lvl)
                e=discord.Embed(title="🎉 LEVEL UP!",description=f'**{msg.author.mention}** وصل **لفل {new_lvl}** 🚀',color=0xf1c40f,timestamp=datetime.now(timezone.utc))
                e.set_thumbnail(url=msg.author.display_avatar.url)
                e.add_field(name="📊 XP الحالي",value=f'`{xp:,}`',inline=True)
                e.add_field(name="⭐ اللفل الجديد",value=f'`{new_lvl}`',inline=True)
                e.add_field(name="🎯 لللفل الجاي",value=f'`{next_xp(new_lvl)-xp:,} XP`',inline=True)
                e.add_field(name="التقدم",value=f'`{bar}` {percent}%',inline=False)
                e.set_footer(text=msg.guild.name,icon_url=msg.guild.icon.url if msg.guild.icon else None)

                new_role = await update_role(msg.author,new_lvl)
                if new_role:
                    e.add_field(name="🎊 رتبة جديدة",value=f"مبروك حصلت على {new_role.mention}",inline=False)
                    print(f"[LEVEL UP] عطيته رول: {new_role.name}")

                try:
                    await ch.send(embed=e)
                    print(f"[LEVEL UP] تم الارسال بروم {ch.name}")
                except Exception as err:
                    print(f"[LEVEL UP ERROR] ما قدرت ارسل: {err}")

    for w in CFG["bad_words"]:
        if w in msg.content.lower():
            await msg.delete(); warns[msg.author.id]=warns.get(msg.author.id,0)+1
            if warns[msg.author.id]>=3: asyncio.create_task(temp_mute(msg.author,3600,"سب")); warns[msg.author.id]=0; await msg.channel.send(f"🔇 {msg.author.mention} ميوت ساعة بسبب السب المتكرر")
            else: await msg.channel.send(f"⚠️ {msg.author.mention} تحذير {warns[msg.author.id]}/3",delete_after=5)
            await log_send(msg.guild,"🚫 تم حذف رسالة سيئة",0xff0000,fields=[("العضو",msg.author.mention,True),("التحذيرات",f"`{warns[msg.author.id]}/3`",True),("الكلمة المحظورة",f"||{w}||",False),("الرسالة",f"```{msg.content[:500]}```",False)]); return

    if msg.content.lower()=="السلام عليكم": await msg.channel.send(f"وعليكم السلام ورحمة الله وبركاته {msg.author.mention} 🌹")
    elif msg.content.lower()=="صباح الخير": await msg.channel.send(f"صباح النور والسرور {msg.author.mention} ☀️")
    elif msg.content.lower()=="مساء الخير": await msg.channel.send(f"مساء الورد {msg.author.mention} 🌙")
    await bot.process_commands(msg)

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.CommandNotFound): return
    msgs={"مسح":"❌ استخدم الأمر كذا: `!مسح 10`","عط":"❌ استخدم الأمر كذا: `!عط @عضو 100`","خصم":"❌ استخدم الأمر كذا: `!خصم @عضو 100`","ميوت":"❌ استخدم الأمر كذا: `!ميوت @عضو 10 سبب`"}
    if isinstance(error,commands.MissingRequiredArgument) and ctx.command.name in msgs: return await ctx.send(embed=discord.Embed(description=msgs[ctx.command.name],color=0xe74c3c),delete_after=5)
    if isinstance(error,commands.MissingPermissions): return await ctx.send(embed=discord.Embed(description="❌ ما عندك صلاحية تستخدم هذا الأمر",color=0xe74c3c),delete_after=5)
    if isinstance(error,commands.BadArgument): return await ctx.send(embed=discord.Embed(description="❌ تأكد إنك كتبت الأمر صح",color=0xe74c3c),delete_after=5)
    print(f"Error in {ctx.command}: {error}")

@bot.command()
async def هلا(ctx): await ctx.send(f"هلا والله {ctx.author.mention} 👋")

@bot.command()
async def بنق(ctx): await ctx.send(embed=discord.Embed(title="🏓 البنق",description=f'**`{round(bot.latency*1000)}ms`**',color=0x2ecc71 if bot.latency<0.1 else 0xe67e22))

@bot.command()
async def سيرفر(ctx):
    g=ctx.guild; bots=len([m for m in g.members if m.bot]); humans=g.member_count-bots
    async with await db() as c: top=await(await c.execute('SELECT user_id,xp,level FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT 1',(str(g.id),))).fetchone()
    e=discord.Embed(title=f"📊 إحصائيات {g.name}",color=0x3498db,timestamp=datetime.now(timezone.utc))
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    e.add_field(name="👥 الأعضاء",value=f"`{humans}`",inline=True); e.add_field(name="🤖 البوتات",value=f"`{bots}`",inline=True); e.add_field(name="📈 الإجمالي",value=f"`{g.member_count}`",inline=True)
    e.add_field(name="👑 أعلى لفل",value=f"<@{top[0]}> لفل `{top[2]}`" if top else "لا يوجد",inline=True)
    e.add_field(name="📅 تاريخ الإنشاء",value=f"<t:{int(g.created_at.timestamp())}:R>",inline=True); e.add_field(name="🔧 البوت",value=f"`{round(bot.latency*1000)}ms`",inline=True)
    e.set_footer(text=f"ID: {g.id}"); await ctx.send(embed=e)

@bot.command()
async def يوزر(ctx,m:discord.Member=None):
    m=m or ctx.author; d=await get_data(str(ctx.guild.id),str(m.id))
    e=discord.Embed(title=f"📋 معلومات {m.name}",color=m.color if m.color.value else 0x3498db,timestamp=datetime.now(timezone.utc))
    e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url)
    e.add_field(name="👤 العضو",value=m.mention,inline=True); e.add_field(name="📅 دخل السيرفر",value=f'<t:{int(m.joined_at.timestamp())}:R>',inline=True); e.add_field(name="⚠️ التحذيرات",value=f'`{warns.get(m.id,0)}/3`',inline=True)
    if d["xp"]>0:
        e.add_field(name="⭐ اللفل",value=f'`{d["level"]}`',inline=True); e.add_field(name="💎 XP الكلي",value=f'`{d["xp"]:,}/{next_xp(d["level"]):,}`',inline=True); e.add_field(name="📈 XP الأسبوع",value=f'`{d["weekly_xp"]:,}`',inline=True)
        bar,percent=progress(d["xp"],d["level"]); e.add_field(name="التقدم للفل الجاي",value=f'`{bar}` {percent}%',inline=False)
    roles=[r.mention for r in m.roles if r.name!="@everyone"]; e.add_field(name="🎭 الرولات",value=" ".join(roles) if roles else "لا يوجد",inline=False)
    e.set_footer(text=f"ID: {m.id}"); await ctx.send(embed=e)

@bot.command()
async def لفل(ctx,m:discord.Member=None):
    m=m or ctx.author; d=await get_data(str(ctx.guild.id),str(m.id))
    if not d["xp"]: return await ctx.send(embed=discord.Embed(description=f"❌ {m.mention} ما عنده XP لحد الحين",color=0xe74c3c))
    e=discord.Embed(title=f"⭐ لفل {m.display_name}",color=0x3498db); e.set_thumbnail(url=m.display_avatar.url)
    e.add_field(name="اللفل",value=f'`{d["level"]}`',inline=True); e.add_field(name="XP",value=f'`{d["xp"]:,}/{next_xp(d["level"]):,}`',inline=True); e.add_field(name="باقي",value=f'`{next_xp(d["level"])-d["xp"]:,} XP`',inline=True)
    e.add_field(name="XP الأسبوع",value=f'`{d["weekly_xp"]:,}`',inline=True); bar,percent=progress(d["xp"],d["level"],15); e.add_field(name="التقدم",value=f'`{bar}` {percent}%',inline=False)
    e.set_footer(text=f"استخدم!توب لرؤية المتصدرين"); await ctx.send(embed=e)

async def top_embed(g,query,title,desc,color):
    async with await db() as c: top=await(await c.execute(query,(str(g.id),))).fetchall()
    if not top: return discord.Embed(title="😴 لا يوجد متفاعلين",description="مافي أحد جمع XP هذا الأسبوع",color=0x95a5a6) if "weekly" in query else discord.Embed(description="❌ مافي أحد عنده XP",color=0xe74c3c)
    e=discord.Embed(title=title,description=desc,color=color,timestamp=datetime.now(timezone.utc)); e.set_thumbnail(url=g.icon.url if g.icon else None)
    medals=["🥇","🥈","🥉"]; e.description="".join([f"{medals[i] if i<3 else f'**{i+1}.**'} <@{u}>\n└ {'`'+str(x)+',` XP • ' if 'weekly' in query else ''}لفل `{l}`{' • `'+str(x)+',` XP' if 'weekly' not in query else ''}\n\n" for i,(u,x,l) in enumerate(top)])
    return e

@bot.command()
async def توب(ctx): e=await top_embed(ctx.guild,'SELECT user_id,xp,level FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT 10',f"🏆 توب 10 في {ctx.guild.name}","**أكثر 10 أعضاء جمعوا XP**",0xf1c40f); e.set_footer(text=f"استخدم!لفل @عضو لرؤية تفاصيل أي شخص"); await ctx.send(embed=e)

@bot.command(name="توب_اسبوع")
async def توب_اسبوع(ctx): e=await top_embed(ctx.guild,'SELECT user_id,weekly_xp,level FROM levels WHERE guild_id=? AND weekly_xp>0 ORDER BY weekly_xp DESC LIMIT 10',"🏆 توب 10 لهذا الأسبوع","**أكثر 10 أعضاء تفاعلاً خلال 7 أيام**",0xf1c40f); e.set_footer(text="يتصفر كل جمعة الساعة 12 ظهراً"); await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def عط(ctx,m:discord.Member,a:int):
    if a<=0: return await ctx.send(embed=discord.Embed(description="❌ الكمية لازم أكبر من صفر",color=0xe74c3c))
    d=await get_data(str(ctx.guild.id),str(m.id)); xp,lvl,wxp=d["xp"]+a,d["level"],d["weekly_xp"]+a; new_lvl=calc_lvl(xp)
    await save_data(str(ctx.guild.id),str(m.id),xp,new_lvl,wxp)
    if new_lvl!=lvl: await update_role(m,new_lvl)
    e=discord.Embed(title="✅ تم إعطاء XP",description=f"تم إعطاء {m.mention} **{a:,} XP**",color=0x2ecc71)
    e.add_field(name="اللفل الحالي",value=f'`{new_lvl}`',inline=True); e.add_field(name="XP الكلي",value=f'`{xp:,}`',inline=True); await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(administrator=True)
async def خصم(ctx,m:discord.Member,a:int):
    if a<=0: return await ctx.send(embed=discord.Embed(description="❌ الكمية لازم أكبر من صفر",color=0xe74c3c))
    d=await get_data(str(ctx.guild.id),str(m.id))
    if not d["xp"]: return await ctx.send(embed=discord.Embed(description=f"❌ {m.mention} ما عنده XP أصلاً",color=0xe74c3c))
    xp,lvl,wxp=max(0,d["xp"]-a),d["level"],max(0,d["weekly_xp"]-a); new_lvl=calc_lvl(xp)
    await save_data(str(ctx.guild.id),str(m.id),xp,new_lvl,wxp)
    if new_lvl!=lvl: await update_role(m,new_lvl)
    e=discord.Embed(title="✅ تم خصم XP",description=f"تم خصم **{a:,} XP** من {m.mention}",color=0xe67e22)
    e.add_field(name="اللفل الحالي",value=f'`{new_lvl}`',inline=True); e.add_field(name="XP الكلي",value=f'`{xp:,}`',inline=True); await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def مسح(ctx,n:int):
    if not 0<n<=100: return await ctx.send(embed=discord.Embed(description="❌ العدد لازم بين 1 و 100",color=0xe74c3c),delete_after=5)
    await ctx.channel.purge(limit=n+1); await ctx.send(embed=discord.Embed(description=f"✅ تم مسح `{n}` رسالة",color=0x2ecc71),delete_after=3)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def ميوت(ctx,m:discord.Member,t:int,*,reason="مافي سبب"): await temp_mute(m,t*60,reason); await ctx.send(embed=discord.Embed(title="🔇 تم إعطاء ميوت",description=f"{m.mention} لمدة `{t}` دقيقة\n**السبب:** {reason}",color=0xe74c3c))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def فك(ctx,m:discord.Member):
    if r:=discord.utils.get(ctx.guild.roles,name="Muted"): await m.remove_roles(r)
    await ctx.send(embed=discord.Embed(description=f"✅ تم فك الميوت عن {m.mention}",color=0x2ecc71))

@bot.command()
@commands.has_permissions(kick_members=True)
async def طرد(ctx,m:discord.Member,*,reason="مافي سبب"):
    await m.kick(reason=reason)
    await log_send(ctx.guild,"👢 تم طرد عضو",0xe74c3c,fields=[("العضو",f"{m.mention}\n`{m.name}`",True),("المشرف",ctx.author.mention,True),("السبب",reason,False)])
    await ctx.send(embed=discord.Embed(description=f"👢 تم طرد {m.mention}\n**السبب:** {reason}",color=0xe74c3c))

@bot.command()
@commands.has_permissions(ban_members=True)
async def باند(ctx,m:discord.Member,*,reason="مافي سبب"): await m.ban(reason=reason); await ctx.send(embed=discord.Embed(description=f"🔨 تم تبنيد {m.mention}\n**السبب:** {reason}",color=0x992d22))

@bot.command()
@commands.has_permissions(administrator=True)
async def قفل(ctx):
    [await ch.set_permissions(ctx.guild.default_role,send_messages=False) for ch in ctx.guild.text_channels]
    await ctx.send(embed=discord.Embed(title="🔒 تم قفل السيرفر",description="للفتح استخدم `!فتح`",color=0xe74c3c))

@bot.command()
@commands.has_permissions(administrator=True)
async def فتح(ctx):
    [await ch.set_permissions(ctx.guild.default_role,send_messages=True) for ch in ctx.guild.text_channels]
    await ctx.send(embed=discord.Embed(title="🔓 تم فتح السيرفر",color=0x2ecc71))

@bot.command()
@commands.has_permissions(kick_members=True)
async def تحذير(ctx,m:discord.Member,*,reason="مافي سبب"): warns[m.id]=warns.get(m.id,0)+1; await ctx.send(embed=discord.Embed(description=f"⚠️ تم تحذير {m.mention} | `{warns[m.id]}/3`\n**السبب:** {reason}",color=0xe67e22))

@bot.command()
async def تحذيراتي(ctx): await ctx.send(embed=discord.Embed(description=f"⚠️ عندك `{warns.get(ctx.author.id,0)}` تحذير",color=0xe67e22))

@bot.command()
@commands.has_permissions(administrator=True)
async def مسح_تحذيرات(ctx,m:discord.Member): warns[m.id]=0; await ctx.send(embed=discord.Embed(description=f"✅ تم مسح تحذيرات {m.mention}",color=0x2ecc71))

async def send_backup(dest,is_dm=False):
    try:
        if not os.path.exists(DB): return await dest.send(embed=discord.Embed(description="❌ ملف قاعدة البيانات ما انشئ لحد الحين",color=0xe74c3c))
        e=discord.Embed(title="📦 نسخة احتياطية",description="هذي نسخة من قاعدة البيانات" if is_dm else "احفظ هذا الملف عندك.\n**للاستعادة:** ارفع الملف مع أمر `!استعادة`",color=0x3498db)
        e.add_field(name="الحجم",value=f"`{os.path.getsize(DB)/1024:.1f} KB`",inline=True)
        if not is_dm: e.add_field(name="التاريخ",value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>",inline=True)
        await dest.send(embed=e,file=discord.File(DB))
        if is_dm: await dest.send(embed=discord.Embed(description="✅ تم الإرسال على الخاص",color=0x2ecc71))
    except: await dest.send(embed=discord.Embed(description="❌ ما قدرت أرسل على الخاص. تأكد إنك فاتح الخاص" if is_dm else f"❌ صار خطأ",color=0xe74c3c))

@bot.command()
@commands.has_permissions(administrator=True)
async def نسخة(ctx): await ctx.send("📤 **جاري رفع النسخة الاحتياطية...**"); await send_backup(ctx)

@bot.command()
@commands.has_permissions(administrator=True)
async def استعادة(ctx):
    if not ctx.message.attachments or ctx.message.attachments[0].filename!="levels.db": return await ctx.send(embed=discord.Embed(description="❌ لازم ترفق ملف `levels.db` مع الرسالة" if not ctx.message.attachments else "❌ اسم الملف لازم يكون `levels.db` بالضبط",color=0xe74c3c))
    await ctx.message.attachments[0].save(DB); await ctx.send(embed=discord.Embed(title="✅ تم الاستعادة",description="تم استرجاع النسخة الاحتياطية...\n🔄 جاري إعادة تشغيل البوت الحين",color=0x2ecc71)); await asyncio.sleep(2); await bot.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def نسخة_خاص(ctx): await send_backup(ctx.author,is_dm=True)

@bot.command()
async def مساعدة(ctx):
    e=discord.Embed(title="📋 أوامر البوت",description="البادئة: `!`",color=0x3498db,timestamp=datetime.now(timezone.utc))
    e.add_field(name="🔹 عامة",value="`هلا` `بنق` `يوزر` `سيرفر` `تحذيراتي`",inline=False)
    e.add_field(name="⭐ اللفل",value="`لفل` `توب_اسبوع` `عط @عضو رقم` `خصم @عضو رقم`",inline=False)
    e.add_field(name="🛡️ الإدارة",value="`مسح` `ميوت` `فك` `طرد` `باند` `تحذير` `قفل` `فتح` `مسح_تحذيرات`",inline=False)
    e.add_field(name="💾 النسخ الاحتياطي",value="`نسخة` `استعادة` `نسخة_خاص`",inline=False)
    e.add_field(name="⚙️ الحماية التلقائية",value="• XP ذكي حسب طول الرسالة\n• حذف روابط + ميوت 5د\n• منع @everyone + ميوت 10د\n• فلتر سب + 3 تحذيرات = ميوت ساعة\n• منع السبام والمنشن الجماعي\n• نسخة تلقائية كل 12 ساعة بالخاص\n• لوق تلقائي للباند والطرد",inline=False)
    e.set_footer(text="بوت متكامل للحماية واللفل"); await ctx.send(embed=e)

bot.run(TOKEN)
