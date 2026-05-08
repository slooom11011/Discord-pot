import discord,os,asyncio,re,aiosqlite,pytz
from discord.ext import commands,tasks
from datetime import datetime,timezone,timedelta
from discord import app_commands
TOKEN=os.getenv("TOKEN")
C={"welcome":"شات-العام","log":"المخالفات","bye":"شات-العام","lvl_up":"لفل-اب","weekly":"توب-الاسبوع","rules":1500607707806433460,"new_role":["الأعضاء الجدد",0x95a5a6],"bad_role":["غير موثق",0xe74c3c],"lvl_roles":{1:["مبتدئ",0x95a5a6],5:["نشيط",0x3498db],10:["متفاعل",0x2ecc71],20:["أسطورة",0xf1c40f],50:["VIP",0xe74c3c]},"bad_words":["سب1","سب2","يا حيوان","ياحيوان","يا كلب","ياكلب","يامريض","كس امك","كسامك","كل زق","كلزق"],"owner_id":763363479960682506,"tasks":{"msg":{"name":"سوالف اليوم","desc":"أرسل 15 رسالة","goal":15,"reward":75},"react":{"name":"المتفاعل","desc":"3 ردة فعل","goal":3,"reward":25},"voice":{"name":"حيّ الفويس","desc":"5 دقايق فويس","goal":5,"reward":100}}}
warns,xp_cd,spam,voice_time={},{},{},{}
DB='levels.db'
calc_lvl=lambda x:int(((-50+(2500+200*x)**0.5)//100))
next_xp=lambda l:50*(l**2)+50*l
def progress(xp,l,bl=10):
 if l==0:return "█"*bl,100
 p,n=next_xp(l-1),next_xp(l);need,have=n-p,xp-p
 if have<0:have=0
 if need<=0:need=1
 prog=min(int((have/need)*bl),bl)
 return "█"*prog+"░"*(bl-prog),min(int((have/need)*100),100)
db=lambda:aiosqlite.connect(DB)
async def db_init():
 async with await db() as c:await c.executescript('CREATE TABLE IF NOT EXISTS levels(guild_id TEXT,user_id TEXT,xp INTEGER DEFAULT 0,level INTEGER DEFAULT 0,weekly_xp INTEGER DEFAULT 0,PRIMARY KEY(guild_id,user_id));CREATE TABLE IF NOT EXISTS tasks(guild_id TEXT,user_id TEXT,task_id TEXT,progress INTEGER DEFAULT 0,completed INTEGER DEFAULT 0,last_reset TEXT,PRIMARY KEY(guild_id,user_id,task_id))');await c.commit()
async def get_data(g,u):
 async with await db() as c:r=await(await c.execute('SELECT xp,level,weekly_xp FROM levels WHERE guild_id=? AND user_id=?',(g,u))).fetchone()
 return {"xp":r[0],"level":r[1],"weekly_xp":r[2]} if r else {"xp":0,"level":0,"weekly_xp":0}
async def save_data(g,u,xp,lvl,wxp):
 async with await db() as c:await c.execute('INSERT INTO levels VALUES(?,?,?,?,?) ON CONFLICT(guild_id,user_id)DO UPDATE SET xp=?,level=?,weekly_xp=?',(g,u,xp,lvl,wxp,xp,lvl,wxp));await c.commit()
async def get_task(g,u,tid):
 today=datetime.now(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d')
 async with await db() as c:
  r=await(await c.execute('SELECT progress,completed,last_reset FROM tasks WHERE guild_id=? AND user_id=? AND task_id=?',(g,u,tid))).fetchone()
  if not r or r[2]!=today:await c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?)ON CONFLICT(guild_id,user_id,task_id)DO UPDATE SET progress=0,completed=0,last_reset=?',(g,u,tid,0,0,today,today));await c.commit();return{"progress":0,"completed":0}
  return{"progress":r[0],"completed":r[1]}
async def update_task(g,u,tid,a=1):
 t=await get_task(g,u,tid)
 if t["completed"]:return False,0
 np=t["progress"]+a;goal=C["tasks"][tid]["goal"];comp=1 if np>=goal else 0;rew=C["tasks"][tid]["reward"] if comp else 0
 async with await db() as c:await c.execute('UPDATE tasks SET progress=?,completed=? WHERE guild_id=? AND user_id=? AND task_id=?',(min(np,goal),comp,g,u,tid));await c.commit()
 return comp,rew
async def add_xp(g,u,a):
 d=await get_data(g,u);xp,lvl,wxp=d["xp"]+a,d["level"],d["weekly_xp"]+a;nlvl=calc_lvl(xp);await save_data(g,u,xp,nlvl,wxp);return nlvl>lvl,xp,nlvl
async def get_role(g,n,c=None):
 r=discord.utils.get(g.roles,name=n)
 if not r and c:
  try:r=await g.create_role(name=n,color=c)
  except:pass
 return r
async def update_role(m,lvl):
 try:
  old=[r for r in m.roles if r.name in[d[0]for d in C["lvl_roles"].values()]]
  if old:await m.remove_roles(*old)
  for lv,(n,c) in sorted(C["lvl_roles"].items(),reverse=True):
   if lvl>=lv:
    r=await get_role(m.guild,n,c)
    if r:await m.add_roles(r);return r
 except:pass
async def announce_level_up(m,xp,nlvl):
 ch=discord.utils.get(m.guild.channels,name=C["lvl_up"])
 if not ch:return
 bar,p=progress(xp,nlvl);e=discord.Embed(title="🎉 LEVEL UP!",description=f'**{m.mention}** وصل **لفل {nlvl}** 🚀',color=0xf1c40f,timestamp=datetime.now(timezone.utc));e.set_thumbnail(url=m.display_avatar.url)
 e.add_field(name="📊 XP الحالي",value=f'`{xp:,}`',inline=True);e.add_field(name="⭐ اللفل الجديد",value=f'`{nlvl}`',inline=True);e.add_field(name="🎯 للفل الجاي",value=f'`{next_xp(nlvl)-xp:,} XP`',inline=True);e.add_field(name="التقدم",value=f'`{bar}` {p}%',inline=False)
 nr=await update_role(m,nlvl)
 if nr:e.add_field(name="🎊 رتبة جديدة",value=f"مبروك حصلت على {nr.mention}",inline=False)
 try:await ch.send(embed=e)
 except:pass
async def temp_mute(m,s,reason):
 r=await get_role(m.guild,"Muted")
 if not r:return
 for ch in m.guild.channels:
  try:await ch.set_permissions(r,send_messages=False,add_reactions=False)
  except:pass
 await m.add_roles(r,reason=reason);await asyncio.sleep(s);await m.remove_roles(r)
async def log_send(g,title,color,**f):
 if ch:=discord.utils.get(g.channels,name=C["log"]):
  e=discord.Embed(title=title,color=color,timestamp=datetime.now(timezone.utc))
  [e.add_field(name=k,value=v,inline=i)for k,v,i in f.get("fields",[])]
  if t:=f.get("thumb"):e.set_thumbnail(url=t)
  try:await ch.send(embed=e)
  except:pass
bot=commands.Bot(command_prefix="!",intents=discord.Intents.all())
@tasks.loop(time=datetime.strptime("00:00","%H:%M").time())
async def reset_daily_tasks():print("[TASKS] تصفير المهام اليومية")
@tasks.loop(time=datetime.strptime("12:00","%H:%M").time())
async def weekly_top():
 if datetime.now(pytz.timezone('Asia/Riyadh')).weekday()!=4:return
 for g in bot.guilds:
  if not(ch:=discord.utils.get(g.channels,name=C["weekly"])):continue
  async with await db()as c:top=await(await c.execute('SELECT user_id,weekly_xp,level FROM levels WHERE guild_id=? AND weekly_xp>0 ORDER BY weekly_xp DESC LIMIT 10',(str(g.id),))).fetchall()
  if not top:await ch.send(embed=discord.Embed(title="😴 لا يوجد متفاعلين",description="مافي أحد جمع XP هذا الأسبوع",color=0x95a5a6));continue
  e=discord.Embed(title="🏆 توب 10 لهذا الأسبوع",color=0xf1c40f,timestamp=datetime.now(timezone.utc));e.set_thumbnail(url=g.icon.url if g.icon else None)
  medals=["🥇","🥈","🥉"];e.description="".join([f"{medals[i] if i<3 else f'**{i+1}.**'} <@{u}>\n└ `{x:,} XP` • لفل `{l}`\n\n"for i,(u,x,l)in enumerate(top)])
  await ch.send(embed=e)
  async with await db()as c:await c.execute('UPDATE levels SET weekly_xp=0 WHERE guild_id=?',(str(g.id),));await c.commit()
@tasks.loop(hours=12)
async def auto_backup():
 if not C["owner_id"]or not os.path.exists(DB):return
 try:u=await bot.fetch_user(C["owner_id"]);e=discord.Embed(title="📦 نسخة احتياطية تلقائية",color=0x3498db);e.add_field(name="الحجم",value=f"`{os.path.getsize(DB)/1024:.1f} KB`",inline=True);await u.send(embed=e,file=discord.File(DB))
 except:pass
@tasks.loop(minutes=1)
async def check_voice_tasks():
 try:
  for g in bot.guilds:
   for vc in g.voice_channels:
    for m in vc.members:
     if m.bot:continue
     uid,gid=str(m.id),str(g.id)
     if uid not in voice_time:voice_time[uid]=datetime.now(timezone.utc)
     elif(datetime.now(timezone.utc)-voice_time[uid]).seconds>=60:
      comp,rew=await update_task(gid,uid,"voice")
      if rew:leveled,xp,nlvl=await add_xp(gid,uid,rew)
      if leveled:await announce_level_up(m,xp,nlvl)
      voice_time[uid]=datetime.now(timezone.utc)
 except:pass
@bot.event
async def on_ready():
 await db_init();print(f'[READY] {bot.user}')
 try:synced=await bot.tree.sync();print(f'تم تسجيل {len(synced)} أمر سلاش')
 except Exception as e:print(f'خطأ تسجيل السلاش: {e}')
 reset_daily_tasks.start();weekly_top.start();auto_backup.start();check_voice_tasks.start()
@bot.event
async def on_member_join(m):
 try:
  if(datetime.now(timezone.utc)-m.created_at).days<7:
   r=await get_role(m.guild,C["bad_role"][0],C["bad_role"][1]);[await ch.set_permissions(r,send_messages=False)for ch in m.guild.channels];await m.add_roles(r);await log_send(m.guild,"⚠️ حساب جديد مشبوه",0xe67e22,fields=[("العضو",m.mention,True),("عمر الحساب",f"`{(datetime.now(timezone.utc)-m.created_at).days} يوم`",True)],thumb=m.avatar.url if m.avatar else m.default_avatar.url);return
  r=await get_role(m.guild,C["new_role"][0],C["new_role"][1]);await m.add_roles(r)
  if ch:=discord.utils.get(m.guild.channels,name=C["welcome"]):
   e=discord.Embed(title="🌟 عضو جديد نورتنا",description=f'**أهلاً وسهلاً {m.mention}**\nنورت **{m.guild.name}**\n\nتم إعطائك رول {r.mention}',color=0x2ecc71,timestamp=datetime.now(timezone.utc));e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url);e.add_field(name="رقم العضو",value=f'`#{m.guild.member_count}`',inline=True);e.add_field(name="تاريخ الإنضمام",value=f'<t:{int(m.joined_at.timestamp())}:R>',inline=True);e.add_field(name="📜 القوانين",value=f"قبل ما تبدأ تأكد تقرأ <#{C['rules']}>",inline=False)
   await ch.send(embed=e)
 except:pass
@bot.event
async def on_member_remove(m):
 try:
  if str(m.id)in voice_time:del voice_time[str(m.id)]
  if ch:=discord.utils.get(m.guild.channels,name=C["bye"]):
   e=discord.Embed(title="💔 عضو غادرنا",description=f'**{m.name}** طلع من السيرفر',color=0xe74c3c,timestamp=datetime.now(timezone.utc));e.set_thumbnail(url=m.avatar.url if m.avatar else m.default_avatar.url);e.add_field(name="عدد الأعضاء الآن",value=f'`{m.guild.member_count}`',inline=True)
   await ch.send(embed=e)
 except:pass
@bot.event
async def on_member_ban(g,u):
 try:await log_send(g,"🔨 تم تبنيد عضو",0x992d22,fields=[("العضو",f"{u.mention}\n`{u.name}`",True)],thumb=u.avatar.url if u.avatar else u.default_avatar.url)
 except:pass
@bot.event
async def on_voice_state_update(m,before,after):
 try:
  if m.bot:return
  uid=str(m.id)
  if before.channel is None and after.channel is not None:voice_time[uid]=datetime.now(timezone.utc)
  elif before.channel is not None and after.channel is None:
   if uid in voice_time:del voice_time[uid]
 except:pass
@bot.event
async def on_reaction_add(reaction,user):
 try:
  if user.bot or not reaction.message.guild:return
  gid,uid=str(reaction.message.guild.id),str(user.id)
  comp,rew=await update_task(gid,uid,"react")
  if rew:leveled,xp,nlvl=await add_xp(gid,uid,rew)
  if leveled:await announce_level_up(user,xp,nlvl)
 except:pass
@bot.event
async def on_message(msg):
 try:
  if msg.author.bot:return
  if re.search(r'discord.(gg|com/invite)',msg.content.lower())and not msg.author.guild_permissions.manage_messages:await msg.delete();asyncio.create_task(temp_mute(msg.author,300,"نشر رابط"));return
  if msg.mention_everyone and not msg.author.guild_permissions.mention_everyone:await msg.delete();asyncio.create_task(temp_mute(msg.author,600,"منشن everyone"));return
  if len(msg.mentions)>=5 and not msg.author.guild_permissions.mention_everyone:await msg.delete();return
  spam.setdefault(msg.author.id,[]).append(msg.content)
  if len(spam[msg.author.id])>5:spam[msg.author.id].pop(0)
  if spam[msg.author.id].count(msg.content)>=4 and not msg.author.guild_permissions.manage_messages:await msg.delete();return
  gid,uid=str(msg.guild.id),str(msg.author.id)
  comp,rew=await update_task(gid,uid,"msg")
  if rew:leveled,xp,nlvl=await add_xp(gid,uid,rew)
  if leveled:await announce_level_up(msg.author,xp,nlvl)
  if uid not in xp_cd or(datetime.now(timezone.utc)-xp_cd[uid]).seconds>=60:
   xp_cd[uid]=datetime.now(timezone.utc);xp_gain=min(len(msg.content)//10,5)if len(msg.content)>5 else 1;leveled,xp,nlvl=await add_xp(gid,uid,xp_gain)
   if leveled:await announce_level_up(msg.author,xp,nlvl)
  for w in C["bad_words"]:
   if w in msg.content.lower():
    await msg.delete();warns[msg.author.id]=warns.get(msg.author.id,0)+1
    if warns[msg.author.id]>=3:asyncio.create_task(temp_mute(msg.author,3600,"سب"));warns[msg.author.id]=0;await msg.channel.send(f"🔇 {msg.author.mention} ميوت ساعة")
    else:await msg.channel.send(f"⚠️ {msg.author.mention} تحذير {warns[msg.author.id]}/3",delete_after=5)
    await log_send(msg.guild,"🚫 تم حذف رسالة سيئة",0xff0000,fields=[("العضو",msg.author.mention,True),("التحذيرات",f"`{warns[msg.author.id]}/3`",True),("الكلمة المحظورة",f"||{w}||",False)]);return
  await bot.process_commands(msg)
 except:pass
@bot.tree.error
async def on_app_command_error(i,e):
 if isinstance(e,app_commands.MissingPermissions):await i.response.send_message(embed=discord.Embed(description="❌ ما عندك صلاحية",color=0xe74c3c),ephemeral=True)
 elif not i.response.is_done():await i.response.send_message(embed=discord.Embed(description="❌ صار خطأ",color=0xe74c3c),ephemeral=True)
@bot.tree.command(name="مهام",description="يعرض مهامك اليومية")
async def مهام(i:discord.Interaction):
 g,u=str(i.guild.id),str(i.user.id);e=discord.Embed(title="📋 مهامك اليومية",color=0x3498db);e.set_thumbnail(url=i.user.display_avatar.url)
 now=datetime.now(pytz.timezone('Asia/Riyadh'));rt=now.replace(hour=0,minute=0,second=0)+timedelta(days=1);diff=rt-now;h,m=divmod(diff.seconds,3600);m,_=divmod(m,60);e.set_footer(text=f"تصفر بعد {h} ساعة و {m} دقيقة")
 for tid,d in C["tasks"].items():
  t=await get_task(g,u,tid);p,gol=t["progress"],d["goal"];per=int((p/gol)*10);bar="█"*per+"░"*(10-per);s="✅" if t["completed"] else ""
  e.add_field(name=f'{d["name"]} {s}',value=f'{d["desc"]}\nالتقدم: `[{bar}] {p}/{gol}`\nالمكافأة: `+{d["reward"]} XP`',inline=False)
 await i.response.send_message(embed=e,ephemeral=True)
@bot.tree.command(name="هلا",description="يسلم عليك")
async def هلا(i:discord.Interaction):await i.response.send_message(f"هلا والله {i.user.mention} 👋")
@bot.tree.command(name="بنق",description="يعرض سرعة البوت")
async def بنق(i:discord.Interaction):await i.response.send_message(embed=discord.Embed(title="🏓 البنق",description=f'**`{round(bot.latency*1000)}ms`**',color=0x2ecc71 if bot.latency<0.1 else 0xe67e22))
@bot.tree.command(name="لفل",description="يعرض لفلك أو لفل عضو")
@app_commands.describe(العضو="العضو")
async def لفل(i:discord.Interaction,العضو:discord.Member=None):
 m=العضو or i.user;d=await get_data(str(i.guild.id),str(m.id))
 if not d["xp"]:return await i.response.send_message(embed=discord.Embed(description=f"❌ {m.mention} ما عنده XP",color=0xe74c3c),ephemeral=True)
 e=discord.Embed(title=f"⭐ لفل {m.display_name}",color=0x3498db);e.set_thumbnail(url=m.display_avatar.url);bar,p=progress(d["xp"],d["level"],15)
 e.add_field(name="اللفل",value=f'`{d["level"]}`',inline=True);e.add_field(name="XP",value=f'`{d["xp"]:,}/{next_xp(d["level"]):,}`',inline=True);e.add_field(name="باقي",value=f'`{next_xp(d["level"])-d["xp"]:,} XP`',inline=True);e.add_field(name="التقدم",value=f'`{bar}` {p}%',inline=False)
 await i.response.send_message(embed=e)
@bot.tree.command(name="توب",description="يعرض أفضل 10 أعضاء")
async def توب(i:discord.Interaction):
 async with await db()as c:top=await(await c.execute('SELECT user_id,xp,level FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT 10',(str(i.guild.id),))).fetchall()
 if not top:return await i.response.send_message(embed=discord.Embed(description="❌ مافي أحد عنده XP",color=0xe74c3c),ephemeral=True)
 e=discord.Embed(title=f"🏆 توب 10 في {i.guild.name}",color=0xf1c40f);e.set_thumbnail(url=i.guild.icon.url if i.guild.icon else None);medals=["🥇","🥈","🥉"];e.description="".join([f"{medals[j]if j<3 else f'**{j+1}.**'} <@{u}>\n└ لفل `{l}` • `{x:,}` XP\n\n"for j,(u,x,l)in enumerate(top)])
 await i.response.send_message(embed=e)
@bot.tree.command(name="توب_اسبوع",description="يعرض توب الأسبوع")
async def توب_اسبوع(i:discord.Interaction):
 async with await db()as c:top=await(await c.execute('SELECT user_id,weekly_xp,level FROM levels WHERE guild_id=? AND weekly_xp>0 ORDER BY weekly_xp DESC LIMIT 10',(str(i.guild.id),))).fetchall()
 if not top:return await i.response.send_message(embed=discord.Embed(title="😴 لا يوجد متفاعلين",description="مافي أحد جمع XP هذا الأسبوع",color=0x95a5a6),ephemeral=True)
 e=discord.Embed(title="🏆 توب 10 لهذا الأسبوع",color=0xf1c40f);medals=["🥇","🥈","🥉"];e.description="".join([f"{medals[j]if j<3 else f'**{j+1}.**'} <@{u}>\n└ `{x:,}` XP • لفل `{l}`\n\n"for j,(u,x,l)in enumerate(top)])
 await i.response.send_message(embed=e)
@bot.tree.command(name="عط",description="يعطي XP لعضو")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(العضو="العضو",الكمية="كم XP")
async def عط(i:discord.Interaction,العضو:discord.Member,الكمية:int):
 if الكمية<=0:return await i.response.send_message(embed=discord.Embed(description="❌ الكمية لازم أكبر من صفر",color=0xe74c3c),ephemeral=True)
 g,u=str(i.guild.id),str(العضو.id);leveled,xp,nlvl=await add_xp(g,u,الكمية);e=discord.Embed(title="✅ تم إعطاء XP",description=f"تم إعطاء {العضو.mention} **{الكمية:,} XP**",color=0x2ecc71);e.add_field(name="اللفل الحالي",value=f'`{nlvl}`',inline=True);e.add_field(name="XP الكلي",value=f'`{xp:,}`',inline=True)
 if leveled:await announce_level_up(العضو,xp,nlvl);r=await update_role(العضو,nlvl)
 if r:e.add_field(name="🎊 رتبة جديدة",value=f"{r.mention}",inline=True)
 await i.response.send_message(embed=e)
@bot.tree.command(name="خصم",description="يخصم XP من عضو")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(العضو="العضو",الكمية="كم XP")
async def خصم(i:discord.Interaction,العضو:discord.Member,الكمية:int):
 if الكمية<=0:return await i.response.send_message(embed=discord.Embed(description="❌ الكمية لازم أكبر من صفر",color=0xe74c3c),ephemeral=True)
 g,u=str(i.guild.id),str(العضو.id);d=await get_data(g,u)
 if not d["xp"]:return await i.response.send_message(embed=discord.Embed(description=f"❌ {العضو.mention} ما عنده XP",color=0xe74c3c),ephemeral=True)
 xp=max(0,d["xp"]-الكمية);wxp=max(0,d["weekly_xp"]-الكمية);nlvl=calc_lvl(xp);await save_data(g,u,xp,nlvl,wxp)
 if nlvl!=d["level"]:await update_role(العضو,nlvl)
 e=discord.Embed(title="✅ تم خصم XP",description=f"تم خصم **{الكمية:,} XP** من {العضو.mention}",color=0xe67e22);e.add_field(name="اللفل الحالي",value=f'`{nlvl}`',inline=True);e.add_field(name="XP الكلي",value=f'`{xp:,}`',inline=True)
 await i.response.send_message(embed=e)
@bot.tree.command(name="مسح",description="يمسح رسائل")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(العدد="عدد الرسائل 1-100")
async def مسح(i:discord.Interaction,العدد:int):
 if not 0<العدد<=100:return await i.response.send_message(embed=discord.Embed(description="❌ العدد لازم بين 1 و 100",color=0xe74c3c),ephemeral=True)
 await i.response.defer(ephemeral=True);d=await i.channel.purge(limit=العدد);await i.followup.send(embed=discord.Embed(description=f"✅ تم مسح `{len(d)}` رسالة",color=0x2ecc71),ephemeral=True)
@bot.tree.command(name="ميوت",description="يعطي ميوت لعضو")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(العضو="العضو",الدقائق="مدة الميوت",السبب="سبب الميوت")
async def ميوت(i:discord.Interaction,العضو:discord.Member,الدقائق:int,السبب:str="مافي سبب"):
 await temp_mute(العضو,الدقائق*60,السبب);await i.response.send_message(embed=discord.Embed(title="🔇 تم إعطاء ميوت",description=f"{العضو.mention} لمدة `{الدقائق}` دقيقة\n**السبب:** {السبب}",color=0xe74c3c))
@bot.tree.command(name="فك",description="يفك الميوت عن عضو")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(العضو="العضو")
async def فك(i:discord.Interaction,العضو:discord.Member):
 if r:=discord.utils.get(i.guild.roles,name="Muted"):await العضو.remove_roles(r)
 await i.response.send_message(embed=discord.Embed(description=f"✅ تم فك الميوت عن {العضو.mention}",color=0x2ecc71))
@bot.tree.command(name="طرد",description="يطرد عضو")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(العضو="العضو",السبب="سبب الطرد")
async def طرد(i:discord.Interaction,العضو:discord.Member,السبب:str="مافي سبب"):
 await العضو.kick(reason=السبب);await log_send(i.guild,"👢 تم طرد عضو",0xe74c3c,fields=[("العضو",f"{العضو.mention}",True),("المشرف",i.user.mention,True),("السبب",السبب,False)]);await i.response.send_message(embed=discord.Embed(description=f"👢 تم طرد {العضو.mention}\n**السبب:** {السبب}",color=0xe74c3c))
@bot.tree.command(name="باند",description="يبند عضو")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(العضو="العضو",السبب="سبب الباند")
async def باند(i:discord.Interaction,العضو:discord.Member,السبب:str="مافي سبب"):await العضو.ban(reason=السبب);await i.response.send_message(embed=discord.Embed(description=f"🔨 تم تبنيد {العضو.mention}\n**السبب:** {السبب}",color=0x992d22))
@bot.tree.command(name="قفل",description="يقفل كل الرومات")
@app_commands.checks.has_permissions(administrator=True)
async def قفل(i:discord.Interaction):await i.response.defer();[await ch.set_permissions(i.guild.default_role,send_messages=False)for ch in i.guild.text_channels];await i.followup.send(embed=discord.Embed(title="🔒 تم قفل السيرفر",description="للفتح استخدم `/فتح`",color=0xe74c3c))
@bot.tree.command(name="فتح",description="يفتح كل الرومات")
@app_commands.checks.has_permissions(administrator=True)
async def فتح(i:discord.Interaction):await i.response.defer();[await ch.set_permissions(i.guild.default_role,send_messages=True)for ch in i.guild.text_channels];await i.followup.send(embed=discord.Embed(title="🔓 تم فتح السيرفر",color=0x2ecc71))
@bot.tree.command(name="تحذير",description="يعطي تحذير لعضو")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(العضو="العضو",السبب="سبب التحذير")
async def تحذير(i:discord.Interaction,العضو:discord.Member,السبب:str="مافي سبب"):
 warns[العضو.id]=warns.get(العضو.id,0)+1;await i.response.send_message(embed=discord.Embed(description=f"⚠️ تم تحذير {العضو.mention} | `{warns[العضو.id]}/3`\n**السبب:** {السبب}",color=0xe67e22));await log_send(i.guild,"⚠️ تم تحذير عضو",0xe67e22,fields=[("العضو",العضو.mention,True),("المشرف",i.user.mention,True),("التحذيرات",f"`{warns[العضو.id]}/3`",True),("السبب",السبب,False)])
 if warns[العضو.id]>=3:await temp_mute(العضو,3600,"وصل 3 تحذيرات");warns[العضو.id]=0;await i.followup.send(f"🔇 {العضو.mention} ميوت ساعة")
@bot.tree.command(name="تحذيراتي",description="يعرض تحذيراتك")
async def تحذيراتي(i:discord.Interaction):await i.response.send_message(embed=discord.Embed(description=f"⚠️ عندك `{warns.get(i.user.id,0)}/3` تحذير",color=0xe67e22),ephemeral=True)
@bot.tree.command(name="مسح_تحذيرات",description="يمسح تحذيرات عضو")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(العضو="العضو")
async def مسح_تحذيرات(i:discord.Interaction,العضو:discord.Member):warns[العضو.id]=0;await i.response.send_message(embed=discord.Embed(description=f"✅ تم مسح تحذيرات {العضو.mention}",color=0x2ecc71))
async def send_backup(dest,is_dm=False):
 try:
  if not os.path.exists(DB):return await dest.send(embed=discord.Embed(description="❌ ملف قاعدة البيانات ما انشئ",color=0xe74c3c))
  e=discord.Embed(title="📦 نسخة احتياطية",description="هذي نسخة من قاعدة البيانات"if is_dm else"احفظ هذا الملف عندك.\n**للاستعادة:** ارفع الملف مع أمر `/استعادة`",color=0x3498db);e.add_field(name="الحجم",value=f"`{os.path.getsize(DB)/1024:.1f} KB`",inline=True)
  if not is_dm:e.add_field(name="التاريخ",value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>",inline=True)
  await dest.send(embed=e,file=discord.File(DB))
  if is_dm:await dest.send(embed=discord.Embed(description="✅ تم الإرسال على الخاص",color=0x2ecc71))
 except Exception as err:await dest.send(embed=discord.Embed(description=f"❌ صار خطأ: {err}",color=0xe74c3c))
@bot.tree.command(name="نسخة",description="يرسل نسخة احتياطية هنا")
@app_commands.checks.has_permissions(administrator=True)
async def نسخة(i:discord.Interaction):await i.response.send_message("📤 **جاري رفع النسخة الاحتياطية...**");await send_backup(i.channel)
@bot.tree.command(name="استعادة",description="يستعيد نسخة احتياطية")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(ملف="ارفع ملف levels.db")
async def استعادة(i:discord.Interaction,ملف:discord.Attachment):
 if ملف.filename!="levels.db":return await i.response.send_message(embed=discord.Embed(description="❌ اسم الملف لازم يكون `levels.db`",color=0xe74c3c),ephemeral=True)
 await ملف.save(DB);await i.response.send_message(embed=discord.Embed(title="✅ تم الاستعادة",description="تم استرجاع النسخة الاحتياطية...\n🔄 جاري إعادة تشغيل البوت",color=0x2ecc71));await asyncio.sleep(2);await bot.close()
@bot.tree.command(name="نسخة_خاص",description="يرسل لك نسخة احتياطية خاص")
@app_commands.checks.has_permissions(administrator=True)
async def نسخة_خاص(i:discord.Interaction):await i.response.send_message("📤 جاري الإرسال...",ephemeral=True);await send_backup(i.user,is_dm=True)
@bot.tree.command(name="مساعدة",description="يعرض كل أوامر البوت")
async def مساعدة(i:discord.Interaction):
    e=discord.Embed(title="📋 أوامر البوت",description="كل الأوامر الآن سلاش `/`",color=0x3498db,timestamp=datetime.now(timezone.utc))
    e.add_field(name="🔹 عامة",value="`/هلا` `/بنق` `/لفل` `/توب` `/توب_اسبوع` `/مهام` `/تحذيراتي`",inline=False)
    e.add_field(name="⭐ إدارة XP",value="`/عط` `/خصم`",inline=False)
    e.add_field(name="🛡️ الإدارة",value="`/مسح` `/ميوت` `/فك` `/طرد` `/باند` `/تحذير` `/قفل` `/فتح` `/مسح_تحذيرات`",inline=False)
    e.add_field(name="💾 النسخ الاحتياطي",value="`/نسخة` `/استعادة` `/نسخة_خاص`",inline=False)
    e.add_field(name="⚙️ الحماية التلقائية",value="• XP ذكي حسب طول الرسالة\n• نظام مهام يومية + مكافآت\n• حذف روابط + ميوت 5د\n• منع @everyone + ميوت 10د\n• فلتر سب + 3 تحذيرات = ميوت ساعة\n• منع السبام والمنشن الجماعي\n• نسخة تلقائية كل 12 ساعة بالخاص\n• لوق تلقائي للباند والطرد",inline=False)
    e.set_footer(text="بوت متكامل للحماية واللفل والمهام")
    await i.response.send_message(embed=e)

bot.run(TOKEN)
