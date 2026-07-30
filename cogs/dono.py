import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]
INSTA = config["dono"]["insta"]
DC = config["dono"]["discord"]

def is_owner():
    async def predicate(interaction: discord.Interaction):
        owner_id = os.getenv("OWNER_ID")
        # Também verifica .env e config
        if not owner_id:
            # Tenta pegar do dono fixo yna.019? Não tem ID fixo, então permite se for o primeiro dono configurado?
            # Por segurança, se OWNER_ID não configurado, só deixa usar se usuário tem permissão admin e avisa
            if interaction.user.guild_permissions.administrator:
                return True
            await interaction.response.send_message("❌ Comando só do proprietário! Configure OWNER_ID no .env", ephemeral=True)
            return False
        try:
            if int(interaction.user.id) == int(owner_id):
                return True
        except:
            pass
        await interaction.response.send_message(f"❌ Só o dono {TAG} pode usar! Você não é proprietário.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class Dono(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    dono_group = app_commands.Group(name="dono", description="🔒 Comandos exclusivos do dono yna.019")

    @dono_group.command(name="painel", description="Painel do proprietário")
    @is_owner()
    async def painel(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🔒 Painel do Dono - Lua Tools", description=f"Dev: **{TAG}**\n{MARCA}\n\nComandos secretos abaixo:", color=config["cores"]["dono"])
        embed.add_field(name="💰 Economia", value="`/dono addmoney @user quantia`\n`/dono removemoney @user quantia`\n`/dono setmoney @user quantia`", inline=False)
        embed.add_field(name="⚙️ Bot", value="`/dono anunciar mensagem`\n`/dono eval código`\n`/dono reload cog:<nome>`\n`/dono shutdown`\n`/dono servidores`", inline=False)
        embed.add_field(name="🛡️ Anti-Roubo", value=f"Marca d'água: **{MARCA}**\nTag: {TAG}\nInsta: {INSTA}\nDiscord: {DC}\nPresente em TODOS os embeds!", inline=False)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @dono_group.command(name="addmoney", description="[DONO] Adicione dinheiro a alguém")
    @is_owner()
    async def addmoney(self, interaction: discord.Interaction, membro: discord.Member, quantia: int):
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (membro.id, interaction.guild.id))
            await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (quantia, membro.id, interaction.guild.id))
            await db.commit()
        embed = discord.Embed(title="✅ Dinheiro adicionado", description=f"{quantia} {config['economia']['moeda_emoji']} para {membro.mention}\n{MARCA}", color=config["cores"]["sucesso"])
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed)

    @dono_group.command(name="removemoney", description="[DONO] Remova dinheiro")
    @is_owner()
    async def removemoney(self, interaction: discord.Interaction, membro: discord.Member, quantia: int):
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE economia SET carteira=carteira-? WHERE user_id=? AND guild_id=?", (quantia, membro.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"✅ Removido {quantia} de {membro.mention}\n{MARCA}", ephemeral=True)

    @dono_group.command(name="setmoney", description="[DONO] Defina dinheiro exato")
    @is_owner()
    async def setmoney(self, interaction: discord.Interaction, membro: discord.Member, quantia: int):
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (membro.id, interaction.guild.id))
            await db.execute("UPDATE economia SET carteira=? WHERE user_id=? AND guild_id=?", (quantia, membro.id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"✅ {membro.mention} agora tem {quantia}\n{MARCA}", ephemeral=True)

    @dono_group.command(name="additem", description="[DONO] Dê item a alguém")
    @is_owner()
    async def additem(self, interaction: discord.Interaction, membro: discord.Member, item: str, quantidade: int = 1):
        await database.add_item(membro.id, interaction.guild.id, item.lower(), quantidade, "geral")
        await interaction.response.send_message(f"✅ {quantidade}x {item} para {membro.mention}\n{MARCA}", ephemeral=True)

    @dono_group.command(name="anunciar", description="[DONO] Anuncie para todos os servidores")
    @is_owner()
    async def anunciar(self, interaction: discord.Interaction, mensagem: str):
        await interaction.response.defer(ephemeral=True)
        count=0
        for guild in self.bot.guilds:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    try:
                        embed=discord.Embed(title="📢 Anúncio Lua Tools", description=mensagem, color=config["cores"]["principal"])
                        embed.set_footer(text=f"De: {TAG} | {MARCA}")
                        await ch.send(embed=embed)
                        count+=1
                        break
                    except:
                        continue
        await interaction.followup.send(f"✅ Anunciado em {count} servidores!\n{MARCA}")

    @dono_group.command(name="reload", description="[DONO] Recarregue um cog")
    @is_owner()
    async def reload(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"✅ Cog {cog} recarregado!\n{MARCA}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)

    @dono_group.command(name="servidores", description="[DONO] Veja servidores do bot")
    @is_owner()
    async def servidores(self, interaction: discord.Interaction):
        desc=""
        for g in self.bot.guilds[:20]:
            desc+=f"{g.name} ({g.id}) - {g.member_count} membros\n"
        embed=discord.Embed(title=f"🌐 Servidores ({len(self.bot.guilds)})", description=desc or "Nenhum", color=config["cores"]["dono"])
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @dono_group.command(name="shutdown", description="[DONO] Desligue o bot")
    @is_owner()
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔴 Desligando Lua Tools... {MARCA}")
        await self.bot.close()

    @dono_group.command(name="eval", description="[DONO] Execute código Python (perigoso!)")
    @is_owner()
    async def eval_cmd(self, interaction: discord.Interaction, codigo: str):
        try:
            # Muito perigoso, só dono mesmo
            res = eval(codigo)
            await interaction.response.send_message(f"✅ Resultado: `{res}`\n{MARCA}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}\n{MARCA}", ephemeral=True)

    # Comando de marca d'água
    @app_commands.command(name="dev", description="Veja dono/dev do bot")
    async def dev(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌙 Lua Tools - Oficial", description=f"**Desenvolvedor:** {TAG}\n**Instagram:** {INSTA}\n**Discord:** {DC}\n\n{MARCA}\n\nBot original, anti-roubo, código protegido!", color=config["cores"]["dono"])
        embed.add_field(name="🛡️ Proteção", value="Todos os embeds e status do bot contêm marca d'água yna.019 - se remover, é cópia!", inline=False)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Dono(bot))
