import os
import discord
from discord.ext import commands
from discord import app_commands, Embed, ButtonStyle, TextStyle
from discord.ui import View, Button, Select, Modal, TextInput

# ================= Configuration =================
TOKEN = os.getenv("DISCORD_TOKEN")

# Badel hna b Category IDs dialek f Discord
BOOST_CATEGORY_ID = 123456789012345678  # Category ID for Boost Orders
CARRY_CATEGORY_ID = 987654321098765432  # Category ID for Carry Orders (2x)

# Prices Matrix for Ranks
RANK_PRICES = {
    "Bronze I": 0, "Bronze II": 1, "Bronze III": 1,
    "Silver I": 1, "Silver II": 1.5, "Silver III": 1.5,
    "Gold I": 2, "Gold II": 2, "Gold III": 2,
    "Diamond I": 2, "Diamond II": 2, "Diamond III": 3,
    "Mythic I": 4, "Mythic II": 5, "Mythic III": 6,
    "Legendary I": 9, "Legendary II": 12, "Legendary III": 15,
    "Masters I": 30, "Masters II": 60, "Pro": 105
}

RANKS_ORDER = list(RANK_PRICES.keys())

def calculate_price(current_rank: str, desired_rank: str, order_type: str) -> float:
    try:
        start_idx = RANKS_ORDER.index(current_rank)
        end_idx = RANKS_ORDER.index(desired_rank)
    except ValueError:
        return 0.0

    if start_idx >= end_idx:
        return 0.0

    base_total = 0.0
    for i in range(start_idx + 1, end_idx + 1):
        base_total += RANK_PRICES[RANKS_ORDER[i]]

    # Carry service is 2x price
    multiplier = 2.0 if order_type == "Carry" else 1.0
    return round(base_total * multiplier, 2)

# ================= Discord Bot Setup =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Modal Form
class OrderModal(Modal):
    def __init__(self, order_type: str):
        super().__init__(title=f"Ranked {order_type} Order")
        self.order_type = order_type

        # Select Current Rank
        self.current_rank = TextInput(
            label="Current Rank",
            placeholder="e.g. Bronze I, Diamond III, Mythic I...",
            required=True,
            style=TextStyle.short
        )
        # Select Desired Rank
        self.desired_rank = TextInput(
            label="Desired Rank",
            placeholder="e.g. Diamond I, Legendary III, Masters I...",
            required=True,
            style=TextStyle.short
        )
        # Power 11 Brawlers
        self.p11_brawlers = TextInput(
            label="How many Power 11 brawlers do you have?",
            placeholder="e.g. 0-10, 11-20, 21-30...",
            required=True,
            style=TextStyle.short
        )
        # Payment Method
        self.payment_method = TextInput(
            label="Payment Method",
            placeholder="PayPal, Venmo, Cash App, Wise, Apple Pay...",
            required=True,
            style=TextStyle.short
        )
        # Additional Notes
        self.notes = TextInput(
            label="Additional Notes (Optional)",
            style=TextStyle.paragraph,
            required=False,
            placeholder="Any special requests or information..."
        )

        self.add_item(self.current_rank)
        self.add_item(self.desired_rank)
        self.add_item(self.p11_brawlers)
        self.add_item(self.payment_method)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        c_rank = self.current_rank.value.strip()
        d_rank = self.desired_rank.value.strip()
        total_price = calculate_price(c_rank, d_rank, self.order_type)

        # Category Routing
        category_id = CARRY_CATEGORY_ID if self.order_type == "Carry" else BOOST_CATEGORY_ID
        category = interaction.guild.get_channel(category_id)

        # Ticket Channel Name Creation
        ticket_name = f"order-{interaction.user.name}".lower()

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        if category and isinstance(category, discord.CategoryChannel):
            ticket_channel = await interaction.guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites
            )
        else:
            ticket_channel = await interaction.guild.create_text_channel(
                name=ticket_name,
                overwrites=overwrites
            )

        # Embed inside Ticket Channel
        header_embed = Embed(
            title="Ranked Boost Order Ticket",
            description=f"Your Ranked {self.order_type} order ticket is now open 👊\n\nClick the button below to close this ticket when you're done.",
            color=0x8A2BE2
        )
        header_embed.set_footer(text="Powered by Iceyz BrawlMart™")

        details_embed = Embed(
            title="Your Ranked Boost Order",
            description="**Step 2/5**\nℹ️ **Order Details**",
            color=0x8A2BE2
        )
        details_embed.add_field(name="Current Rank 🛡️", value=f"└ `{c_rank}`", inline=False)
        details_embed.add_field(name="Desired Rank 🏆", value=f"└ `{d_rank}`", inline=False)
        details_embed.add_field(name="Order Type 🚀", value=f"└ `{self.order_type}`", inline=False)
        details_embed.add_field(name="Total Price 💰", value=f"└ `${total_price} USD`", inline=False)
        details_embed.add_field(name="Power 11 Count ⚡", value=f"└ `{self.p11_brawlers.value}`", inline=False)
        details_embed.add_field(name="Payment Method 💳", value=f"└ `{self.payment_method.value}`", inline=False)
        
        if self.notes.value:
            details_embed.add_field(name="Notes 📝", value=f"└ `{self.notes.value}`", inline=False)

        details_embed.set_footer(text=f"Powered by Iceyz BrawlMart™ • {interaction.user.id}")

        # Controls Buttons inside Ticket
        view = View()
        view.add_item(Button(label="Close", style=ButtonStyle.danger, custom_id="close_ticket"))
        view.add_item(Button(label="Close With Reason", style=ButtonStyle.secondary, custom_id="close_reason_ticket"))
        view.add_item(Button(label="I Sent Payment", style=ButtonStyle.success, custom_id="sent_payment"))

        await ticket_channel.send(content=f"{interaction.user.mention}", embeds=[header_embed, details_embed], view=view)
        await interaction.followup.send(f"Ticket created successfully! {ticket_channel.mention}", ephemeral=True)

# Select Service Type View
class ServiceTypeView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get B00sted", style=ButtonStyle.success, emoji="🚀")
    async def boosted_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(OrderModal(order_type="Boost"))

    @discord.ui.button(label="Get Carried (2x Price)", style=ButtonStyle.blurple, emoji="🤝")
    async def carried_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(OrderModal(order_type="Carry"))

# Main Ticket Panel View
class MainTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Your Rank Upgraded", style=ButtonStyle.primary, emoji="👊", custom_id="get_rank_upgraded")
    async def upgrade_button(self, interaction: discord.Interaction, button: Button):
        embed = Embed(
            title="Choose your service type:",
            description="🚀 **B00st** - Standard service\n🤝 **Carry** - Play together (2x price)",
            color=0x8A2BE2
        )
        await interaction.response.send_message(embed=embed, view=ServiceTypeView(), ephemeral=True)

# Command to Setup Main Message
@bot.tree.command(name="setup_panel", description="Setup Ranked Boost Panel")
@app_commands.default_permissions(administrator=True)
async def setup_panel(interaction: discord.Interaction):
    embed = Embed(
        title="Ranked B00st Service",
        description="**What We Offer**\n• Climb the ranks with professional boosting service\n• Fast, secure, and reliable rank progression\n• Experienced boosters with proven track records",
        color=0x8A2BE2
    )
    # Hna t9dr tzid image URL dyalek f Discord
    # embed.set_image(url="YOUR_IMAGE_URL")

    await interaction.channel.send(embed=embed, view=MainTicketView())
    await interaction.response.send_message("Panel created!", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot logged in as {bot.user}")

# Handle Ticket Close Buttons
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        cid = interaction.data.get("custom_id")
        if cid == "close_ticket":
            await interaction.response.send_message("Closing channel in 5 seconds...")
            await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.datetime.timedelta(seconds=5))
            await interaction.channel.delete()
        elif cid == "sent_payment":
            await interaction.response.send_message("Payment confirmation received! Staff will verify shortly.", ephemeral=False)

if __name__ == "__main__":
    bot.run(TOKEN)
