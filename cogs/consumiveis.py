import discord
from discord.ext import commands
from discord import app_commands
import json
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

class Consumiveis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="usar", description="Use um item do inventário (poção, caixa, etc)")
    @app_commands.describe(item="ID do item", quantidade="Quantidade (padrão 1)")
    async def usar(self, interaction: discord.Interaction, item: str, quantidade: int = 1):
        item = item.lower()
        qtd = quantidade
        
        if not await database.has_item(interaction.user.id, interaction.guild.id, item, qtd):
            await interaction.response.send_message(f"❌ Você não tem {qtd}x `{item}`! Veja `/mochila`", ephemeral=True)
            return
        
        # Poções RPG
        consumiveis_rpg = config["rpg"].get("consumiveis", {})
        if item in consumiveis_rpg:
            info = consumiveis_rpg[item]
            # Cura
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT vida, vida_max, buffs FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                    row = await cur.fetchone()
                    if not row:
                        await interaction.response.send_message("Crie personagem RPG primeiro! `/rpg criar`", ephemeral=True)
                        return
                    vida, vida_max, buffs_json = row
                    buffs = json.loads(buffs_json) if buffs_json else {}
                
                if "cura" in info:
                    cura = info["cura"]
                    if info.get("tipo")=="full":
                        nova_vida = vida_max
                    else:
                        nova_vida = min(vida_max, vida + cura)
                    curada = nova_vida - vida
                    
                    await db.execute("UPDATE rpg_users SET vida=? WHERE user_id=? AND guild_id=?", (nova_vida, interaction.user.id, interaction.guild.id))
                    await db.commit()
                    
                    await database.remove_item(interaction.user.id, interaction.guild.id, item, qtd)
                    
                    embed = discord.Embed(title=f"{info['emoji']} Usou {info['nome']}!", description=f"Recuperou {curada} de vida! {vida} → {nova_vida}/{vida_max} ❤️", color=config["cores"]["sucesso"])
                    await interaction.response.send_message(embed=embed)
                    return
                
                if "bonus_ataque" in info:
                    # Adiciona buff temporário
                    buffs["forca"] = buffs.get("forca", 0) + info["bonus_ataque"]
                    buffs["forca_batalhas"] = info.get("duracao_batalhas", 3)
                    await db.execute("UPDATE rpg_users SET buffs=? WHERE user_id=? AND guild_id=?", (json.dumps(buffs), interaction.user.id, interaction.guild.id))
                    await db.commit()
                    await database.remove_item(interaction.user.id, interaction.guild.id, item, qtd)
                    await interaction.response.send_message(f"💪 Usou {info['nome']}! +{info['bonus_ataque']} ATK por {info['duracao_batalhas']} batalhas!")
                    return
        
        # Caixa misteriosa economia
        if item == "caixa_misteriosa":
            import random
            premios = [
                ("dinheiro", random.randint(500, 5000)),
                ("pokebola", random.randint(1,5)),
                ("pocao_vida", random.randint(1,3)),
                ("nada", 0)
            ]
            premio_tipo, premio_qtd = random.choice(premios)
            
            await database.remove_item(interaction.user.id, interaction.guild.id, item, 1)
            
            if premio_tipo == "dinheiro":
                async with aiosqlite.connect(database.DB_PATH) as db:
                    await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (interaction.user.id, interaction.guild.id))
                    await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (premio_qtd, interaction.user.id, interaction.guild.id))
                    await db.commit()
                await interaction.response.send_message(f"🎁 Caixa aberta! Ganhou {config['economia']['moeda_emoji']} {premio_qtd}!")
            elif premio_tipo == "nada":
                await interaction.response.send_message(f"🎁 Caixa aberta! ... veio vazia 😢")
            else:
                await database.add_item(interaction.user.id, interaction.guild.id, premio_tipo, premio_qtd, "geral" if premio_tipo!="pokebola" else "pokemon")
                await interaction.response.send_message(f"🎁 Caixa aberta! Ganhou {premio_qtd}x {premio_tipo}!")
            return
        
        if item == "roubo_protegido":
            # Ativa proteção 24h - salva no inventario como buff? Simplifica: adiciona flag em economia?
            # Vamos usar eventos_ativos como proteção?
            import datetime
            async with aiosqlite.connect(database.DB_PATH) as db:
                agora = datetime.datetime.now()
                fim = agora + datetime.timedelta(hours=24)
                await db.execute("INSERT OR REPLACE INTO eventos_ativos (guild_id, evento_id, tipo, multiplicador, inicio, fim) VALUES (?, ?, ?, ?, ?, ?)",
                                 (interaction.guild.id, f"protecao_{interaction.user.id}", "protecao_roubo", 0, agora.isoformat(), fim.isoformat()))
                await db.commit()
            await database.remove_item(interaction.user.id, interaction.guild.id, item, 1)
            await interaction.response.send_message(f"🔫 Proteção contra roubo ativada por 24h! Até <t:{int(fim.timestamp())}:F>")
            return
        
        # Se chegou aqui, item não usável
        await interaction.response.send_message(f"❓ Item `{item}` não é usável ou não tem uso implementado. Use `/mochila` pra ver itens.", ephemeral=True)

    @app_commands.command(name="inventario-usavel", description="Veja itens usáveis")
    async def inventario_usavel(self, interaction: discord.Interaction):
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id)
        if not inv:
            await interaction.response.send_message("Mochila vazia!", ephemeral=True)
            return
        
        consumiveis_rpg = config["rpg"].get("consumiveis", {})
        usaveis = []
        for item_id, qtd, tipo in inv:
            if item_id in consumiveis_rpg or item_id in ["caixa_misteriosa", "roubo_protegido"]:
                usaveis.append(f"`{item_id}` x{qtd} - use `/usar item:{item_id}`")
        
        if not usaveis:
            await interaction.response.send_message("Nenhum item usável! Compre poções em `/loja` ou `/rpg loja`", ephemeral=True)
            return
        
        embed = discord.Embed(title="🧪 Itens usáveis", description="\n".join(usaveis), color=config["cores"]["sucesso"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Consumiveis(bot))
