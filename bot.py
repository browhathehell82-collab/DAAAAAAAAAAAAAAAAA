# ══════════════════════════════════════════════════════════
#
#   🌸 Welcome & Goodbye Bot
#   Created by Maruan / Teally Willy
#   Beautiful welcome/goodbye cards with images
#
# ══════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import aiohttp
import os

# ══════════════════════════════════════════════════════════
#                    CONFIGURATION
# ══════════════════════════════════════════════════════════

TOKEN = "MTQ4ODUzMjAyMDM1NDM1NTI3MA.GJGu5j.I8n6EE13DBQkaq60kz3TZftMBITKGWXtUO3xVo"
PREFIX = "!"

# Channel IDs (set with !setwelcome and !setgoodbye)
guild_config = {}

# ══════════════════════════════════════════════════════════
#                    BOT SETUP
# ══════════════════════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ══════════════════════════════════════════════════════════
#               IMAGE GENERATOR CLASS
# ══════════════════════════════════════════════════════════

class CardGenerator:
    def __init__(self):
        self.width = 934
        self.height = 500
        self.avatar_size = 180

        # Try to load custom font, fallback to default
        self.font_path = "assets/font.ttf"
        if not os.path.exists(self.font_path):
            self.font_path = None

    def get_font(self, size):
        """Get font with fallback"""
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, size)
            else:
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            return ImageFont.load_default()

    def make_circle_avatar(self, avatar_image):
        """Make avatar circular with border"""
        avatar = avatar_image.resize((self.avatar_size, self.avatar_size))

        # Create circular mask
        mask = Image.new("L", (self.avatar_size, self.avatar_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, self.avatar_size, self.avatar_size), fill=255)

        # Apply mask
        circular = Image.new("RGBA", (self.avatar_size, self.avatar_size), (0, 0, 0, 0))
        circular.paste(avatar, (0, 0), mask)

        return circular

    def make_border_circle(self, color=(255, 255, 255)):
        """Create a circular border for the avatar"""
        border_size = self.avatar_size + 16
        border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(border)

        # Outer circle (border)
        draw.ellipse(
            (0, 0, border_size - 1, border_size - 1),
            fill=None,
            outline=color,
            width=4
        )

        # Inner glow
        draw.ellipse(
            (2, 2, border_size - 3, border_size - 3),
            fill=None,
            outline=(*color, 150),
            width=2
        )

        return border

    def add_text_with_shadow(self, draw, position, text, font, fill=(255, 255, 255), shadow_color=(0, 0, 0)):
        """Add text with shadow effect"""
        x, y = position

        # Shadow
        for offset in [(2, 2), (1, 1), (2, 1), (1, 2)]:
            draw.text(
                (x + offset[0], y + offset[1]),
                text, font=font,
                fill=(*shadow_color, 150),
                anchor="mm"
            )

        # Main text
        draw.text(position, text, font=font, fill=fill, anchor="mm")

    def create_overlay(self, base_image):
        """Create a dark gradient overlay"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Dark gradient from bottom
        for y in range(self.height):
            alpha = int(180 * (y / self.height))
            draw.line([(0, y), (self.width, y)], fill=(0, 0, 0, alpha))

        # Combine
        result = base_image.copy().convert("RGBA")
        result = Image.alpha_composite(result, overlay)

        return result

    async def generate_card(self, member, card_type="welcome", custom_bg=None):
        """Generate a welcome or goodbye card"""

        # ---- BACKGROUND ----
        bg_path = f"assets/{'welcome_bg' if card_type == 'welcome' else 'goodbye_bg'}.png"

        if custom_bg:
            background = custom_bg.copy()
        elif os.path.exists(bg_path):
            background = Image.open(bg_path)
        else:
            # Generate a beautiful gradient background if no image exists
            background = self.generate_gradient_bg(card_type)

        # Resize and crop background
        background = background.resize((self.width, self.height))
        background = background.convert("RGBA")

        # Apply blur for aesthetic effect
        bg_blurred = background.filter(ImageFilter.GaussianBlur(radius=2))

        # Add dark overlay
        card = self.create_overlay(bg_blurred)
        draw = ImageDraw.Draw(card)

        # ---- DECORATIVE ELEMENTS ----
        # Top bar
        bar_color = (255, 182, 193) if card_type == "welcome" else (169, 169, 200)
        draw.rectangle([(0, 0), (self.width, 5)], fill=bar_color)
        draw.rectangle([(0, self.height - 5), (self.width, self.height)], fill=bar_color)

        # Side accents
        draw.rectangle([(0, 0), (5, self.height)], fill=(*bar_color, 100))
        draw.rectangle([(self.width - 5, 0), (self.width, self.height)], fill=(*bar_color, 100))

        # ---- DECORATIVE BORDER ----
        # Rounded rectangle border
        border_color = (*bar_color, 150)
        margin = 20
        draw.rounded_rectangle(
            [(margin, margin), (self.width - margin, self.height - margin)],
            radius=25,
            outline=border_color,
            width=2
        )

        # ---- AVATAR ----
        # Download avatar
        avatar_image = await self.download_avatar(member)
        circular_avatar = self.make_circle_avatar(avatar_image)

        # Create border
        border = self.make_border_circle(bar_color)

        # Position avatar in center-top
        avatar_x = (self.width - self.avatar_size) // 2
        avatar_y = 60

        border_x = avatar_x - 8
        border_y = avatar_y - 8

        # Paste border and avatar
        card.paste(border, (border_x, border_y), border)
        card.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)

        # ---- ONLINE STATUS DOT ----
        status_colors = {
            discord.Status.online: (67, 181, 129),
            discord.Status.idle: (250, 166, 26),
            discord.Status.dnd: (240, 71, 71),
            discord.Status.offline: (116, 127, 141)
        }
        status_color = status_colors.get(member.status, (116, 127, 141))
        status_x = avatar_x + self.avatar_size - 25
        status_y = avatar_y + self.avatar_size - 25
        draw.ellipse(
            [(status_x, status_y), (status_x + 30, status_y + 30)],
            fill=status_color,
            outline=(255, 255, 255),
            width=3
        )

        # ---- TEXT ----
        center_x = self.width // 2

        # Welcome / Goodbye title
        if card_type == "welcome":
            title = "WELCOME"
            subtitle_color = (255, 182, 193)
        else:
            title = "GOODBYE"
            subtitle_color = (169, 169, 200)

        title_font = self.get_font(48)
        name_font = self.get_font(36)
        info_font = self.get_font(22)
        small_font = self.get_font(18)

        # Title
        self.add_text_with_shadow(
            draw,
            (center_x, avatar_y + self.avatar_size + 40),
            title,
            title_font,
            fill=subtitle_color
        )

        # Username
        username = member.display_name
        if len(username) > 20:
            username = username[:17] + "..."

        self.add_text_with_shadow(
            draw,
            (center_x, avatar_y + self.avatar_size + 90),
            username,
            name_font,
            fill=(255, 255, 255)
        )

        # Handle (@username)
        handle = f"@{member.name}"
        self.add_text_with_shadow(
            draw,
            (center_x, avatar_y + self.avatar_size + 125),
            handle,
            info_font,
            fill=(200, 200, 200)
        )

        # ---- DECORATIVE LINE ----
        line_y = avatar_y + self.avatar_size + 150
        line_width = 300
        line_start = center_x - line_width // 2
        line_end = center_x + line_width // 2

        # Gradient line
        for i in range(line_width):
            alpha = int(255 * (1 - abs(i - line_width // 2) / (line_width // 2)))
            x = line_start + i
            draw.line([(x, line_y), (x, line_y + 2)], fill=(*subtitle_color, alpha))

        # ---- MEMBER COUNT / SERVER INFO ----
        if card_type == "welcome":
            member_count = member.guild.member_count
            info_text = f"You are member #{member_count}"
        else:
            member_count = member.guild.member_count
            info_text = f"We now have {member_count} members"

        self.add_text_with_shadow(
            draw,
            (center_x, line_y + 30),
            info_text,
            info_font,
            fill=(220, 220, 220)
        )

        # Server name
        server_name = member.guild.name
        self.add_text_with_shadow(
            draw,
            (center_x, line_y + 60),
            server_name,
            small_font,
            fill=(*subtitle_color, 200)
        )

        # ---- DECORATIVE DOTS ----
        dot_y = self.height - 35
        total_dots = 5
        dot_spacing = 20
        start_x = center_x - (total_dots * dot_spacing) // 2

        for i in range(total_dots):
            dot_x = start_x + (i * dot_spacing)
            size = 6 if i == total_dots // 2 else 4
            alpha = 255 if i == total_dots // 2 else 150
            draw.ellipse(
                [(dot_x, dot_y), (dot_x + size, dot_y + size)],
                fill=(*subtitle_color, alpha)
            )

        # ---- CONVERT TO BYTES ----
        buffer = BytesIO()
        card.save(buffer, "PNG", quality=95)
        buffer.seek(0)

        return buffer

    def generate_gradient_bg(self, card_type):
        """Generate a gradient background if no image file exists"""
        bg = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(bg)

        if card_type == "welcome":
            # Pink/purple gradient
            for y in range(self.height):
                r = int(255 - (y / self.height) * 100)
                g = int(150 - (y / self.height) * 80)
                b = int(200 + (y / self.height) * 55)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        else:
            # Dark blue/gray gradient
            for y in range(self.height):
                r = int(40 + (y / self.height) * 30)
                g = int(40 + (y / self.height) * 30)
                b = int(60 + (y / self.height) * 50)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return bg

    async def download_avatar(self, member):
        """Download member avatar"""
        try:
            avatar_url = member.display_avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(str(avatar_url)) as response:
                    if response.status == 200:
                        data = await response.read()
                        return Image.open(BytesIO(data)).convert("RGBA")
        except Exception:
            pass

        # Fallback: create default avatar
        default = Image.new("RGBA", (256, 256), (114, 137, 218))
        draw = ImageDraw.Draw(default)
        draw.ellipse([(0, 0), (255, 255)], fill=(114, 137, 218))
        return default

# Initialize generator
card_gen = CardGenerator()

# ══════════════════════════════════════════════════════════
#                    BOT EVENTS
# ══════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print("")
    print("╔══════════════════════════════════════════╗")
    print("║   🌸 Welcome & Goodbye Bot              ║")
    print("║   Created by Maruan / Teally Willy       ║")
    print(f"║   Bot: {bot.user.name:<33}║")
    print(f"║   Servers: {str(len(bot.guilds)):<29}║")
    print("╠══════════════════════════════════════════╣")
    print("║   ✅ Welcome cards                       ║")
    print("║   ✅ Goodbye cards                       ║")
    print("║   ✅ Custom backgrounds                  ║")
    print("║   ✅ Auto-generated gradients             ║")
    print("╚══════════════════════════════════════════╝")
    print("")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="new members | !help"
        )
    )

# ══════════════════════════════════════════════════════════
#               WELCOME EVENT
# ══════════════════════════════════════════════════════════

@bot.event
async def on_member_join(member):
    config = guild_config.get(member.guild.id, {})
    welcome_channel_id = config.get("welcome_channel")

    if not welcome_channel_id:
        return

    channel = member.guild.get_channel(welcome_channel_id)
    if not channel:
        return

    try:
        # Generate welcome card
        card_buffer = await card_gen.generate_card(member, "welcome")

        # Create embed
        embed = discord.Embed(
            description=(
                f"### 🌸 Welcome to **{member.guild.name}**!\n\n"
                f"> Hey {member.mention}! We're glad to have you here.\n"
                f"> Make sure to read the rules and have fun!\n\n"
                f"📊 You are our **{member.guild.member_count}th** member!"
            ),
            color=discord.Color.from_rgb(255, 182, 193),
            timestamp=member.joined_at or discord.utils.utcnow()
        )
        embed.set_footer(
            text=f"ID: {member.id}",
            icon_url=member.display_avatar.url
        )

        # Send card + embed
        file = discord.File(card_buffer, filename="welcome.png")
        embed.set_image(url="attachment://welcome.png")

        await channel.send(
            content=f"||{member.mention}||",
            embed=embed,
            file=file
        )

    except Exception as e:
        print(f"Welcome error: {e}")

# ══════════════════════════════════════════════════════════
#               GOODBYE EVENT
# ══════════════════════════════════════════════════════════

@bot.event
async def on_member_remove(member):
    config = guild_config.get(member.guild.id, {})
    goodbye_channel_id = config.get("goodbye_channel")

    if not goodbye_channel_id:
        return

    channel = member.guild.get_channel(goodbye_channel_id)
    if not channel:
        return

    try:
        # Generate goodbye card
        card_buffer = await card_gen.generate_card(member, "goodbye")

        # Calculate time in server
        if member.joined_at:
            time_in_server = discord.utils.utcnow() - member.joined_at
            days = time_in_server.days
            if days > 365:
                time_text = f"{days // 365} years, {(days % 365) // 30} months"
            elif days > 30:
                time_text = f"{days // 30} months, {days % 30} days"
            else:
                time_text = f"{days} days"
        else:
            time_text = "Unknown"

        # Create embed
        embed = discord.Embed(
            description=(
                f"### 👋 Goodbye, **{member.display_name}**\n\n"
                f"> **{member.name}** has left **{member.guild.name}**.\n"
                f"> They were with us for **{time_text}**.\n\n"
                f"📊 We now have **{member.guild.member_count}** members."
            ),
            color=discord.Color.from_rgb(169, 169, 200),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(
            text=f"ID: {member.id}",
            icon_url=member.display_avatar.url
        )

        # Send card + embed
        file = discord.File(card_buffer, filename="goodbye.png")
        embed.set_image(url="attachment://goodbye.png")

        await channel.send(embed=embed, file=file)

    except Exception as e:
        print(f"Goodbye error: {e}")

# ══════════════════════════════════════════════════════════
#                    COMMANDS
# ══════════════════════════════════════════════════════════

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="🌸 Welcome & Goodbye Bot",
        description="Beautiful welcome and goodbye cards for your server!",
        color=discord.Color.from_rgb(255, 182, 193)
    )
    embed.add_field(
        name="⚙️ Setup",
        value=(
            "`!setwelcome #channel` - Set welcome channel\n"
            "`!setgoodbye #channel` - Set goodbye channel\n"
            "`!removewelcome` - Disable welcome\n"
            "`!removegoodbye` - Disable goodbye"
        ),
        inline=False
    )
    embed.add_field(
        name="🧪 Testing",
        value=(
            "`!testwelcome` - Test welcome card\n"
            "`!testgoodbye` - Test goodbye card"
        ),
        inline=False
    )
    embed.add_field(
        name="📊 Info",
        value=(
            "`!settings` - View current settings\n"
            "`!help` - Show this menu"
        ),
        inline=False
    )
    embed.set_footer(text="Created by Maruan / Teally Willy 🌸")
    await ctx.send(embed=embed)

# --- SET WELCOME ---
@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    if ctx.guild.id not in guild_config:
        guild_config[ctx.guild.id] = {}
    guild_config[ctx.guild.id]["welcome_channel"] = channel.id

    embed = discord.Embed(
        title="✅ Welcome Channel Set",
        description=f"Welcome messages will be sent to {channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# --- SET GOODBYE ---
@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, channel: discord.TextChannel):
    if ctx.guild.id not in guild_config:
        guild_config[ctx.guild.id] = {}
    guild_config[ctx.guild.id]["goodbye_channel"] = channel.id

    embed = discord.Embed(
        title="✅ Goodbye Channel Set",
        description=f"Goodbye messages will be sent to {channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# --- REMOVE WELCOME ---
@bot.command(name="removewelcome")
@commands.has_permissions(administrator=True)
async def removewelcome(ctx):
    if ctx.guild.id in guild_config:
        guild_config[ctx.guild.id].pop("welcome_channel", None)

    embed = discord.Embed(
        title="❌ Welcome Disabled",
        description="Welcome messages have been disabled.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

# --- REMOVE GOODBYE ---
@bot.command(name="removegoodbye")
@commands.has_permissions(administrator=True)
async def removegoodbye(ctx):
    if ctx.guild.id in guild_config:
        guild_config[ctx.guild.id].pop("goodbye_channel", None)

    embed = discord.Embed(
        title="❌ Goodbye Disabled",
        description="Goodbye messages have been disabled.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

# --- TEST WELCOME ---
@bot.command(name="testwelcome")
@commands.has_permissions(administrator=True)
async def testwelcome(ctx):
    try:
        card_buffer = await card_gen.generate_card(ctx.author, "welcome")

        embed = discord.Embed(
            description=(
                f"### 🌸 Welcome to **{ctx.guild.name}**!\n\n"
                f"> Hey {ctx.author.mention}! We're glad to have you here.\n"
                f"> Make sure to read the rules and have fun!\n\n"
                f"📊 You are our **{ctx.guild.member_count}th** member!"
            ),
            color=discord.Color.from_rgb(255, 182, 193),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="🧪 This is a test", icon_url=ctx.author.display_avatar.url)

        file = discord.File(card_buffer, filename="welcome.png")
        embed.set_image(url="attachment://welcome.png")
        await ctx.send(embed=embed, file=file)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# --- TEST GOODBYE ---
@bot.command(name="testgoodbye")
@commands.has_permissions(administrator=True)
async def testgoodbye(ctx):
    try:
        card_buffer = await card_gen.generate_card(ctx.author, "goodbye")

        embed = discord.Embed(
            description=(
                f"### 👋 Goodbye, **{ctx.author.display_name}**\n\n"
                f"> **{ctx.author.name}** has left **{ctx.guild.name}**.\n"
                f"> They were with us for a long time.\n\n"
                f"📊 We now have **{ctx.guild.member_count}** members."
            ),
            color=discord.Color.from_rgb(169, 169, 200),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="🧪 This is a test", icon_url=ctx.author.display_avatar.url)

        file = discord.File(card_buffer, filename="goodbye.png")
        embed.set_image(url="attachment://goodbye.png")
        await ctx.send(embed=embed, file=file)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# --- SETTINGS ---
@bot.command(name="settings")
@commands.has_permissions(administrator=True)
async def settings(ctx):
    config = guild_config.get(ctx.guild.id, {})

    welcome_id = config.get("welcome_channel")
    goodbye_id = config.get("goodbye_channel")

    welcome_ch = ctx.guild.get_channel(welcome_id) if welcome_id else None
    goodbye_ch = ctx.guild.get_channel(goodbye_id) if goodbye_id else None

    embed = discord.Embed(
        title="⚙️ Current Settings",
        color=discord.Color.from_rgb(255, 182, 193),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="🌸 Welcome Channel",
        value=welcome_ch.mention if welcome_ch else "❌ Not set",
        inline=True
    )
    embed.add_field(
        name="👋 Goodbye Channel",
        value=goodbye_ch.mention if goodbye_ch else "❌ Not set",
        inline=True
    )
    embed.set_footer(text="Use !setwelcome and !setgoodbye to configure")
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════════════════
#                ERROR HANDLER
# ══════════════════════════════════════════════════════════

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permissions.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Error: {error}")

# ══════════════════════════════════════════════════════════
#                    START BOT
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🌸 Starting Welcome & Goodbye Bot...")
    bot.run(TOKEN)