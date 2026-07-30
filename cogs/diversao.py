import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "diversao", interaction.channel.id):
            embed = discord.Embed(title="❌ Módulo desativado", description="Módulo diversão desativado aqui - use /modulos pra ver onde é ativo", color=config["cores"]["erro"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="Pergunte ao 8ball mágico")
    @check_modulo()
    async def eight_ball(self, interaction: discord.Interaction, pergunta: str):
        respostas = ["Sim!", "Não!", "Talvez...", "Com certeza!", "Jamais!", "Provavelmente sim", "Pergunte de novo", "Claro que não", "O destino diz não", "Sinais apontam que sim"]
        embed = discord.Embed(title="🎱 8Ball", color=config["cores"]["principal"])
        embed.add_field(name="Pergunta", value=pergunta, inline=False)
        embed.add_field(name="Resposta", value=random.choice(respostas), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="abraçar", description="Abrace alguém")
    @check_modulo()
    async def abracar(self, interaction: discord.Interaction, membro: discord.Member):
        gifs = ["https://i.pinimg.com/originals/79/e0/19/79e019551f169284bc6a63cea9c664e8.gif"]
        embed = discord.Embed(description=f"{interaction.user.mention} abraçou {membro.mention} 🤗", color=config["cores"]["principal"])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="beijar", description="Beije alguém 😘")
    @check_modulo()
    async def beijar(self, interaction: discord.Interaction, membro: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} beijou {membro.mention} 😘💋")

    @app_commands.command(name="tapa", description="Dê um tapa de brincadeira")
    @check_modulo()
    async def tapa(self, interaction: discord.Interaction, membro: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} deu um tapa em {membro.mention} 👋 com carinho")

    @app_commands.command(name="ship", description="Veja o quanto combina com alguém")
    @check_modulo()
    async def ship(self, interaction: discord.Interaction, pessoa1: discord.Member, pessoa2: discord.Member = None):
        p2 = pessoa2 or interaction.user
        porcent = random.randint(0, 100)
        barra = "█" * (porcent // 10) + "░" * (10 - porcent // 10)
        embed = discord.Embed(title="💘 Ship", description=f"{pessoa1.mention} + {p2.mention} = **{porcent}%**\n`{barra}`", color=0xFF69B4)
        if porcent > 80:
            embed.set_footer(text="💍 Casal perfeito! Casem com /casar")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ppt", description="Pedra, papel, tesoura vs bot")
    @app_commands.choices(escolha=[app_commands.Choice(name="🪨 Pedra", value="pedra"), app_commands.Choice(name="📄 Papel", value="papel"), app_commands.Choice(name="✂️ Tesoura", value="tesoura")])
    @check_modulo()
    async def ppt(self, interaction: discord.Interaction, escolha: str):
        bot = random.choice(["pedra","papel","tesoura"])
        regras = {("pedra","tesoura"): True, ("tesoura","papel"): True, ("papel","pedra"): True}
        if escolha==bot:
            res="Empate! 🤝"
        elif regras.get((escolha,bot)):
            res=f"Você venceu! 🎉 Eu escolhi {bot}"
        else:
            res=f"Você perdeu! 😢 Eu escolhi {bot}"
        await interaction.response.send_message(res)

    @app_commands.command(name="dado", description="Rola um dado")
    @app_commands.describe(lados="Lados do dado (padrão 6)")
    @check_modulo()
    async def dado(self, interaction: discord.Interaction, lados: int = 6):
        await interaction.response.send_message(f"🎲 Rolou: **{random.randint(1, lados)}** (1-{lados})")

    @app_commands.command(name="piada", description="Conta uma piada")
    @check_modulo()
    async def piada(self, interaction: discord.Interaction):
        piadas = [
            "Por que o livro de matemática ficou triste? Porque tinha muitos problemas!",
            "O que o pato disse pra pata? Vem Quá!",
            "Por que o tomate não dorme? Porque ele é semi-acordado (semi-verde)!",
            "Qual é o cúmulo da mentira? Contar que está lendo isso de verdade... ops",
            "Lua Tools é tão completo que até o bot riu da minha piada!"
        ]
        await interaction.response.send_message(f"😂 {random.choice(piadas)}")

    @app_commands.command(name="fato", description="Fato aleatório")
    @check_modulo()
    async def fato(self, interaction: discord.Interaction):
        fatos = ["Polvos têm 3 corações!", "Lua Tools tem 12 cogs!", "O mel nunca estraga!", "Pokémons raros têm 3% de spawn no Lua Tools!"]
        await interaction.response.send_message(f"🧠 Fato: {random.choice(fatos)}")

    @app_commands.command(name="carinho", description="Faça carinho")
    @check_modulo()
    async def carinho(self, interaction: discord.Interaction, membro: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} fez carinho em {membro.mention} 🥰")

    @app_commands.command(name="meme", description="Meme aleatório (texto)")
    @check_modulo()
    async def meme(self, interaction: discord.Interaction):
        memes = ["Quando você pede /daily e vem 1500 🌙", "Eu tentando capturar Mewtwo com pokebola 60%...", "Quando sua casa tem 60 de conforto e você ainda mora no barraco IRL"]
        await interaction.response.send_message(f"🤣 {random.choice(memes)}")

async def setup(bot):
    await bot.add_cog(Diversao(bot))
