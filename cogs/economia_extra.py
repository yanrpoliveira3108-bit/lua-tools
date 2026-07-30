import discord
from discord.ext import commands
from discord import app_commands
import json, random, asyncio, aiosqlite, database

with open("config.json","r",encoding="utf-8") as f:
    config=json.load(f)

MOEDA=config["economia"]["moeda_nome"]
EMOJI=config["economia"]["moeda_emoji"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "economia", interaction.channel.id):
            await interaction.response.send_message("❌ Economia desativada aqui", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class EconomiaExtra(commands.Cog):
    def __init__(self, bot):
        self.bot=bot

    @app_commands.command(name="coinflip", description="Cara ou coroa - aposte dinheiro")
    @app_commands.describe(aposta="Quanto apostar", escolha="Cara ou coroa?")
    @app_commands.choices(escolha=[app_commands.Choice(name="Cara", value="cara"), app_commands.Choice(name="Coroa", value="coroa")])
    @check_modulo()
    async def coinflip(self, interaction: discord.Interaction, aposta: int, escolha: str):
        if aposta<=0:
            await interaction.response.send_message("Aposta inválida", ephemeral=True)
            return
        dados=await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"]<aposta:
            await interaction.response.send_message(f"Só tem {dados['carteira']}", ephemeral=True)
            return
        resultado=random.choice(["cara","coroa"])
        ganhou=resultado==escolha
        async with aiosqlite.connect(database.DB_PATH) as db:
            if ganhou:
                await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (aposta, interaction.user.id, interaction.guild.id))
            else:
                await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (aposta, interaction.user.id, interaction.guild.id))
            await db.commit()
        embed=discord.Embed(title="🪙 Coinflip", description=f"Você escolheu **{escolha}**\nResultado: **{resultado}**\n{'🎉 Ganhou' if ganhou else '😢 Perdeu'} {EMOJI} {aposta}", color=config["cores"]["sucesso"] if ganhou else config["cores"]["erro"])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="apostar", description="Aposte e tente dobrar (50% chance)")
    @app_commands.describe(quantia="Quanto apostar")
    @check_modulo()
    async def apostar(self, interaction: discord.Interaction, quantia: int):
        if quantia<=0:
            await interaction.response.send_message("Inválido", ephemeral=True)
            return
        dados=await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"]<quantia:
            await interaction.response.send_message(f"Só tem {dados['carteira']}", ephemeral=True)
            return
        ganhou=random.choice([True,False])
        async with aiosqlite.connect(database.DB_PATH) as db:
            if ganhou:
                await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (quantia, interaction.user.id, interaction.guild.id))
                msg=f"🎉 Dobrou! +{EMOJI} {quantia}"
            else:
                await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (quantia, interaction.user.id, interaction.guild.id))
                msg=f"💸 Perdeu {EMOJI} {quantia}"
            await db.commit()
        await interaction.response.send_message(msg)

    @app_commands.command(name="loteria", description="Loteria da Lua - custa 100, prêmio até 5000")
    @check_modulo()
    async def loteria(self, interaction: discord.Interaction):
        preco=100
        dados=await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"]<preco:
            await interaction.response.send_message(f"Precisa {preco}", ephemeral=True)
            return
        numero_bot=random.randint(1,100)
        numero_user=random.randint(1,100)
        premio=0
        if numero_user==numero_bot:
            premio=5000
        elif abs(numero_user-numero_bot)<=5:
            premio=500
        elif abs(numero_user-numero_bot)<=15:
            premio=100
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (preco, interaction.user.id, interaction.guild.id))
            if premio>0:
                await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (premio, interaction.user.id, interaction.guild.id))
            await db.commit()
        
        embed=discord.Embed(title="🎰 Loteria Lua", description=f"Seu número: {numero_user}\nNúmero sorteado: {numero_bot}\n\n{'🎉 Ganhou ' + str(premio) + ' ' + EMOJI if premio>0 else '😢 Não foi dessa vez'}", color=config["cores"]["loja"])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="doar", description="Doe dinheiro para alguém")
    @check_modulo()
    async def doar(self, interaction: discord.Interaction, membro: discord.Member, quantia: int):
        if quantia<=0 or membro.id==interaction.user.id or membro.bot:
            await interaction.response.send_message("Doação inválida", ephemeral=True)
            return
        dados=await database.get_economia(interaction.user.id, interaction.guild.id)
        if dados["carteira"]<quantia:
            await interaction.response.send_message(f"Só tem {dados['carteira']}", ephemeral=True)
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (quantia, interaction.user.id, interaction.guild.id))
            await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (membro.id, interaction.guild.id))
            await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (quantia, membro.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"💝 {interaction.user.mention} doou {EMOJI} {quantia} para {membro.mention}!")

    @app_commands.command(name="presentear", description="Presenteie um item da mochila")
    @check_modulo()
    async def presentear(self, interaction: discord.Interaction, membro: discord.Member, item: str, quantidade: int=1):
        if membro.id==interaction.user.id or membro.bot:
            await interaction.response.send_message("Inválido", ephemeral=True)
            return
        if not await database.has_item(interaction.user.id, interaction.guild.id, item, quantidade):
            await interaction.response.send_message(f"Você não tem {quantidade}x {item}", ephemeral=True)
            return
        await database.remove_item(interaction.user.id, interaction.guild.id, item, quantidade)
        # Pega tipo do item
        inv=await database.get_inventario(interaction.user.id, interaction.guild.id)
        tipo="geral"
        for i_id,qtd,t in inv:
            if i_id==item:
                tipo=t
                break
        await database.add_item(membro.id, interaction.guild.id, item, quantidade, tipo)
        await interaction.response.send_message(f"🎁 {interaction.user.mention} presenteou {membro.mention} com {quantidade}x {item}!")

async def setup(bot):
    await bot.add_cog(EconomiaExtra(bot))
