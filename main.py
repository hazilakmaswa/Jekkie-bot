import discord
from discord.ext import commands
import os
import time
from flask import Flask, jsonify
import threading

# ============ ENV ============
TOKEN = os.getenv("TOKEN")
if not TOKEN or len(TOKEN) < 20:
    raise SystemExit("❌ TOKEN environment variable missing/invalid (set di Railway Variables)")

# ============ BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

source_id, target_id, invite_id, log_id = None, None, None, None
mirror_active, invite_active = True, True
message_map, invites_cache = {}, {}
voice_channel_id = None
vc_client = None
START_TIME = time.time()

# ============ FLASK (Railway health) ============
app = Flask(__name__)

@app.route('/')
def home():
    return f"<h1>Jekkie-Bot Online</h1><p>Mirror: {mirror_active} | Invite: {invite_active} | Logs: {log_id}</p>"

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "bot": str(bot.user) if bot.user else None,
        "uptime_seconds": int(time.time() - START_TIME),
        "mirror": mirror_active,
        "invite": invite_active,
    })

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# ============ HELPERS ============
def embed(t, d, c=0x2B2D31):
    e = discord.Embed(title=t, description=d, color=c)
    e.set_footer(text="Jekkie • Premium access")
    return e
def success(t, d): return embed(t, d, c=0x57F287)
def failed(t, d): return embed(t, d, c=0xED4245)

# ============ COMMANDS ============
@bot.tree.command(name="setsource", description="Set source channel for mirroring")
async def setsource(interaction: discord.Interaction, channel: discord.TextChannel):
    global source_id
    source_id = channel.id
    await interaction.response.send_message(embed=success("📌 Source Set", f"Mirroring from {channel.mention}"), ephemeral=True)

@bot.tree.command(name="settarget", description="Set target channel for mirroring")
async def settarget(interaction: discord.Interaction, channel: discord.TextChannel):
    global target_id
    target_id = channel.id
    await interaction.response.send_message(embed=success("📤 Target Set", f"Mirroring to {channel.mention}"), ephemeral=True)

@bot.tree.command(name="setinvite", description="Set invite tracker log channel")
async def setinvite(interaction: discord.Interaction, channel: discord.TextChannel):
    global invite_id
    invite_id = channel.id
    await interaction.response.send_message(embed=success("📝 Invite Log Set", f"Invite logs will be sent to {channel.mention}"), ephemeral=True)

@bot.tree.command(name="setlog", description="Set main logs channel like Dyno")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    global log_id
    log_id = channel.id
    await interaction.response.send_message(embed=success("📜 Logs Set", f"Logs will be sent to {channel.mention}"), ephemeral=True)

@bot.tree.command(name="start_mirror", description="Enable chat mirroring")
async def start_mirror(interaction: discord.Interaction):
    global mirror_active
    mirror_active = True
    await interaction.response.send_message(embed=success("✅ Mirror Enabled", "Chat mirroring is now ON"), ephemeral=True)

@bot.tree.command(name="stop_mirror", description="Disable chat mirroring")
async def stop_mirror(interaction: discord.Interaction):
    global mirror_active
    mirror_active = False
    await interaction.response.send_message(embed=failed("⏸️ Mirror Disabled", "Chat mirroring is now OFF"), ephemeral=True)

@bot.tree.command(name="start_invite", description="Enable invite tracking")
async def start_invite(interaction: discord.Interaction):
    global invite_active
    invite_active = True
    await interaction.response.send_message(embed=success("✅ Invite Tracker ON", "Invite tracking enabled"), ephemeral=True)

@bot.tree.command(name="stop_invite", description="Disable invite tracking")
async def stop_invite(interaction: discord.Interaction):
    global invite_active
    invite_active = False
    await interaction.response.send_message(embed=failed("⏸️ Invite Tracker OFF", "Invite tracking disabled"), ephemeral=True)

@bot.tree.command(name="stoplog", description="Disable main logs")
async def stoplog(interaction: discord.Interaction):
    global log_id
    log_id = None
    await interaction.response.send_message(embed=success("✅ Logs OFF", "Logging disabled"), ephemeral=True)

@bot.tree.command(name="setvoice", description="Set 24/7 voice channel")
async def setvoice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    global voice_channel_id
    voice_channel_id = channel.id
    await interaction.response.send_message(embed=success("🔊 Voice Channel Set", f"Set to {channel.mention}, use /joinvoice"), ephemeral=True)

@bot.tree.command(name="joinvoice", description="Join voice channel 24/7")
async def joinvoice(interaction: discord.Interaction):
    global vc_client
    if not voice_channel_id:
        return await interaction.response.send_message(embed=failed("❌ Failed", "Set voice channel first with /setvoice"), ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try:
        ch = bot.get_channel(voice_channel_id)
        if vc_client and vc_client.is_connected():
            await vc_client.move_to(ch)
        else:
            vc_client = await ch.connect(self_deaf=True)
        await interaction.followup.send(embed=success("✅ Joined Voice", f"Staying 24/7 in {ch.mention}"), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=failed("❌ Error", str(e)), ephemeral=True)

@bot.tree.command(name="leavevoice", description="Leave voice channel")
async def leavevoice(interaction: discord.Interaction):
    global vc_client
    if vc_client and vc_client.is_connected():
        await vc_client.disconnect()
        vc_client = None
        await interaction.response.send_message(embed=success("👋 Left Voice", "Disconnected from voice"), ephemeral=True)
    else:
        await interaction.response.send_message(embed=failed("❌ Failed", "Not in voice"), ephemeral=True)

@bot.tree.command(name="status", description="Check bot status")
async def status_cmd(interaction: discord.Interaction):
    txt = (
        f"Source: <#{source_id}>\n"
        f"Target: <#{target_id}>\n"
        f"Invite: <#{invite_id}>\n"
        f"Logs: <#{log_id}>\n"
        f"Voice: <#{voice_channel_id}>\n"
        f"Mirror: {mirror_active}\n"
        f"Invite Tracker: {invite_active}"
    )
    await interaction.response.send_message(embed=success("📊 Bot Status", txt), ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency and status")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    if latency < 100:
        color, status = 0x57F287, "🟢 Excellent"
    elif latency < 200:
        color, status = 0xFEE75C, "🟡 Good"
    else:
        color, status = 0xED4245, "🔴 Slow"

    uptime_sec = int(time.time() - START_TIME)
    hours, rem = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(rem, 60)

    e = discord.Embed(title="🏓 Pong!", color=color, timestamp=discord.utils.utcnow())
    e.add_field(name="📡 WebSocket Ping", value=f"**{latency}ms**\n{status}", inline=True)
    e.add_field(name="⏱️ Uptime", value=f"`{hours}h {minutes}m {seconds}s`", inline=True)
    e.add_field(name="💾 Status", value=f"Mirror: {'ON' if mirror_active else 'OFF'}\nTracker: {'ON' if invite_active else 'OFF'}", inline=True)
    e.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
    await interaction.response.send_message(embed=e)

# ============ EVENTS ============
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    for guild in bot.guilds:
        try:
            invites_cache[guild.id] = {i.code: i.uses for i in await guild.invites()}
        except Exception as e:
            print(f"invite cache error {guild.id}: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"sync error: {e}")

@bot.event
async def on_invite_create(invite):
    try:
        invites_cache[invite.guild.id] = {i.code: i.uses for i in await invite.guild.invites()}
    except Exception:
        pass

@bot.event
async def on_invite_delete(invite):
    try:
        invites_cache[invite.guild.id] = {i.code: i.uses for i in await invite.guild.invites()}
    except Exception:
        pass

@bot.event
async def on_member_join(member):
    if not invite_active or not invite_id:
        return
    try:
        ch = bot.get_channel(invite_id)
        if not ch:
            return
        old = invites_cache.get(member.guild.id, {})
        new_invites = await member.guild.invites()
        inviter = None
        for inv in new_invites:
            if inv.code in old and inv.uses > old[inv.code]:
                inviter = inv.inviter
                break
            elif inv.code not in old:
                inviter = inv.inviter
                break
        invites_cache[member.guild.id] = {i.code: i.uses for i in new_invites}

        e = discord.Embed(title="Member Joined", color=0x57F287, timestamp=discord.utils.utcnow())
        e.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
        e.add_field(name="Member", value=f"{member.mention} `{member.id}`", inline=False)
        if inviter:
            e.add_field(name="Invited By", value=f"{inviter.mention} `{inviter.id}`", inline=False)
            e.description = f"**{member}** was invited by **{inviter}**"
        else:
            e.description = f"**{member}** joined (Invite source unknown - Vanity / OAuth)"
        await ch.send(embed=e)
    except Exception as e:
        print(f"invite tracker error: {e}")

@bot.event
async def on_message_delete(message):
    if not log_id or message.author.bot:
        return
    try:
        ch = bot.get_channel(log_id)
        if not ch:
            return
        e = discord.Embed(color=0xED4245, timestamp=discord.utils.utcnow())
        e.set_author(name=f"{message.author} - Message Deleted",
                     icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
        e.add_field(
            name=f"From: {message.author.mention} In: {message.channel.mention}",
            value=f"{message.content[:1000] if message.content else '*Image / File / Embed*'}",
            inline=False,
        )
        e.set_footer(text=f"Author ID: {message.author.id} | Message ID: {message.id}")
        await ch.send(embed=e)
    except Exception:
        pass

@bot.event
async def on_voice_state_update(member, before, after):
    if not log_id or member.bot:
        return
    try:
        ch = bot.get_channel(log_id)
        if not ch:
            return
        e = discord.Embed(timestamp=discord.utils.utcnow())
        e.set_author(name=str(member),
                     icon_url=member.display_avatar.url if member.display_avatar else None)
        if not before.channel and after.channel:
            e.color = 0x57F287
            e.description = f"{member.mention} joined voice channel {after.channel.mention}"
            e.add_field(name="", value=f"ID: {member.id}")
        elif before.channel and not after.channel:
            e.color = 0xED4245
            e.description = f"{member.mention} left voice channel {before.channel.mention}"
        elif before.channel != after.channel:
            e.color = 0xFEE75C
            e.description = f"{member.mention} moved {before.channel.mention} → {after.channel.mention}"
        else:
            return
        await ch.send(embed=e)
    except Exception:
        pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not source_id or not target_id or not mirror_active:
        return
    dest = None
    if message.channel.id == source_id:
        dest = bot.get_channel(target_id)
    elif message.channel.id == target_id:
        dest = bot.get_channel(source_id)
    else:
        return
    if not dest:
        return
    try:
        files = [await a.to_file() for a in message.attachments] if message.attachments else []
        ref = None
        if message.reference and message.reference.message_id in message_map:
            try:
                mid = message_map[message.reference.message_id]
                mt = await dest.fetch_message(mid)
                ref = mt.to_reference()
            except Exception:
                pass
        if message.content or files:
            k = await dest.send(content=message.content or None, files=files or None, reference=ref)
            message_map[message.id] = k.id
            message_map[k.id] = message.id
    except Exception as e:
        print(f"Mirror failed: {e}")

# ============ RUN ============
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
