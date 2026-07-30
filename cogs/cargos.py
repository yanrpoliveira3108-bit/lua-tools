import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

class CargosLoja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="loja-cargos", description="Loja de cargos VIP com dinheiro do bot")
    async def loja_cargos(self, interaction: discord.Interaction):
        embed = discord.Embed(title="👑 Loja de Cargos - Compre com Lolicoins!", description="Cargos temporários comprados com dinheiro do bot\nUse `/comprar-cargo cargo:<nome>`", color=config["cores"]["loja"])
        for cargo_id, info in config["economia"]["cargos_loja"].items():
            embed.add_field(name=f"{info['emoji']} {info['nome']} - {info['preco']} {config['economia']['moeda_emoji']}", value=f"Duração: {info['duracao_dias']} dias\nID: `{cargo_id}`", inline=False)
        
        # Mostra cargos do servidor que estão à venda (ADMs configuram)
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT cargo_id, preco, duracao_dias FROM cargos_loja WHERE guild_id=?", (interaction.guild.id,)) as cur:
                rows = await cur.fetchall()
                if rows:
                    txt = ""
                    for cargo_id, preco, duracao in rows:
                        cargo = interaction.guild.get_role(cargo_id)
                        nome = cargo.name if cargo else f"Cargo {cargo_id}"
                        txt += f"**{nome}** - {preco} {config['economia']['moeda_emoji']} - {duracao} dias\n"
                    embed.add_field(name="🏷️ Cargos do Servidor à venda", value=txt, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="comprar-cargo", description="Compre um cargo VIP")
    @app_commands.describe(cargo="ID do cargo da loja (vip, premium, etc) ou mencione um cargo configurado")
    async def comprar_cargo(self, interaction: discord.Interaction, cargo: str):
        cargo = cargo.lower()
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        
        # Verifica se é cargo da config padrão
        preco = None
        duracao = None
        cargo_nome = None
        cargo_id_real = None
        
        if cargo in config["economia"]["cargos_loja"]:
            info = config["economia"]["cargos_loja"][cargo]
            preco = info["preco"]
            duracao = info["duracao_dias"]
            cargo_nome = info["nome"]
            # Tenta achar cargo com mesmo nome no servidor
            for r in interaction.guild.roles:
                if r.name.lower() == cargo_nome.lower() or r.name.lower() == cargo.lower():
                    cargo_id_real = r.id
                    break
            # Se não achar, cria? Não, avisa ADM precisa configurar
            if not cargo_id_real:
                # Procura cargo VIP existente ou tenta usar primeiro cargo vendável
                async with aiosqlite.connect(database.DB_PATH) as db:
                    async with db.execute("SELECT cargo_id FROM cargos_loja WHERE guild_id=? LIMIT 1", (guild_id,)) as cur:
                        row = await cur.fetchone()
                        if row:
                            cargo_id_real = row[0]
                        else:
                            await interaction.response.send_message(f"❌ Servidor não tem cargo `{cargo_nome}` criado! Peça ADM usar `/config-cargo` para configurar cargos do servidor à venda.", ephemeral=True)
                            return
        else:
            # Tenta achar por ID ou nome nos cargos_loja custom
            try:
                # Se mencionou cargo <@&id> extrai id
                if cargo.startswith("<@&"):
                    cargo_id_real = int(cargo[3:-1])
                else:
                    cargo_id_real = int(cargo)
                cargo_obj = interaction.guild.get_role(cargo_id_real)
                if not cargo_obj:
                    await interaction.response.send_message("Cargo não encontrado!", ephemeral=True)
                    return
                cargo_nome = cargo_obj.name
            except:
                # Procura por nome
                encontrado = None
                for r in interaction.guild.roles:
                    if cargo in r.name.lower():
                        encontrado = r
                        break
                if not encontrado:
                    await interaction.response.send_message(f"Cargo `{cargo}` não encontrado! Use `/loja-cargos`", ephemeral=True)
                    return
                cargo_id_real = encontrado.id
                cargo_nome = encontrado.name
            
            # Busca preço custom
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT preco, duracao_dias FROM cargos_loja WHERE guild_id=? AND cargo_id=?", (guild_id, cargo_id_real)) as cur:
                    row = await cur.fetchone()
                    if not row:
                        await interaction.response.send_message(f"Cargo {cargo_nome} não está à venda! ADM use `/config-cargo`", ephemeral=True)
                        return
                    preco, duracao = row
        
        # Verifica dinheiro
        dados = await database.get_economia(user_id, guild_id)
        if dados["carteira"] < preco:
            await interaction.response.send_message(f"Precisa {preco} {config['economia']['moeda_emoji']}, você tem {dados['carteira']}", ephemeral=True)
            return
        
        # Compra
        role = interaction.guild.get_role(cargo_id_real)
        if not role:
            await interaction.response.send_message("Cargo não existe mais!", ephemeral=True)
            return
        
        # Verifica hierarquia bot
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message("❌ Meu cargo é menor que o cargo que você quer comprar! Peça ADM subir meu cargo.", ephemeral=True)
            return
        
        agora = datetime.datetime.now()
        expira = agora + datetime.timedelta(days=duracao)
        
        try:
            await interaction.user.add_roles(role, reason=f"Compra na loja por {preco} coins")
        except Exception as e:
            await interaction.response.send_message(f"Erro ao dar cargo: {e}", ephemeral=True)
            return
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (preco, user_id, guild_id))
            await db.execute("INSERT OR REPLACE INTO cargos_users (guild_id, user_id, cargo_id, expira) VALUES (?, ?, ?, ?)", (guild_id, user_id, cargo_id_real, expira.isoformat()))
            await db.commit()
        
        embed = discord.Embed(title="✅ Cargo comprado!", description=f"Você comprou **{cargo_nome}** por {config['economia']['moeda_emoji']} {preco}\nDuração: {duracao} dias (expira <t:{int(expira.timestamp())}:D>)", color=config["cores"]["sucesso"])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="config-cargo", description="[ADM] Configure um cargo para vender na loja")
    @app_commands.default_permissions(manage_roles=True)
    async def config_cargo(self, interaction: discord.Interaction, cargo: discord.Role, preco: int, duracao_dias: int = 7):
        if preco <=0:
            await interaction.response.send_message("Preço inválido!", ephemeral=True)
            return
        if cargo.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message("Esse cargo é maior que o meu! Não posso vender.", ephemeral=True)
            return
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO cargos_loja (guild_id, cargo_id, preco, duracao_dias, tipo) VALUES (?, ?, ?, ?, ?)", (interaction.guild.id, cargo.id, preco, duracao_dias, "custom"))
            await db.commit()
        
        await interaction.response.send_message(f"✅ Cargo {cargo.mention} agora à venda por {preco} {config['economia']['moeda_emoji']} - {duracao_dias} dias")

    @app_commands.command(name="meus-cargos", description="Veja seus cargos comprados")
    async def meus_cargos(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT cargo_id, expira FROM cargos_users WHERE guild_id=? AND user_id=?", (interaction.guild.id, interaction.user.id)) as cur:
                rows = await cur.fetchall()
                if not rows:
                    await interaction.response.send_message("Você não comprou nenhum cargo! `/loja-cargos`", ephemeral=True)
                    return
                embed = discord.Embed(title=f"👑 Cargos de {interaction.user.display_name}", color=config["cores"]["loja"])
                desc = ""
                for cargo_id, expira in rows:
                    role = interaction.guild.get_role(cargo_id)
                    nome = role.name if role else f"Cargo {cargo_id}"
                    exp_ts = int(datetime.datetime.fromisoformat(expira).timestamp()) if expira else 0
                    desc += f"{nome} - Expira <t:{exp_ts}:R>\n"
                embed.description = desc
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        # Task para remover cargos expirados a cada hora
        self.bot.loop.create_task(self.check_expirados())

    async def check_expirados(self):
        await self.bot.wait_until_ready()
        import asyncio
        while not self.bot.is_closed():
            try:
                async with aiosqlite.connect(database.DB_PATH) as db:
                    async with db.execute("SELECT guild_id, user_id, cargo_id, expira FROM cargos_users") as cur:
                        rows = await cur.fetchall()
                        for guild_id, user_id, cargo_id, expira in rows:
                            if not expira:
                                continue
                            try:
                                exp_dt = datetime.datetime.fromisoformat(expira)
                                if datetime.datetime.now() >= exp_dt:
                                    guild = self.bot.get_guild(guild_id)
                                    if guild:
                                        member = guild.get_member(user_id)
                                        role = guild.get_role(cargo_id)
                                        if member and role and role in member.roles:
                                            try:
                                                await member.remove_roles(role, reason="Cargo VIP expirado")
                                            except:
                                                pass
                                    await db.execute("DELETE FROM cargos_users WHERE guild_id=? AND user_id=? AND cargo_id=?", (guild_id, user_id, cargo_id))
                                    await db.commit()
                            except:
                                continue
            except Exception as e:
                print(f"[CARGOS] Erro check expirados: {e}")
            await asyncio.sleep(3600)

async def setup(bot):
    await bot.add_cog(CargosLoja(bot))
