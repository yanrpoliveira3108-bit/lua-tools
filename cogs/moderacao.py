import discord
from discord.ext import commands
from discord import app_commands
import json

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]

class Moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="limpar", description="[MOD] Limpe mensagens do chat")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(quantidade="Qtd de mensagens (1-100)")
    async def limpar(self, interaction: discord.Interaction, quantidade: int):
        if quantidade<1 or quantidade>100:
            await interaction.response.send_message("1-100 apenas!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=quantidade)
            await interaction.followup.send(f"✅ {len(deleted)} mensagens apagadas! | {MARCA}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="[MOD] Banir usuário")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
        if membro.top_role >= interaction.user.top_role:
            await interaction.response.send_message("Não pode banir alguém com cargo igual/maior!", ephemeral=True)
            return
        try:
            await interaction.guild.ban(membro, reason=motivo)
            embed=discord.Embed(title="🔨 Ban", description=f"{membro.mention} banido por {interaction.user.mention}\nMotivo: {motivo}\n{MARCA}", color=config["cores"]["erro"])
            embed.set_footer(text=MARCA)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @app_commands.command(name="kick", description="[MOD] Expulsar usuário")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
        try:
            await interaction.guild.kick(membro, reason=motivo)
            await interaction.response.send_message(f"👢 {membro.mention} kickado! Motivo: {motivo} | {MARCA}")
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @app_commands.command(name="lock", description="[MOD] Trancar canal")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
            await interaction.response.send_message(f"🔒 Canal trancado por {interaction.user.mention} | {MARCA}")
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @app_commands.command(name="unlock", description="[MOD] Destrancar canal")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
            await interaction.response.send_message(f"🔓 Canal destrancado! | {MARCA}")
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @app_commands.command(name="anunciar", description="[MOD] Anúncio bonito no canal")
    @app_commands.default_permissions(manage_messages=True)
    async def anunciar(self, interaction: discord.Interaction, titulo: str, mensagem: str):
        embed=discord.Embed(title=f"📢 {titulo}", description=mensagem, color=config["cores"]["principal"])
        embed.set_footer(text=f"Anunciado por {interaction.user.display_name} | {MARCA}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderacao(bot))
