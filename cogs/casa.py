import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

CASAS = config["casa"]["niveis"]
MOVEIS = config["casa"]["moveis"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "casa", interaction.channel.id):
            await interaction.response.send_message("❌ Módulo casa desativado", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class Casa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.casa_group = app_commands.Group(name="casa", description="Sistema de casas")

    @app_commands.command(name="casa", description="Veja sua casa")
    @check_modulo()
    async def ver_casa(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT nivel, conforto, moveis FROM casas WHERE user_id=? AND guild_id=?", (alvo.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    if alvo.id == interaction.user.id:
                        await interaction.response.send_message("Você não tem casa! Use `/casa-loja` para comprar", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"{alvo.display_name} não tem casa (mora de aluguel 😢)", ephemeral=True)
                    return
                nivel, conforto, moveis_json = row
                moveis = json.loads(moveis_json) if moveis_json else {}
        
        casa_info = CASAS.get(str(nivel), {"nome":"Sem casa","emoji":"🏚️","slots_moveis":0})
        embed = discord.Embed(title=f"{casa_info['emoji']} Casa de {alvo.display_name} - {casa_info['nome']} Nv {nivel}", color=config["cores"]["casa"])
        embed.add_field(name="Conforto", value=f"{conforto} ✨", inline=True)
        embed.add_field(name="Slots", value=f"{len(moveis)}/{casa_info['slots_moveis']}", inline=True)
        
        if moveis:
            txt = ""
            for mov_id, qtd in moveis.items():
                info = MOVEIS.get(mov_id, {"nome":mov_id,"emoji":"❓"})
                txt += f"{info['emoji']} {info['nome']} x{qtd}\n"
            embed.add_field(name="🪑 Móveis", value=txt, inline=False)
            
            # Bonus diário baseado em conforto
            bonus = conforto * 2
            embed.add_field(name="💰 Renda passiva", value=f"Sua casa gera {bonus} {config['economia']['moeda_emoji']}/dia no /daily", inline=False)
        else:
            embed.add_field(name="Móveis", value="Nenhum! `/moveis-loja`", inline=False)
        
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="casa-loja", description="Loja de casas")
    @check_modulo()
    async def casa_loja(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🏠 Loja de Casas", description="Use `/comprar-casa nivel:<nivel>`", color=config["cores"]["casa"])
        for nivel, info in CASAS.items():
            embed.add_field(name=f"{info['emoji']} Nível {nivel} - {info['nome']} - {info['preco']} {config['economia']['moeda_emoji']}", value=f"Slots: {info['slots_moveis']} móveis\nID: `{nivel}`", inline=False)
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT nivel FROM casas WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if row:
                    embed.add_field(name="🏠 Sua casa atual", value=f"Nível {row[0]} - {CASAS.get(str(row[0]),{}).get('nome','')}", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="comprar-casa", description="Compre uma casa")
    @app_commands.describe(nivel="Nível da casa 1-4")
    @check_modulo()
    async def comprar_casa(self, interaction: discord.Interaction, nivel: int):
        if str(nivel) not in CASAS:
            await interaction.response.send_message("Nível inválido! 1-4", ephemeral=True)
            return
        info = CASAS[str(nivel)]
        preco = info["preco"]
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT nivel FROM casas WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                nivel_atual = row[0] if row else 0
                if nivel_atual >= nivel:
                    await interaction.response.send_message(f"Você já tem casa nível {nivel_atual} ou superior!", ephemeral=True)
                    return
                # Custo upgrade = diferença
                if nivel_atual>0:
                    preco_atual = CASAS.get(str(nivel_atual),{"preco":0})["preco"]
                    preco = preco - preco_atual
        
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"] < preco:
            await interaction.response.send_message(f"Precisa {preco} {config['economia']['moeda_emoji']}, tem {dados['carteira']}", ephemeral=True)
            return
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (preco, interaction.user.id, interaction.guild.id))
            await db.execute("INSERT OR REPLACE INTO casas (user_id, guild_id, nivel, conforto, moveis) VALUES (?, ?, ?, COALESCE((SELECT conforto FROM casas WHERE user_id=? AND guild_id=?),0), COALESCE((SELECT moveis FROM casas WHERE user_id=? AND guild_id=?), '{}'))", 
                             (interaction.user.id, interaction.guild.id, nivel, interaction.user.id, interaction.guild.id, interaction.user.id, interaction.guild.id))
            await db.commit()
        
        await interaction.response.send_message(f"🏠 Comprou {info['emoji']} **{info['nome']}** nível {nivel} por {preco} {config['economia']['moeda_emoji']}!")

    @app_commands.command(name="moveis-loja", description="Loja de móveis")
    @check_modulo()
    async def moveis_loja(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🪑 Loja de Móveis", description="Use `/comprar-movel movel:<id>`\nMóveis aumentam conforto e dão bônus no daily!", color=config["cores"]["casa"])
        for mov_id, info in MOVEIS.items():
            embed.add_field(name=f"{info['emoji']} {info['nome']} - {info['preco']} {config['economia']['moeda_emoji']} | +{info['conforto']} conforto", value=f"ID: `{mov_id}`", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="comprar-movel", description="Compre um móvel pra sua casa")
    @check_modulo()
    async def comprar_movel(self, interaction: discord.Interaction, movel: str):
        movel = movel.lower()
        if movel not in MOVEIS:
            await interaction.response.send_message(f"Móvel `{movel}` não existe! `/moveis-loja`", ephemeral=True)
            return
        info = MOVEIS[movel]
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT nivel, conforto, moveis FROM casas WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Precisa ter casa primeiro! `/casa-loja`", ephemeral=True)
                    return
                nivel, conforto, moveis_json = row
                moveis = json.loads(moveis_json) if moveis_json else {}
                casa_info = CASAS.get(str(nivel))
                if len(moveis) >= casa_info["slots_moveis"] and movel not in moveis:
                    await interaction.response.send_message(f"Casa lotada! {len(moveis)}/{casa_info['slots_moveis']} slots. Upgrade com `/comprar-casa nivel:{nivel+1}`", ephemeral=True)
                    return
        
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"] < info["preco"]:
            await interaction.response.send_message(f"Precisa {info['preco']}", ephemeral=True)
            return
        
        # Compra
        moveis[movel] = moveis.get(movel, 0) + 1
        novo_conforto = conforto + info["conforto"]
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (info["preco"], interaction.user.id, interaction.guild.id))
            await db.execute("UPDATE casas SET moveis=?, conforto=? WHERE user_id=? AND guild_id=?", (json.dumps(moveis), novo_conforto, interaction.user.id, interaction.guild.id))
            await db.commit()
        
        await interaction.response.send_message(f"✅ Comprou {info['emoji']} **{info['nome']}**! Conforto +{info['conforto']} (total {novo_conforto})")

    @app_commands.command(name="vender-movel", description="Venda um móvel")
    @check_modulo()
    async def vender_movel(self, interaction: discord.Interaction, movel: str):
        movel = movel.lower()
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT conforto, moveis FROM casas WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Sem casa!", ephemeral=True)
                    return
                conforto, moveis_json = row
                moveis = json.loads(moveis_json) if moveis_json else {}
                if movel not in moveis or moveis[movel]<=0:
                    await interaction.response.send_message("Não tem esse móvel!", ephemeral=True)
                    return
                info = MOVEIS.get(movel, {"preco":100,"conforto":5})
                # Vende por 50%
                preco_venda = int(info["preco"]*0.5)
                moveis[movel]-=1
                if moveis[movel]<=0:
                    del moveis[movel]
                novo_conforto = max(0, conforto - info["conforto"])
                await db.execute("UPDATE casas SET moveis=?, conforto=? WHERE user_id=? AND guild_id=?", (json.dumps(moveis), novo_conforto, interaction.user.id, interaction.guild.id))
                await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (preco_venda, interaction.user.id, interaction.guild.id))
                await db.commit()
        await interaction.response.send_message(f"💰 Vendeu {movel} por {preco_venda} {config['economia']['moeda_emoji']} (50% valor)")

async def setup(bot):
    await bot.add_cog(Casa(bot))
