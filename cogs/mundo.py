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

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

class Mundo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mobs_ativos = {}  # (guild, channel) -> mob data
        self.dungeons_ativas = {}
        self.loots_ativos = {}

    async def get_ping_text(self, guild_id, channel_id, modulo):
        role_id = await database.get_ping_role(guild_id, channel_id, modulo)
        if not role_id:
            role_id = await database.get_ping_role(guild_id, 0, modulo)
        if role_id:
            return f"<@&{role_id}> "
        return ""

    async def spawn_mob(self, guild, channel):
        if not await database.is_modulo_enabled(guild.id, "rpg", channel.id):
            return
        # Verifica se já tem mob
        if (guild.id, channel.id) in self.mobs_ativos:
            return
        
        mob = random.choice(config["rpg"]["monstros"])
        # Adiciona variação
        mob_data = {
            "nome": mob["nome"],
            "vida": mob["vida"],
            "vida_max": mob["vida"],
            "ataque": mob["ataque"],
            "defesa": mob["defesa"],
            "xp": mob["xp"],
            "dinheiro": mob["dinheiro"]
        }
        self.mobs_ativos[(guild.id, channel.id)] = mob_data
        
        ping = await self.get_ping_text(guild.id, channel.id, "rpg")
        
        embed = discord.Embed(title=f"👹 {mob_data['nome']} apareceu!", description=f"Um **{mob_data['nome']}** selvagem surgiu em {channel.mention}!\nVida: {mob_data['vida']} | Ataque: {mob_data['ataque']} | Defesa: {mob_data['defesa']}\n\nClique em **Atacar** para lutar! (Precisa ter `/rpg criar`)", color=config["cores"]["rpg"])
        embed.set_footer(text=f"{MARCA} | Spawn RPG | {TAG}")
        
        class MobView(discord.ui.View):
            def __init__(self, cog, guild_id, channel_id, mob):
                super().__init__(timeout=120)
                self.cog = cog
                self.guild_id = guild_id
                self.channel_id = channel_id
                self.mob = mob
            
            @discord.ui.button(label="⚔️ Atacar", style=discord.ButtonStyle.red)
            async def atacar(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Verifica RPG
                async with aiosqlite.connect(database.DB_PATH) as db:
                    async with db.execute("SELECT nivel, vida, ataque, defesa, equipamentos FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, self.guild_id)) as cur:
                        row = await cur.fetchone()
                        if not row:
                            await interaction.response.send_message("Crie personagem: `/rpg criar`", ephemeral=True)
                            return
                        nivel, vida_user, atk_user, def_user, equip_json = row
                
                import json as js
                equip = js.loads(equip_json) if equip_json else {}
                # Calcula bonus equip
                bonus_atk = sum([config["rpg"]["equipamentos"].get(item_id,{}).get("ataque",0) for item_id in equip.values()])
                bonus_def = sum([config["rpg"]["equipamentos"].get(item_id,{}).get("defesa",0) for item_id in equip.values()])
                atk_total = atk_user + bonus_atk
                def_total = def_user + bonus_def
                
                # Batalha rápida
                mob_vida = self.mob["vida"]
                user_vida = vida_user
                log=[]
                for _ in range(10):
                    dano_u = max(1, atk_total + random.randint(-5,8) - self.mob["defesa"])
                    mob_vida -= dano_u
                    log.append(f"Você causou {dano_u}")
                    if mob_vida <=0:
                        break
                    dano_m = max(1, self.mob["ataque"] + random.randint(-3,5) - def_total)
                    user_vida -= dano_m
                    log.append(f"{self.mob['nome']} causou {dano_m}")
                    if user_vida <=0:
                        break
                
                if user_vida <=0:
                    await interaction.response.send_message(f"💀 Você foi derrotado pelo {self.mob['nome']}! Vida restante mob: {mob_vida}", ephemeral=True)
                    # Não remove mob, outro pode tentar
                else:
                    # Venceu! Remove mob e dá recompensa
                    if (self.guild_id, self.channel_id) in self.cog.mobs_ativos:
                        del self.cog.mobs_ativos[(self.guild_id, self.channel_id)]
                    
                    async with aiosqlite.connect(database.DB_PATH) as db:
                        await db.execute("UPDATE rpg_users SET xp=xp+?, vida=? WHERE user_id=? AND guild_id=?", (self.mob["xp"], user_vida, interaction.user.id, self.guild_id))
                        await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (interaction.user.id, self.guild_id))
                        await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (self.mob["dinheiro"], interaction.user.id, self.guild_id))
                        await db.commit()
                    
                    embed = discord.Embed(title=f"✅ {self.mob['nome']} derrotado!", description=f"{interaction.user.mention} venceu!\n+{self.mob['xp']} XP e {config['economia']['moeda_emoji']} {self.mob['dinheiro']}\n\nLog:\n" + "\n".join(log[-5:]), color=config["cores"]["sucesso"])
                    embed.set_footer(text=MARCA)
                    await interaction.response.send_message(embed=embed)
                    self.stop()
                    try:
                        await interaction.message.delete()
                    except:
                        pass

        view = MobView(self, guild.id, channel.id, mob_data)
        try:
            allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
            await channel.send(content=ping if ping else None, embed=embed, view=view, allowed_mentions=allowed)
            print(f"[MUNDO] Mob {mob_data['nome']} spawn #{channel.name} ping={ping}")
        except Exception as e:
            print(f"[MUNDO] Erro spawn mob: {e}")
            try:
                await channel.send(embed=embed, view=view)
            except:
                pass

    async def spawn_dungeon(self, guild, channel):
        if (guild.id, channel.id) in self.dungeons_ativas:
            return
        dungeons = [
            {"nome": "Caverna Sombria", "nivel_min": 1, "recompensa": 1000, "emoji": "🕳️"},
            {"nome": "Castelo Assombrado", "nivel_min": 5, "recompensa": 3000, "emoji": "🏰"},
            {"nome": "Templo Perdido", "nivel_min": 10, "recompensa": 7000, "emoji": "🏛️"},
            {"nome": "Abismo do Dragão", "nivel_min": 15, "recompensa": 15000, "emoji": "🐉"},
        ]
        dungeon = random.choice(dungeons)
        self.dungeons_ativas[(guild.id, channel.id)] = dungeon
        ping = await self.get_ping_text(guild.id, channel.id, "dungeon")
        
        embed = discord.Embed(title=f"{dungeon['emoji']} Dungeon: {dungeon['nome']}!", description=f"Uma dungeon **{dungeon['nome']}** apareceu!\nNível mínimo: {dungeon['nivel_min']}\nRecompensa: {config['economia']['moeda_emoji']} {dungeon['recompensa']}\n\nClique para entrar! Precisa party ou solo nível {dungeon['nivel_min']}+", color=config["cores"]["principal"])
        embed.set_footer(text=MARCA)
        
        class DungeonView(discord.ui.View):
            def __init__(self, cog, guild_id, channel_id, dungeon):
                super().__init__(timeout=180)
                self.cog = cog
                self.guild_id = guild_id
                self.channel_id = channel_id
                self.dungeon = dungeon
                self.jogadores = []
            
            @discord.ui.button(label="🏰 Entrar na Dungeon", style=discord.ButtonStyle.blurple)
            async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id in self.jogadores:
                    await interaction.response.send_message("Já entrou!", ephemeral=True)
                    return
                # Verifica nivel RPG
                async with aiosqlite.connect(database.DB_PATH) as db:
                    async with db.execute("SELECT nivel FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, self.guild_id)) as cur:
                        row = await cur.fetchone()
                        if not row or row[0] < self.dungeon["nivel_min"]:
                            await interaction.response.send_message(f"Precisa nível {self.dungeon['nivel_min']}! Seu: {row[0] if row else 0}", ephemeral=True)
                            return
                self.jogadores.append(interaction.user.id)
                await interaction.response.send_message(f"✅ Entrou na dungeon! Jogadores: {len(self.jogadores)}/3 - Aguarde 20s ou clique Iniciar", ephemeral=True)
                if len(self.jogadores) >= 3:
                    await self.iniciar_dungeon(interaction)
            
            @discord.ui.button(label="▶️ Iniciar", style=discord.ButtonStyle.green)
            async def iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not self.jogadores:
                    await interaction.response.send_message("Ninguém entrou ainda!", ephemeral=True)
                    return
                await self.iniciar_dungeon(interaction)
            
            async def iniciar_dungeon(self, interaction):
                if (self.guild_id, self.channel_id) not in self.cog.dungeons_ativas:
                    await interaction.followup.send("Dungeon já foi!", ephemeral=True)
                    return
                del self.cog.dungeons_ativas[(self.guild_id, self.channel_id)]
                
                # Simula dungeon: recompensa dividida
                recompensa_total = self.dungeon["recompensa"]
                por_jogador = recompensa_total // max(1, len(self.jogadores))
                
                async with aiosqlite.connect(database.DB_PATH) as db:
                    for uid in self.jogadores:
                        await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (uid, self.guild_id))
                        await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (por_jogador, uid, self.guild_id))
                        await db.execute("UPDATE rpg_users SET xp=xp+? WHERE user_id=? AND guild_id=?", (50, uid, self.guild_id))
                    await db.commit()
                
                mentions = " ".join([f"<@{uid}>" for uid in self.jogadores])
                embed = discord.Embed(title=f"🏆 {self.dungeon['nome']} Concluída!", description=f"Jogadores: {mentions}\nCada um ganhou {config['economia']['moeda_emoji']} {por_jogador} e 50 XP!", color=config["cores"]["sucesso"])
                embed.set_footer(text=MARCA)
                await interaction.followup.send(embed=embed)
                self.stop()
                try:
                    await interaction.message.delete()
                except:
                    pass
        
        view = DungeonView(self, guild.id, channel.id, dungeon)
        try:
            allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
            await channel.send(content=ping if ping else None, embed=embed, view=view, allowed_mentions=allowed)
            print(f"[MUNDO] Dungeon {dungeon['nome']} spawn #{channel.name} ping={ping}")
        except Exception as e:
            print(f"[MUNDO] Erro dungeon: {e}")
            try:
                await channel.send(embed=embed, view=view)
            except:
                pass

    async def spawn_loot(self, guild, channel):
        if (guild.id, channel.id) in self.loots_ativos:
            return
        loots = [
            {"nome": "Baú Comum", "emoji": "📦", "min": 100, "max": 500, "raridade": "comum"},
            {"nome": "Baú Raro", "emoji": "🎁", "min": 500, "max": 1500, "raridade": "raro"},
            {"nome": "Baú Lendário", "emoji": "💎", "min": 1500, "max": 5000, "raridade": "lendario"},
            {"nome": "Baú Mítico", "emoji": "👑", "min": 5000, "max": 15000, "raridade": "mitico"},
        ]
        # Peso raridade
        roll = random.random()
        if roll < 0.6:
            loot = loots[0]
        elif roll < 0.85:
            loot = loots[1]
        elif roll < 0.95:
            loot = loots[2]
        else:
            loot = loots[3]
        
        valor = random.randint(loot["min"], loot["max"])
        # Bonus itens
        itens_bonus = []
        if loot["raridade"] in ["raro","lendario","mitico"]:
            itens_bonus.append(random.choice(["pokebola","pocao_vida","madeira","ferro"]))
        
        self.loots_ativos[(guild.id, channel.id)] = {"loot": loot, "valor": valor, "itens": itens_bonus}
        ping = await self.get_ping_text(guild.id, channel.id, "loot")
        
        cor = {"comum": 0x95a5a6, "raro": 0x3498db, "lendario": 0xf1c40f, "mitico": 0x9b59b6}[loot["raridade"]]
        embed = discord.Embed(title=f"{loot['emoji']} {loot['nome']} apareceu!", description=f"Um **{loot['nome']}** com **{config['economia']['moeda_emoji']} {valor}** surgiu!\nRaridade: {loot['raridade'].upper()}\nSeja o primeiro a clicar em **Abrir**!", color=cor)
        if itens_bonus:
            embed.add_field(name="Bônus", value=", ".join(itens_bonus))
        embed.set_footer(text=MARCA)
        
        class LootView(discord.ui.View):
            def __init__(self, cog, guild_id, channel_id, loot_data):
                super().__init__(timeout=60)
                self.cog = cog
                self.guild_id = guild_id
                self.channel_id = channel_id
                self.loot_data = loot_data
            
            @discord.ui.button(label="📦 Abrir Baú", style=discord.ButtonStyle.green)
            async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
                if (self.guild_id, self.channel_id) not in self.cog.loots_ativos:
                    await interaction.response.send_message("Baú já foi aberto!", ephemeral=True)
                    return
                del self.cog.loots_ativos[(self.guild_id, self.channel_id)]
                
                valor = self.loot_data["valor"]
                async with aiosqlite.connect(database.DB_PATH) as db:
                    await db.execute("INSERT OR IGNORE INTO economia (user_id, guild_id, carteira) VALUES (?, ?, 0)", (interaction.user.id, self.guild_id))
                    await db.execute("UPDATE economia SET carteira=carteira+? WHERE user_id=? AND guild_id=?", (valor, interaction.user.id, self.guild_id))
                    await db.commit()
                for item in self.loot_data["itens"]:
                    await database.add_item(interaction.user.id, self.guild_id, item, 1, "geral")
                
                embed = discord.Embed(title=f"{self.loot_data['loot']['emoji']} Baú Aberto!", description=f"{interaction.user.mention} abriu {self.loot_data['loot']['nome']} e ganhou {config['economia']['moeda_emoji']} {valor} + {', '.join(self.loot_data['itens']) if self.loot_data['itens'] else 'só dinheiro'}!", color=config["cores"]["sucesso"])
                embed.set_footer(text=MARCA)
                await interaction.response.send_message(embed=embed)
                self.stop()
                try:
                    await interaction.message.delete()
                except:
                    pass
        
        view = LootView(self, guild.id, channel.id, {"loot": loot, "valor": valor, "itens": itens_bonus})
        try:
            allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
            await channel.send(content=ping if ping else None, embed=embed, view=view, allowed_mentions=allowed)
            print(f"[MUNDO] Loot {loot['nome']} spawn #{channel.name} ping={ping} valor={valor}")
        except Exception as e:
            print(f"[MUNDO] Erro loot: {e}")
            try:
                await channel.send(embed=embed, view=view)
            except:
                pass

async def setup(bot):
    await bot.add_cog(Mundo(bot))
