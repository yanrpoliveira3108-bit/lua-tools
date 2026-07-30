import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import datetime
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

RECURSOS = config["farm"]["recursos"]
FERRAMENTAS = config["farm"]["ferramentas"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "farm", interaction.channel.id):
            await interaction.response.send_message("❌ Módulo farm desativado", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    farm_group = app_commands.Group(name="farm", description="Mineração e coleta")

    @farm_group.command(name="minerar", description="Minere recursos")
    @check_modulo()
    async def minerar(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT ferramenta, nivel, xp, recursos, last_farm FROM farm_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    # Cria conta farm
                    await db.execute("INSERT INTO farm_users (user_id, guild_id, ferramenta, nivel, recursos, last_farm) VALUES (?, ?, ?, 1, ?, ?)", 
                                     (interaction.user.id, interaction.guild.id, "picareta_madeira", "{}"))
                    await db.commit()
                    ferramenta = "picareta_madeira"
                    nivel = 1
                    xp = 0
                    recursos = {}
                    last_farm = None
                else:
                    ferramenta, nivel, xp, recursos_json, last_farm = row
                    recursos = json.loads(recursos_json) if recursos_json else {}

        # Cooldown
        if last_farm:
            last = datetime.datetime.fromisoformat(last_farm)
            diff = (datetime.datetime.now() - last).total_seconds()
            if diff < config["farm"]["cooldown_segundos"]:
                await interaction.response.send_message(f"⛏️ Picareta cansada! Espere {int(config['farm']['cooldown_segundos']-diff)}s", ephemeral=True)
                return

        # Mineracao
        tool_info = FERRAMENTAS.get(ferramenta, {"multiplicador":1, "chance_raro":0.05})
        multiplicador = tool_info["multiplicador"]
        chance_raro = tool_info["chance_raro"] + (nivel * 0.01)

        # Sorteia recurso
        roll = random.random()
        if roll < chance_raro * 0.1:
            recurso_id = "netherita"
        elif roll < chance_raro * 0.3:
            recurso_id = "diamante"
        elif roll < chance_raro * 0.6:
            recurso_id = random.choice(["ouro", "ferro"])
        elif roll < 0.5:
            recurso_id = random.choice(["pedra", "madeira"])
        else:
            recurso_id = random.choice(list(RECURSOS.keys()))

        qtd = random.randint(1, 3) * multiplicador
        if recurso_id in ["madeira","pedra"]:
            qtd = random.randint(2,5) * multiplicador

        # Aplica evento farm se ativo
        bonus_evento = 1
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT multiplicador FROM eventos_ativos WHERE guild_id=? AND evento_id='hora_feliz'", (interaction.guild.id,)) as cur:
                r = await cur.fetchone()
                if r:
                    bonus_evento = r[0]
                    qtd = int(qtd * bonus_evento)

        # Salva
        recursos[recurso_id] = recursos.get(recurso_id, 0) + qtd
        xp_gain = random.randint(5,15)
        novo_xp = xp + xp_gain
        novo_nivel = nivel
        if novo_xp >= nivel * 100:
            novo_nivel +=1
            novo_xp = 0

        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE farm_users SET recursos=?, xp=?, nivel=?, last_farm=?, total_minerado=total_minerado+? WHERE user_id=? AND guild_id=?", 
                             (json.dumps(recursos), novo_xp, novo_nivel, datetime.datetime.now().isoformat(), qtd, interaction.user.id, interaction.guild.id))
            await db.commit()

        info = RECURSOS[recurso_id]
        embed = discord.Embed(title="⛏️ Mineração!", description=f"Você minerou **{qtd}x {info['emoji']} {info['nome']}** usando {ferramenta}\n+{xp_gain} XP Farm", color=config["cores"]["farm"])
        if bonus_evento>1:
            embed.add_field(name="🎉 Evento", value=f"{bonus_evento}x bônus ativo!")
        if novo_nivel>nivel:
            embed.add_field(name="🎉 Level Up!", value=f"Farm nível {novo_nivel}!", inline=False)
        embed.add_field(name="Ferramenta", value=f"{ferramenta} - {multiplicador}x", inline=True)
        embed.add_field(name="Nível", value=f"{novo_nivel} ({novo_xp}/{novo_nivel*100} XP)", inline=True)
        await interaction.response.send_message(embed=embed)

    @farm_group.command(name="inventario", description="Seus recursos minerados")
    @check_modulo()
    async def inventario(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT recursos, ferramenta, nivel, xp FROM farm_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Nenhum recurso! Use `/farm minerar`", ephemeral=True)
                    return
                recursos_json, ferramenta, nivel, xp = row
                recursos = json.loads(recursos_json) if recursos_json else {}
        
        if not recursos:
            await interaction.response.send_message("Inventário vazio!", ephemeral=True)
            return
        
        embed = discord.Embed(title=f"🎒 Mochila Farm - Nv {nivel}", color=config["cores"]["farm"])
        total_valor = 0
        txt = ""
        for res_id, qtd in recursos.items():
            info = RECURSOS.get(res_id, {"nome": res_id, "emoji":"❓", "valor":10})
            valor = info["valor"] * qtd
            total_valor += valor
            txt += f"{info['emoji']} **{info['nome']}** x{qtd} = {valor} {config['economia']['moeda_emoji']}\n"
        embed.description = txt
        embed.add_field(name="💰 Valor total se vender tudo", value=f"{total_valor} {config['economia']['moeda_emoji']}", inline=False)
        embed.add_field(name="⛏️ Ferramenta", value=ferramenta, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @farm_group.command(name="vender", description="Venda recursos")
    @app_commands.describe(recurso="Qual recurso (ou 'tudo')", quantidade="Quantidade (0 = tudo)")
    @check_modulo()
    async def vender(self, interaction: discord.Interaction, recurso: str, quantidade: int = 0):
        recurso = recurso.lower()
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT recursos FROM farm_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Sem recursos!", ephemeral=True)
                    return
                recursos = json.loads(row[0]) if row[0] else {}
        
        total_ganho = 0
        if recurso == "tudo":
            for res_id, qtd in list(recursos.items()):
                info = RECURSOS.get(res_id)
                if not info: continue
                ganho = info["valor"] * qtd
                total_ganho += ganho
            recursos = {}
        else:
            if recurso not in recursos:
                await interaction.response.send_message(f"Você não tem {recurso}!", ephemeral=True)
                return
            qtd_disponivel = recursos[recurso]
            qtd_vender = quantidade if quantidade>0 else qtd_disponivel
            if qtd_vender > qtd_disponivel:
                await interaction.response.send_message(f"Só tem {qtd_disponivel}x {recurso}", ephemeral=True)
                return
            info = RECURSOS.get(recurso, {"valor":10})
            total_ganho = info["valor"] * qtd_vender
            recursos[recurso] -= qtd_vender
            if recursos[recurso] <=0:
                del recursos[recurso]
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE farm_users SET recursos=? WHERE user_id=? AND guild_id=?", (json.dumps(recursos), interaction.user.id, interaction.guild.id))
            await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (interaction.user.id, interaction.guild.id))
            await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (total_ganho, interaction.user.id, interaction.guild.id))
            await db.commit()
        
        await interaction.response.send_message(f"✅ Vendeu por {config['economia']['moeda_emoji']} {total_ganho}!")

    @farm_group.command(name="loja", description="Loja de ferramentas farm")
    @check_modulo()
    async def loja(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⛏️ Loja Farm - Ferramentas", color=config["cores"]["farm"])
        for tool_id, info in config["economia"]["loja"].items():
            if info["tipo"]!="farm":
                continue
            f_info = FERRAMENTAS.get(tool_id, {})
            embed.add_field(name=f"{info['emoji']} {tool_id} - {info['preco']} {config['economia']['moeda_emoji']}", value=f"{info['desc']}\nMulti {f_info.get('multiplicador',1)}x | Raro {int(f_info.get('chance_raro',0)*100)}%", inline=False)
        embed.set_footer(text="Use /comprar item:<tool>")
        await interaction.response.send_message(embed=embed)

    @farm_group.command(name="equipar", description="Equipe ferramenta farm")
    @check_modulo()
    async def equipar(self, interaction: discord.Interaction, ferramenta: str):
        ferramenta = ferramenta.lower()
        if ferramenta not in FERRAMENTAS:
            await interaction.response.send_message("Ferramenta inválida! `/farm loja`", ephemeral=True)
            return
        if not await database.has_item(interaction.user.id, interaction.guild.id, ferramenta, 1):
            # Também aceita se já comprou antes? Verifica se tem no inventario farm?
            # Vamos permitir equipar se tem no inventario geral
            # Se não tem, avisa
            await interaction.response.send_message(f"Você não tem {ferramenta}! Compre com `/comprar item:{ferramenta}`", ephemeral=True)
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE farm_users SET ferramenta=? WHERE user_id=? AND guild_id=?", (ferramenta, interaction.user.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"✅ Equipado {ferramenta} - {FERRAMENTAS[ferramenta]['multiplicador']}x recursos!")

    @farm_group.command(name="rank", description="Top mineradores")
    @check_modulo()
    async def rank(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT user_id, total_minerado, nivel FROM farm_users WHERE guild_id=? ORDER BY total_minerado DESC LIMIT 10", (interaction.guild.id,)) as cur:
                rows = await cur.fetchall()
        embed = discord.Embed(title="🏆 Top Mineradores", color=config["cores"]["farm"])
        desc=""
        for i,(uid,total,nivel) in enumerate(rows,1):
            m = interaction.guild.get_member(uid)
            nome = m.display_name if m else f"User {uid}"
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            desc+=f"{medal} {nome} - Nv {nivel} - {total} minerados\n"
        embed.description=desc or "Ninguém minerou"
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Farm(bot))
