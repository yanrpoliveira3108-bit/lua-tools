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

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "familia", interaction.channel.id):
            await interaction.response.send_message("❌ Módulo família desativado aqui", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class Familia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.casamento_group = app_commands.Group(name="casar", description="Sistema de casamento")
        self.familia_group = app_commands.Group(name="familia", description="Família")
        # Registrar groups no setup

    async def get_casamento(self, guild_id, user_id):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT user2_id, data FROM casamentos WHERE guild_id=? AND (user1_id=? OR user2_id=?)", (guild_id, user_id, user_id)) as cur:
                row = await cur.fetchone()
                if row:
                    parceiro = row[0] if row[0]!=user_id else None
                    # Se user1 é o pesquisado, user2 é parceiro, mas se user2 é pesquisado, precisa pegar user1
                    if parceiro is None:
                        async with db.execute("SELECT user1_id FROM casamentos WHERE guild_id=? AND user2_id=?", (guild_id, user_id)) as cur2:
                            r2 = await cur2.fetchone()
                            if r2:
                                parceiro = r2[0]
                    return {"parceiro_id": parceiro if parceiro!=user_id else row[0], "data": row[1]}
                # Tenta outro lado
                async with db.execute("SELECT user1_id, data FROM casamentos WHERE guild_id=? AND user2_id=?", (guild_id, user_id)) as cur:
                    row = await cur.fetchone()
                    if row:
                        return {"parceiro_id": row[0], "data": row[1]}
            return None

    @app_commands.command(name="casar", description="Peça alguém em casamento 💍")
    @check_modulo()
    async def casar(self, interaction: discord.Interaction, pessoa: discord.Member, anel: str = "anel_casamento"):
        if pessoa.id == interaction.user.id:
            await interaction.response.send_message("Não pode casar consigo mesmo!", ephemeral=True)
            return
        if pessoa.bot:
            await interaction.response.send_message("Não pode casar com bot!", ephemeral=True)
            return
        
        # Verifica se já casado
        casamento1 = await self.get_casamento(interaction.guild.id, interaction.user.id)
        casamento2 = await self.get_casamento(interaction.guild.id, pessoa.id)
        if casamento1:
            await interaction.response.send_message("Você já é casado!", ephemeral=True)
            return
        if casamento2:
            await interaction.response.send_message(f"{pessoa.display_name} já é casado!", ephemeral=True)
            return
        
        # Verifica anel
        custo = config["casamento"]["custo_anel"]
        if anel == "anel_casamento":
            if not await database.has_item(interaction.user.id, interaction.guild.id, "anel_casamento", 1):
                dados = await database.get_economia(interaction.user.id, interaction.guild.id)
                if dados["carteira"] < custo:
                    await interaction.response.send_message(f"Precisa de anel! Compre com `/comprar item:anel_casamento` ({custo} {config['economia']['moeda_emoji']})", ephemeral=True)
                    return
                # Auto-compra anel se tiver dinheiro
                async with aiosqlite.connect(database.DB_PATH) as db:
                    await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (custo, interaction.user.id, interaction.guild.id))
                    await db.commit()
            else:
                await database.remove_item(interaction.user.id, interaction.guild.id, "anel_casamento", 1)
        
        # Cria pedido
        agora = datetime.datetime.now().isoformat()
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO casamentos_pedidos (guild_id, de_id, para_id, data) VALUES (?, ?, ?, ?)", (interaction.guild.id, interaction.user.id, pessoa.id, agora))
            await db.commit()
        
        embed = discord.Embed(title="💍 Pedido de Casamento!", description=f"{interaction.user.mention} pediu {pessoa.mention} em casamento!", color=config["cores"]["familia"])
        embed.add_field(name="Como aceitar?", value=f"{pessoa.mention} use `/aceitar-casamento` ou `/recusar-casamento`", inline=False)
        embed.set_footer(text=f"Anel custou {custo} {config['economia']['moeda_emoji']}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="aceitar-casamento", description="Aceite um pedido de casamento")
    @check_modulo()
    async def aceitar_casamento(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT de_id FROM casamentos_pedidos WHERE guild_id=? AND para_id=?", (interaction.guild.id, interaction.user.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Nenhum pedido para você!", ephemeral=True)
                    return
                de_id = row[0]
                agora = datetime.datetime.now().isoformat()
                await db.execute("INSERT INTO casamentos (guild_id, user1_id, user2_id, data) VALUES (?, ?, ?, ?)", (interaction.guild.id, de_id, interaction.user.id, agora))
                await db.execute("DELETE FROM casamentos_pedidos WHERE guild_id=? AND para_id=?", (interaction.guild.id, interaction.user.id))
                await db.commit()
        
        de_user = interaction.guild.get_member(de_id)
        embed = discord.Embed(title="💒 Casamento Realizado!", description=f"🎉 {de_user.mention if de_user else f'<@{de_id}>'} e {interaction.user.mention} agora são casados!\n\n💰 Bônus diário de casal: +{config['casamento']['bonus_diario_casado']} {config['economia']['moeda_emoji']} no /daily\n💑 Podem ter filhos com `/ter-filho`\n💸 Herança de 10% compartilhada", color=config["cores"]["familia"])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="recusar-casamento", description="Recuse um pedido")
    @check_modulo()
    async def recusar_casamento(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT de_id FROM casamentos_pedidos WHERE guild_id=? AND para_id=?", (interaction.guild.id, interaction.user.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Nenhum pedido!", ephemeral=True)
                    return
                await db.execute("DELETE FROM casamentos_pedidos WHERE guild_id=? AND para_id=?", (interaction.guild.id, interaction.user.id))
                await db.commit()
        # Devolve anel
        await database.add_item(row[0], interaction.guild.id, "anel_casamento", 1, "casamento")
        await interaction.response.send_message(f"💔 Pedido recusado. Anel devolvido.")

    @app_commands.command(name="divorciar", description="Divorcie-se")
    @check_modulo()
    async def divorciar(self, interaction: discord.Interaction):
        casamento = await self.get_casamento(interaction.guild.id, interaction.user.id)
        if not casamento:
            await interaction.response.send_message("Você não é casado!", ephemeral=True)
            return
        custo = config["casamento"]["custo_divorcio"]
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"] < custo:
            await interaction.response.send_message(f"Divórcio custa {custo} {config['economia']['moeda_emoji']}", ephemeral=True)
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("DELETE FROM casamentos WHERE guild_id=? AND (user1_id=? OR user2_id=?)", (interaction.guild.id, interaction.user.id, interaction.user.id))
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (custo, interaction.user.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"💔 Divórcio realizado! Custou {custo} {config['economia']['moeda_emoji']}")

    @app_commands.command(name="familia", description="Veja sua família")
    @check_modulo()
    async def familia(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        casamento = await self.get_casamento(interaction.guild.id, alvo.id)
        embed = discord.Embed(title=f"👨‍👩‍👧‍👦 Família de {alvo.display_name}", color=config["cores"]["familia"])
        
        if casamento:
            parceiro_id = casamento["parceiro_id"]
            parceiro = interaction.guild.get_member(parceiro_id)
            nome_parc = parceiro.display_name if parceiro else f"User {parceiro_id}"
            embed.add_field(name="💍 Casado com", value=f"{nome_parc} desde <t:{int(datetime.datetime.fromisoformat(casamento['data']).timestamp())}:D>", inline=False)
            
            # Filhos
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT filho_id, nome FROM filhos WHERE guild_id=? AND (parent1_id=? OR parent2_id=?)", (interaction.guild.id, alvo.id, alvo.id)) as cur:
                    filhos = await cur.fetchall()
                    if filhos:
                        txt = "\n".join([f"👶 {nome} (<@{fid}>)" if interaction.guild.get_member(fid) else f"👶 {nome}" for fid, nome in filhos])
                        embed.add_field(name="Filhos", value=txt, inline=False)
                    else:
                        embed.add_field(name="Filhos", value="Nenhum ainda! Use `/ter-filho` (custa 10k)", inline=False)
            
            # Herança: soma dinheiro casal
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT carteira+banco FROM economia WHERE guild_id=? AND user_id=?", (interaction.guild.id, parceiro_id)) as cur:
                    row = await cur.fetchone()
                    parceiro_total = row[0] if row else 0
            dados = await database.get_economia(alvo.id, interaction.guild.id)
            total_casal = dados["carteira"]+dados["banco"] + parceiro_total
            embed.add_field(name="💰 Patrimônio casal", value=f"{config['economia']['moeda_emoji']} {total_casal:,} (10% compartilhado)", inline=False)
        else:
            embed.description = "Solteiro(a) 😢\nUse `/casar @pessoa` para casar!"
            # Verifica se é filho de alguém
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT parent1_id, parent2_id FROM filhos WHERE guild_id=? AND filho_id=?", (interaction.guild.id, alvo.id)) as cur:
                    row = await cur.fetchone()
                    if row:
                        p1 = interaction.guild.get_member(row[0])
                        p2 = interaction.guild.get_member(row[1])
                        n1 = p1.display_name if p1 else f"User {row[0]}"
                        n2 = p2.display_name if p2 else f"User {row[1]}"
                        embed.add_field(name="👪 Pais", value=f"{n1} e {n2}", inline=False)
        
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ter-filho", description="Tenha um filho (precisa ser casado)")
    @check_modulo()
    async def ter_filho(self, interaction: discord.Interaction, nome: str, membro: discord.Member):
        if membro.bot:
            await interaction.response.send_message("Não pode adotar bot como filho!", ephemeral=True)
            return
        casamento = await self.get_casamento(interaction.guild.id, interaction.user.id)
        if not casamento or casamento["parceiro_id"] != membro.id and membro.id != interaction.user.id:
            # Permite ter filho só se casado com a pessoa ou ter filho sozinho? Vamos exigir casal
            # Checa se parceiro é o membro mencionado ou se é inclusão do casal
            parceiro_ok = casamento and (casamento["parceiro_id"]==membro.id or membro.id==interaction.user.id)
            if not parceiro_ok:
                await interaction.response.send_message("Precisa ser casado para ter filho! Ou mencione seu parceiro e a criança.", ephemeral=True)
                return
        
        # membro aqui é a criança na verdade? Vamos reinterpretar: /ter-filho nome: membro: @crianca
        # Se usuário mencionar criança, verifica se criança já tem pais
        # Se membro é parceiro, então usa lógica diferente - vamos ajustar: se casamento existe, o segundo parâmetro pode ser a criança
        
        # Para simplificar: ter-filho nome:filho membro:@crianca (criança é um membro do servidor)
        # Se o casal já tem, verifica custo
        custo = config["casamento"]["custo_filho"]
        dados = await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"] < custo:
            await interaction.response.send_message(f"Custa {custo} {config['economia']['moeda_emoji']} ter um filho!", ephemeral=True)
            return
        
        # Verifica se criança já tem pais
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT * FROM filhos WHERE guild_id=? AND filho_id=?", (interaction.guild.id, membro.id)) as cur:
                if await cur.fetchone():
                    await interaction.response.send_message(f"{membro.display_name} já tem pais!", ephemeral=True)
                    return
        
        # Pega parceiro id
        parceiro_id = casamento["parceiro_id"] if casamento else interaction.user.id
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT INTO filhos (guild_id, filho_id, parent1_id, parent2_id, nome, nascimento) VALUES (?, ?, ?, ?, ?, ?)", (interaction.guild.id, membro.id, interaction.user.id, parceiro_id, nome, datetime.datetime.now().isoformat()))
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE guild_id=? AND user_id=?", (custo, interaction.guild.id, interaction.user.id))
            await db.commit()
        
        embed = discord.Embed(title="👶 Filho registrado!", description=f"{nome} ({membro.mention}) agora é filho de <@{interaction.user.id}> e <@{parceiro_id}>", color=config["cores"]["familia"])
        embed.add_field(name="Herança", value=f"Filho recebe 10% da herança dos pais ao usar `/heranca`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="heranca", description="Receba herança dos pais (filho)")
    @check_modulo()
    async def heranca(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT parent1_id, parent2_id FROM filhos WHERE guild_id=? AND filho_id=?", (interaction.guild.id, interaction.user.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Você não é filho registrado!", ephemeral=True)
                    return
                p1, p2 = row
                # Pega dinheiro dos pais
                async with db.execute("SELECT carteira FROM economia WHERE guild_id=? AND user_id=?", (interaction.guild.id, p1)) as cur2:
                    r1 = await cur2.fetchone()
                    money1 = r1[0] if r1 else 0
                async with db.execute("SELECT carteira FROM economia WHERE guild_id=? AND user_id=?", (interaction.guild.id, p2)) as cur2:
                    r2 = await cur2.fetchone()
                    money2 = r2[0] if r2 else 0
                
                heranca_p1 = int(money1 * config["casamento"]["heranca_percent"])
                heranca_p2 = int(money2 * config["casamento"]["heranca_percent"])
                total = heranca_p1 + heranca_p2
                
                if total <=0:
                    await interaction.response.send_message("Seus pais estão lisos, sem herança!", ephemeral=True)
                    return
                
                await db.execute("UPDATE economia SET carteira=carteira-? WHERE guild_id=? AND user_id=?", (heranca_p1, interaction.guild.id, p1))
                await db.execute("UPDATE economia SET carteira=carteira-? WHERE guild_id=? AND user_id=?", (heranca_p2, interaction.guild.id, p2))
                await db.execute("UPDATE economia SET carteira=carteira+? WHERE guild_id=? AND user_id=?", (total, interaction.guild.id, interaction.user.id))
                await db.commit()
        
        await interaction.response.send_message(f"💰 Você recebeu herança de {config['economia']['moeda_emoji']} {total:,} ({heranca_p1} de pai1 + {heranca_p2} de pai2)")

async def setup(bot):
    await bot.add_cog(Familia(bot))
