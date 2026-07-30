import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

EQUIPS = config["rpg"]["equipamentos"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "rpg", interaction.channel.id):
            embed = discord.Embed(title="❌ Desativado", description="**RPG** desativado aqui.", color=config["cores"]["erro"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

def calc_stats(base_ataque, base_defesa, equipamentos_dict):
    bonus_atk = 0
    bonus_def = 0
    for slot, item_id in equipamentos_dict.items():
        if item_id in EQUIPS:
            bonus_atk += EQUIPS[item_id].get("ataque",0)
            bonus_def += EQUIPS[item_id].get("defesa",0)
    return base_ataque + bonus_atk, base_defesa + bonus_def

CLASSES = {
    "guerreiro": {"vida": 120, "ataque": 15, "defesa": 10, "emoji": "⚔️"},
    "mago": {"vida": 80, "ataque": 25, "defesa": 3, "emoji": "🧙"},
    "arqueiro": {"vida": 90, "ataque": 20, "defesa": 5, "emoji": "🏹"},
    "tanque": {"vida": 150, "ataque": 8, "defesa": 15, "emoji": "🛡️"}
}

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    rpg_group = app_commands.Group(name="rpg", description="RPG")

    @rpg_group.command(name="criar", description="Crie seu personagem")
    @app_commands.choices(classe=[
        app_commands.Choice(name="Guerreiro ⚔️ - Equilibrado", value="guerreiro"),
        app_commands.Choice(name="Mago 🧙 - Dano alto", value="mago"),
        app_commands.Choice(name="Arqueiro 🏹 - Ágil", value="arqueiro"),
        app_commands.Choice(name="Tanque 🛡️ - Tank", value="tanque"),
    ])
    @check_modulo()
    async def criar(self, interaction: discord.Interaction, classe: str):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT * FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                if await cur.fetchone():
                    await interaction.response.send_message("Já tem personagem! `/rpg perfil`", ephemeral=True)
                    return
            dados = CLASSES[classe]
            await db.execute("INSERT INTO rpg_users (user_id, guild_id, classe, vida, vida_max, ataque, defesa, nivel, xp, equipamentos) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?)",
                             (interaction.user.id, interaction.guild.id, classe, dados["vida"], dados["vida"], dados["ataque"], dados["defesa"], json.dumps({})))
            await db.commit()
        embed = discord.Embed(title=f"{dados['emoji']} Criado!", description=f"Classe **{classe}** | Vida {dados['vida']} | Atk {dados['ataque']} | Def {dados['defesa']}", color=config["cores"]["rpg"])
        await interaction.response.send_message(embed=embed)

    @rpg_group.command(name="perfil", description="Seu perfil RPG")
    @check_modulo()
    async def perfil(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT classe, nivel, xp, vida, vida_max, ataque, defesa, equipamentos FROM rpg_users WHERE user_id=? AND guild_id=?", (alvo.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message(f"{alvo.display_name} sem personagem! `/rpg criar`", ephemeral=True)
                    return
                classe, nivel, xp, vida, vida_max, atk, defesa, equip_json = row
        equip_dict = json.loads(equip_json) if equip_json else {}
        atk_total, def_total = calc_stats(atk, defesa, equip_dict)
        
        classe_info = CLASSES.get(classe, {})
        embed = discord.Embed(title=f"{classe_info.get('emoji','')} {alvo.display_name} - Nv {nivel}", color=config["cores"]["rpg"])
        embed.add_field(name="Classe", value=classe.capitalize(), inline=True)
        embed.add_field(name="XP", value=f"{xp}/{nivel*100}", inline=True)
        embed.add_field(name="Vida", value=f"{vida}/{vida_max} ❤️", inline=True)
        embed.add_field(name="Ataque", value=f"{atk} + {atk_total-atk} = **{atk_total}** ⚔️", inline=True)
        embed.add_field(name="Defesa", value=f"{defesa} + {def_total-defesa} = **{def_total}** 🛡️", inline=True)
        if equip_dict:
            txt = "\n".join([f"{slot}: {EQUIPS.get(item_id,{}).get('emoji','')} {EQUIPS.get(item_id,{}).get('nome',item_id)}" for slot,item_id in equip_dict.items()])
            embed.add_field(name="🛠️ Equipado", value=txt, inline=False)
        else:
            embed.add_field(name="🛠️ Equipado", value="Nada equipado! Use `/rpg loja`", inline=False)
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @rpg_group.command(name="loja", description="Loja de equipamentos RPG")
    @check_modulo()
    async def loja(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚔️ Ferreiro - Loja RPG", description="Use `/comprar item:<id>` e `/rpg equipar item:<id>`", color=config["cores"]["rpg"])
        for tipo in ["arma","escudo","armadura","acessorio"]:
            itens = {k:v for k,v in EQUIPS.items() if v["tipo"]==tipo}
            if not itens:
                continue
            txt = ""
            for item_id, info in itens.items():
                txt += f"{info['emoji']} **{info['nome']}** (`{item_id}`) - {info['preco']} {config['economia']['moeda_emoji']}\nATK+{info['ataque']} DEF+{info['defesa']} | Nv {info['nivel_min']}\n"
            embed.add_field(name=tipo.upper(), value=txt, inline=False)
        # mostra inventario
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id, "rpg")
        if inv:
            embed.add_field(name="🎒 Seu inventário RPG", value=", ".join([f"{k} x{v}" for k,v in inv.items()]), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rpg_group.command(name="equipar", description="Equipe um item")
    @app_commands.describe(item="ID do item (ex: espada_ferro)")
    @check_modulo()
    async def equipar(self, interaction: discord.Interaction, item: str):
        item = item.lower()
        if item not in EQUIPS:
            await interaction.response.send_message(f"Item não existe. `/rpg loja`", ephemeral=True)
            return
        if not await database.has_item(interaction.user.id, interaction.guild.id, item, 1):
            await interaction.response.send_message(f"Você não tem `{item}`! Compre com `/comprar item:{item}`", ephemeral=True)
            return
        
        info = EQUIPS[item]
        slot = info["tipo"]  # arma, escudo, armadura, acessorio
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT equipamentos FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Crie personagem!", ephemeral=True)
                    return
                equip_dict = json.loads(row[0]) if row[0] else {}
            
            # Se já tem algo no slot, desequipa (mantem no inv)
            equip_dict[slot] = item
            await db.execute("UPDATE rpg_users SET equipamentos=? WHERE user_id=? AND guild_id=?", (json.dumps(equip_dict), interaction.user.id, interaction.guild.id))
            await db.commit()
        
        atk_total, def_total = calc_stats(0,0,{slot:item}) # só bonus do item pra msg
        await interaction.response.send_message(f"✅ Equipado {info['emoji']} **{info['nome']}** no slot `{slot}`! +{info['ataque']} ATK +{info['defesa']} DEF")

    @rpg_group.command(name="inventario", description="Seu inventário RPG")
    @check_modulo()
    async def inventario(self, interaction: discord.Interaction):
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id, "rpg")
        if not inv:
            await interaction.response.send_message("Inventário vazio! `/rpg loja`", ephemeral=True)
            return
        embed = discord.Embed(title="🎒 Inventário RPG", color=config["cores"]["rpg"])
        desc = ""
        for item_id, qtd in inv.items():
            info = EQUIPS.get(item_id, {"nome": item_id, "emoji":"❓"})
            desc += f"{info['emoji']} **{info['nome']}** (`{item_id}`) x{qtd} - ATK+{info.get('ataque',0)} DEF+{info.get('defesa',0)}\n"
        embed.description = desc
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rpg_group.command(name="cacada", description="Caçar monstros PvE")
    @check_modulo()
    async def cacada(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT nivel, vida, ataque, defesa, equipamentos FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Crie personagem primeiro! `/rpg criar`", ephemeral=True)
                    return
                nivel, vida, atk, defesa, equip_json = row
        
        equip_dict = json.loads(equip_json) if equip_json else {}
        atk_total, def_total = calc_stats(atk, defesa, equip_dict)
        
        # Escolhe monstro baseado no nivel
        monstros = config["rpg"]["monstros"]
        # nivel 1-2 slime, 3-5 goblin, etc
        idx = min(len(monstros)-1, max(0, (nivel-1)//2))
        monstros_possiveis = monstros[max(0,idx-1):idx+2]
        monstro = random.choice(monstros_possiveis)
        
        await interaction.response.defer()
        m_vida = monstro["vida"]
        p_vida = vida
        log = [f"⚔️ Você encontrou um **{monstro['nome']}**! (Vida {m_vida})"]
        
        for _ in range(15):
            dano_p = max(1, atk_total + random.randint(-5,10) - monstro["defesa"])
            m_vida -= dano_p
            log.append(f"Você causou {dano_p}")
            if m_vida <=0:
                break
            dano_m = max(1, monstro["ataque"] + random.randint(-3,5) - def_total)
            p_vida -= dano_m
            log.append(f"{monstro['nome']} causou {dano_m}")
            if p_vida <=0:
                break
        
        if p_vida <=0:
            # Perdeu
            async with aiosqlite.connect(database.DB_PATH) as db:
                await db.execute("UPDATE rpg_users SET vida=? WHERE user_id=? AND guild_id=?", (max(1, vida//2), interaction.user.id, interaction.guild.id))
                await db.commit()
            embed = discord.Embed(title="💀 Você foi derrotado!", description=f"Perdeu para **{monstro['nome']}**\nVida reduzida pra {max(1,vida//2)}", color=config["cores"]["erro"])
            embed.add_field(name="Log", value="\n".join(log[-6:]))
            await interaction.followup.send(embed=embed)
        else:
            # Venceu
            xp_gain = monstro["xp"]
            dinheiro = monstro["dinheiro"] + random.randint(0,50)
            async with aiosqlite.connect(database.DB_PATH) as db:
                await db.execute("UPDATE rpg_users SET xp=xp+?, vida=? WHERE user_id=? AND guild_id=?", (xp_gain, p_vida, interaction.user.id, interaction.guild.id))
                await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 1000)", (interaction.user.id, interaction.guild.id))
                await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (dinheiro, interaction.user.id, interaction.guild.id))
                # Chance de dropar item
                if random.random() < 0.15:
                    drop = random.choice(list(EQUIPS.keys())[:4]) # drop itens iniciais
                    await db.commit()
                    await database.add_item(interaction.user.id, interaction.guild.id, drop, 1, "rpg")
                    drop_msg = f"🎁 Dropou **{EQUIPS[drop]['nome']}**!"
                else:
                    drop_msg = ""
                    await db.commit()
            
            # Level up check
            async with aiosqlite.connect(database.DB_PATH) as db:
                async with db.execute("SELECT nivel, xp FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                    nivel_atual, xp_atual = await cur.fetchone()
                    if xp_atual >= nivel_atual*100:
                        await db.execute("UPDATE rpg_users SET nivel=nivel+1, xp=0, vida_max=vida_max+10, ataque=ataque+2, defesa=defesa+1, vida=vida_max WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id))
                        await db.commit()
                        lvl_up = f"\n🎉 **UPOU PARA NÍVEL {nivel_atual+1}!** +10 Vida Max, +2 ATK, +1 DEF"
                    else:
                        lvl_up = ""
            
            embed = discord.Embed(title=f"✅ Venceu {monstro['nome']}!", description=f"+{xp_gain} XP e {config['economia']['moeda_emoji']} {dinheiro}{lvl_up}\n{drop_msg}", color=config["cores"]["sucesso"])
            embed.add_field(name="Log", value="\n".join(log[-6:]))
            await interaction.followup.send(embed=embed)

    @rpg_group.command(name="batalhar", description="PvP contra jogador")
    @check_modulo()
    async def batalhar(self, interaction: discord.Interaction, oponente: discord.Member):
        if oponente.id == interaction.user.id or oponente.bot:
            await interaction.response.send_message("Oponente inválido!", ephemeral=True)
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT classe, nivel, vida_max, ataque, defesa, equipamentos FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                p1 = await cur.fetchone()
            async with db.execute("SELECT classe, nivel, vida_max, ataque, defesa, equipamentos FROM rpg_users WHERE user_id=? AND guild_id=?", (oponente.id, interaction.guild.id)) as cur:
                p2 = await cur.fetchone()
        if not p1 or not p2:
            await interaction.response.send_message("Ambos precisam personagem!", ephemeral=True)
            return
        
        def get_total(p):
            classe,nivel,vida_max,atk,defe,equip_json = p
            equip = json.loads(equip_json) if equip_json else {}
            atkt, deft = calc_stats(atk, defe, equip)
            return vida_max, atkt, deft, equip
        
        p1_vida, p1_atk, p1_def, _ = get_total(p1)
        p2_vida, p2_atk, p2_def, _ = get_total(p2)
        p1_vida_atual = p1_vida
        p2_vida_atual = p2_vida
        log=[]
        for _ in range(12):
            d1 = max(1, p1_atk + random.randint(-4,8) - p2_def)
            p2_vida_atual -= d1
            log.append(f"{interaction.user.display_name} -{d1}")
            if p2_vida_atual <=0:
                vencedor=interaction.user; perdedor=oponente; break
            d2 = max(1, p2_atk + random.randint(-4,8) - p1_def)
            p1_vida_atual -= d2
            log.append(f"{oponente.display_name} -{d2}")
            if p1_vida_atual <=0:
                vencedor=oponente; perdedor=interaction.user; break
        else:
            vencedor = interaction.user if p1_vida_atual>p2_vida_atual else oponente
            perdedor = oponente if vencedor==interaction.user else interaction.user
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("UPDATE rpg_users SET xp=xp+? WHERE user_id=? AND guild_id=?", (30, vencedor.id, interaction.guild.id))
            await db.execute("UPDATE rpg_users SET xp=xp+? WHERE user_id=? AND guild_id=?", (8, perdedor.id, interaction.guild.id))
            await db.commit()
        
        embed = discord.Embed(title="⚔️ Batalha PvP", description=f"{interaction.user.mention} vs {oponente.mention}\nVencedor: {vencedor.mention}", color=config["cores"]["rpg"])
        embed.add_field(name="Placar", value=f"{interaction.user.display_name} {p1_vida_atual} HP restantes\n{oponente.display_name} {p2_vida_atual} HP restantes", inline=False)
        embed.add_field(name="Log", value="\n".join(log[-8:]))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RPG(bot))
