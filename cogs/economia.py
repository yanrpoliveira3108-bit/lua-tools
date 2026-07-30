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

MOEDA = config["economia"]["moeda_nome"]
EMOJI = config["economia"]["moeda_emoji"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "economia", interaction.channel.id):
            embed = discord.Embed(title="❌ Módulo desativado", description=f"**Economia** desativada aqui. Use `/modulos`", color=config["cores"]["erro"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="carteira", description=f"Sua carteira de {MOEDA}")
    @check_modulo()
    async def carteira(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        dados = await database.get_economia(alvo.id, interaction.guild.id)
        inv = await database.get_inventario(alvo.id, interaction.guild.id)
        total = dados["carteira"] + dados["banco"]
        
        embed = discord.Embed(title=f"{EMOJI} {alvo.display_name}", color=config["cores"]["economia"])
        embed.add_field(name="💵 Carteira", value=f"{EMOJI} {dados['carteira']:,}", inline=True)
        embed.add_field(name="🏦 Banco", value=f"{EMOJI} {dados['banco']:,}", inline=True)
        embed.add_field(name="💰 Total", value=f"{EMOJI} {total:,}", inline=True)
        if inv:
            itens_txt = "\n".join([f"{qtd}x {item}" for item,qtd,tipo in inv[:5]])
            embed.add_field(name="🎒 Itens (top 5)", value=itens_txt or "Vazio", inline=False)
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Resgate diário")
    @check_modulo()
    async def daily(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT last_daily FROM economia WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                agora = datetime.datetime.now()
                if row and row[0]:
                    last = datetime.datetime.fromisoformat(row[0])
                    if (agora - last).total_seconds() < 86400:
                        h = int((86400 - (agora-last).total_seconds())//3600)
                        await interaction.response.send_message(f"⏰ Já pegou hoje! Volte em {h}h", ephemeral=True)
                        return
                premio = random.randint(config["economia"]["daily_min"], config["economia"]["daily_max"])
                bonus_casa = 0
                bonus_casado = 0
                desc_bonus = ""
                # Bonus casa
                try:
                    async with db.execute("SELECT conforto FROM casas WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur_casa:
                        row_casa = await cur_casa.fetchone()
                        if row_casa:
                            bonus_casa = row_casa[0] * 2
                            if bonus_casa>0:
                                desc_bonus += f"\n🏠 Casa conforto +{bonus_casa}"
                except: pass
                # Bonus casado
                try:
                    async with db.execute("SELECT * FROM casamentos WHERE guild_id=? AND (user1_id=? OR user2_id=?)", (interaction.guild.id, interaction.user.id, interaction.user.id)) as cur_cas:
                        if await cur_cas.fetchone():
                            bonus_casado = config["casamento"]["bonus_diario_casado"]
                            desc_bonus += f"\n💍 Casado +{bonus_casado}"
                except: pass
                
                premio_total = premio + bonus_casa + bonus_casado

                # Multiplicador evento hora_feliz
                try:
                    async with db.execute("SELECT multiplicador FROM eventos_ativos WHERE guild_id=? AND evento_id='hora_feliz'", (interaction.guild.id,)) as cur_ev:
                        row_ev = await cur_ev.fetchone()
                        if row_ev:
                            premio_total = int(premio_total * row_ev[0])
                            desc_bonus += f"\n🎉 Evento {row_ev[0]}x!"
                except: pass

                await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 1000)", (interaction.user.id, interaction.guild.id))
                await db.execute("UPDATE economia SET carteira=carteira+?, last_daily=? WHERE user_id=? AND guild_id=?", (premio_total, agora.isoformat(), interaction.user.id, interaction.guild.id))
                await db.commit()
            await database.add_item(interaction.user.id, interaction.guild.id, "pokebola", 2, "pokemon")
        embed = discord.Embed(title="💰 Daily!", description=f"+{EMOJI} {premio_total:,} (base {premio} + bônus)\n+ 2x Pokébolas 🔴{desc_bonus}", color=config["cores"]["sucesso"])
        await interaction.response.send_message(embed=embed)

    # GRUPO BANCO
    banco_group = app_commands.Group(name="banco", description="Banco - guarde seu dinheiro")

    @banco_group.command(name="depositar", description="Deposite no banco")
    @check_modulo()
    async def banco_depositar(self, interaction: discord.Interaction, quantia: int):
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if quantia <=0 or dados["carteira"] < quantia:
            await interaction.response.send_message(f"Você só tem {EMOJI} {dados['carteira']}", ephemeral=True)
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-?, banco=banco+? WHERE user_id=? AND guild_id=?", (quantia, quantia, interaction.user.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"🏦 Depositado {EMOJI} {quantia}")

    @banco_group.command(name="sacar", description="Saque do banco")
    @check_modulo()
    async def banco_sacar(self, interaction: discord.Interaction, quantia: int):
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if quantia <=0 or dados["banco"] < quantia:
            await interaction.response.send_message(f"Banco tem só {EMOJI} {dados['banco']}", ephemeral=True)
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira+?, banco=banco-? WHERE user_id=? AND guild_id=?", (quantia, quantia, interaction.user.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"💵 Sacado {EMOJI} {quantia}")

    # GRUPO TRABALHO - NOVO!
    trabalho_group = app_commands.Group(name="trabalho", description="Sistema de empregos")

    @trabalho_group.command(name="lista", description="Veja os trabalhos disponíveis")
    @check_modulo()
    async def trabalho_lista(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💼 Central de Empregos", color=config["cores"]["economia"])
        for job_id, info in config["economia"]["trabalhos"].items():
            embed.add_field(name=f"{info['emoji']} {job_id.capitalize()} - {info['salario_min']}-{info['salario_max']} {EMOJI}", value=f"{info['desc']}\nXP: {info['xp']}/trabalho", inline=False)
        embed.set_footer(text="Use /trabalho escolher e depois /trabalho trabalhar")
        await interaction.response.send_message(embed=embed)

    @trabalho_group.command(name="escolher", description="Escolha seu emprego")
    @app_commands.describe(emprego="Qual emprego")
    @app_commands.choices(emprego=[
        app_commands.Choice(name="💻 Programador", value="programador"),
        app_commands.Choice(name="🎮 Streamer", value="streamer"),
        app_commands.Choice(name="🍞 Padeiro", value="padeiro"),
        app_commands.Choice(name="⛏️ Minerador", value="minerador"),
        app_commands.Choice(name="👮 Policial", value="policial"),
        app_commands.Choice(name="👨‍⚕️ Médico", value="medico"),
    ])
    @check_modulo()
    async def trabalho_escolher(self, interaction: discord.Interaction, emprego: str):
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO trabalhos_users (user_id, guild_id, job_id, nivel, xp) VALUES (?, ?, ?, 1, 0)", (interaction.user.id, interaction.guild.id, emprego))
            await db.commit()
        await interaction.response.send_message(f"✅ Agora você é **{emprego.capitalize()}**! Use `/trabalho trabalhar`")

    @trabalho_group.command(name="trabalhar", description="Trabalhe no seu emprego")
    @check_modulo()
    async def trabalho_trabalhar(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT job_id, nivel, xp FROM trabalhos_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Escolha um emprego primeiro: `/trabalho lista`", ephemeral=True)
                    return
                job_id, nivel, xp = row
            
            async with db.execute("SELECT last_work FROM economia WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                r = await cur.fetchone()
                agora = datetime.datetime.now()
                if r and r[0]:
                    last = datetime.datetime.fromisoformat(r[0])
                    if (agora-last).total_seconds() < 1800: # 30 min cooldown agora
                        mins = int((1800 - (agora-last).total_seconds())/60)
                        await interaction.response.send_message(f"⏰ Cansado! Descanse {mins} min", ephemeral=True)
                        return

            info = config["economia"]["trabalhos"][job_id]
            salario = random.randint(info["salario_min"], info["salario_max"]) + (nivel * 20)
            bonus = random.choice([0,0,0,50,100]) if job_id=="streamer" else 0
            total = salario+bonus

            await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 1000)", (interaction.user.id, interaction.guild.id))
            await db.execute("UPDATE economia SET carteira=carteira+?, last_work=?, total_trabalhos=total_trabalhos+1 WHERE user_id=? AND guild_id=?", (total, agora.isoformat(), interaction.user.id, interaction.guild.id))
            
            # XP
            novo_xp = xp + info["xp"]
            novo_nivel = nivel
            if novo_xp >= nivel*100:
                novo_nivel += 1
                novo_xp = 0
            
            await db.execute("UPDATE trabalhos_users SET nivel=?, xp=? WHERE user_id=? AND guild_id=?", (novo_nivel, novo_xp, interaction.user.id, interaction.guild.id))
            await db.commit()

        msg = f"{info['emoji']} Você trabalhou como **{job_id.capitalize()}** e ganhou {EMOJI} {salario}"
        if bonus:
            msg += f" + bônus {EMOJI} {bonus}!"
        if novo_nivel > nivel:
            msg += f"\n🎉 **PROMOVIDO para nível {novo_nivel}!** Salário aumentado!"
        embed = discord.Embed(title="💼 Trabalho", description=msg, color=config["cores"]["sucesso"])
        embed.add_field(name="Progresso", value=f"Nível {novo_nivel} - XP {novo_xp}/{novo_nivel*100}")
        await interaction.response.send_message(embed=embed)

    @trabalho_group.command(name="perfil", description="Seu perfil de trabalho")
    @check_modulo()
    async def trabalho_perfil(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT job_id, nivel, xp FROM trabalhos_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Nenhum emprego! `/trabalho lista`", ephemeral=True)
                    return
                job_id, nivel, xp = row
            async with db.execute("SELECT total_trabalhos FROM economia WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                total = (await cur.fetchone())[0] or 0
        info = config["economia"]["trabalhos"][job_id]
        embed = discord.Embed(title=f"{info['emoji']} Perfil - {job_id.capitalize()}", color=config["cores"]["economia"])
        embed.add_field(name="Nível", value=nivel, inline=True)
        embed.add_field(name="XP", value=f"{xp}/{nivel*100}", inline=True)
        embed.add_field(name="Total trabalhos", value=total, inline=True)
        embed.add_field(name="Salário", value=f"{info['salario_min']+nivel*20} - {info['salario_max']+nivel*20}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loja", description="Lojinha global")
    @check_modulo()
    async def loja(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛒 Loja - Economia", color=config["cores"]["loja"])
        for item_id, info in config["economia"]["loja"].items():
            embed.add_field(name=f"{info['emoji']} {item_id} - {info['preco']} {EMOJI}", value=info["desc"], inline=False)
        embed.add_field(name="💡 Pokebolas?", value="Use `/pokeloja`", inline=False)
        embed.add_field(name="⚔️ Equipamentos?", value="Use `/rpg loja`", inline=False)
        embed.set_footer(text="Use /comprar item:<nome>")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="comprar", description="Compre um item")
    @check_modulo()
    async def comprar(self, interaction: discord.Interaction, item: str, quantidade: int = 1):
        item = item.lower()
        # Verifica se é item da loja economica
        loja = config["economia"]["loja"]
        # Pokebolas
        pokebolas = config["pokemon"]["pokebolas"]
        # Equipamentos
        equip = config["rpg"]["equipamentos"]

        preco = None
        tipo = None
        if item in loja:
            preco = loja[item]["preco"]
            tipo = "geral"
        elif item in pokebolas:
            preco = pokebolas[item]["preco"]
            tipo = "pokemon"
        elif item in equip:
            preco = equip[item]["preco"]
            tipo = "rpg"
            # verifica nivel
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT nivel FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                    row = await cur.fetchone()
                    if not row:
                        await interaction.response.send_message("Crie personagem RPG primeiro! `/rpg criar`", ephemeral=True)
                        return
                    if row[0] < equip[item]["nivel_min"]:
                        await interaction.response.send_message(f"Precisa nível {equip[item]['nivel_min']} para comprar isso!", ephemeral=True)
                        return
        else:
            await interaction.response.send_message(f"Item `{item}` não existe. Use `/loja`, `/pokeloja`, `/rpg loja`", ephemeral=True)
            return

        total_preco = preco * quantidade
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"] < total_preco:
            await interaction.response.send_message(f"Precisa {EMOJI} {total_preco}, só tem {dados['carteira']}", ephemeral=True)
            return
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (total_preco, interaction.user.id, interaction.guild.id))
            await db.commit()
        await database.add_item(interaction.user.id, interaction.guild.id, item, quantidade, tipo)
        
        embed = discord.Embed(title="✅ Compra!", description=f"Comprou {quantidade}x **{item}** por {EMOJI} {total_preco}", color=config["cores"]["sucesso"])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mochila", description="Veja sua mochila/inventário")
    @check_modulo()
    async def mochila(self, interaction: discord.Interaction):
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id)
        if not inv:
            await interaction.response.send_message("Mochila vazia!", ephemeral=True)
            return
        embed = discord.Embed(title=f"🎒 Mochila de {interaction.user.display_name}", color=config["cores"]["principal"])
        for tipo in ["geral","pokemon","rpg"]:
            itens = [f"{qtd}x {item_id}" for item_id,qtd,t in inv if t==tipo]
            if itens:
                embed.add_field(name=tipo.capitalize(), value="\n".join(itens), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rank", description="Ranking dos ricos")
    @check_modulo()
    async def rank(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT user_id, carteira+banco as total FROM economia WHERE guild_id=? ORDER BY total DESC LIMIT 10", (interaction.guild.id,)) as cur:
                rows = await cur.fetchall()
        embed = discord.Embed(title=f"🏆 Top Ricos - {MOEDA}", color=config["cores"]["economia"])
        desc = ""
        for i, (uid, total) in enumerate(rows, 1):
            m = interaction.guild.get_member(uid)
            nome = m.display_name if m else f"User {uid}"
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            desc += f"{medal} {nome} - {EMOJI} {total:,}\n"
        embed.description = desc or "Vazio"
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economia(bot))
