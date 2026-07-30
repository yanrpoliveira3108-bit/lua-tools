import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import aiosqlite
import database
import asyncio

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "pokemon", interaction.channel.id):
            await interaction.response.send_message("❌ Módulo pokemon desativado", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# Stats base por pokemon (simplificado)
POKEMON_BASE_STATS = {
    "pikachu": {"atk": 55, "def": 40, "speed": 90, "tipo": "eletrico"},
    "charizard": {"atk": 84, "def": 78, "speed": 100, "tipo": "fogo"},
    "bulbasaur": {"atk": 49, "def": 49, "speed": 45, "tipo": "planta"},
    "squirtle": {"atk": 48, "def": 65, "speed": 43, "tipo": "agua"},
    "charmander": {"atk": 52, "def": 43, "speed": 65, "tipo": "fogo"},
    "gengar": {"atk": 65, "def": 60, "speed": 110, "tipo": "fantasma"},
    "mewtwo": {"atk": 110, "def": 90, "speed": 130, "tipo": "psiquico"},
    "eevee": {"atk": 55, "def": 50, "speed": 55, "tipo": "normal"},
    "snorlax": {"atk": 110, "def": 65, "speed": 30, "tipo": "normal"},
    "gyarados": {"atk": 125, "def": 79, "speed": 81, "tipo": "agua"},
    "dragonite": {"atk": 134, "def": 95, "speed": 80, "tipo": "dragao"},
}

def get_pokemon_stats(poke_dict):
    nome = poke_dict.get("nome","pikachu").lower()
    nivel = poke_dict.get("nivel", 10)
    base = POKEMON_BASE_STATS.get(nome, {"atk": 50, "def": 50, "speed": 60, "tipo": "normal"})
    # Escala por nível
    atk = base["atk"] + (nivel * 2)
    defe = base["def"] + nivel
    hp = 50 + (nivel * 5) + (base["def"] //2)
    speed = base["speed"] + (nivel //2)
    return {"nome": nome, "nivel": nivel, "atk": atk, "def": defe, "hp": hp, "max_hp": hp, "speed": speed, "tipo": base["tipo"]}

class PokemonPvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.batalhas_ativas = {}  # guild_id -> {desafiante, oponente, pokemons...}

    @app_commands.command(name="pokemon-batalhar", description="Batalhe Pokémon PvP contra alguém!")
    @app_commands.describe(oponente="Quem desafiar", seu_pokemon="ID do seu pokémon (posição na lista, 1=primeiro)")
    @check_modulo()
    async def pokemon_batalhar(self, interaction: discord.Interaction, oponente: discord.Member, seu_pokemon: int = 1):
        if oponente.id == interaction.user.id:
            await interaction.response.send_message("Não pode batalhar consigo mesmo!", ephemeral=True)
            return
        if oponente.bot:
            await interaction.response.send_message("Não pode batalhar contra bot!", ephemeral=True)
            return

        # Pega pokemons dos dois
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message("Você não tem pokémons! Capture com `/capturar`", ephemeral=True)
                    return
                import json as js
                lista1 = js.loads(row[0])
                if not lista1 or seu_pokemon<1 or seu_pokemon>len(lista1):
                    await interaction.response.send_message(f"Pokémon {seu_pokemon} inválido! Você tem {len(lista1)}. Use `/meus-pokemons` pra ver", ephemeral=True)
                    return
                poke1 = lista1[seu_pokemon-1]

            async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (oponente.id, interaction.guild.id)) as cur:
                row2 = await cur.fetchone()
                if not row2:
                    await interaction.response.send_message(f"{oponente.display_name} não tem pokémons!", ephemeral=True)
                    return
                lista2 = js.loads(row2[0])
                if not lista2:
                    await interaction.response.send_message(f"{oponente.display_name} não tem pokémons!", ephemeral=True)
                    return
                # Oponente usa pokemon mais forte automaticamente ou aleatório
                poke2 = max(lista2, key=lambda x: x.get("nivel",0))

        # Cria embed de desafio
        stats1 = get_pokemon_stats(poke1)
        stats2 = get_pokemon_stats(poke2)

        embed = discord.Embed(title="⚔️ Desafio Pokémon!", description=f"{interaction.user.mention} desafiou {oponente.mention}!\n\n**{interaction.user.display_name}**: {poke1['nome'].capitalize()} Nv {poke1['nivel']} (ATK {stats1['atk']} DEF {stats1['def']})\n**{oponente.display_name}**: {poke2['nome'].capitalize()} Nv {poke2['nivel']} (ATK {stats2['atk']} DEF {stats2['def']})\n\n{oponente.mention} aceita?", color=config["cores"]["pokemon"])

        class BatalhaView(discord.ui.View):
            def __init__(self, cog, guild_id, desafiante_id, oponente_id, p1, p2, s1, s2):
                super().__init__(timeout=60)
                self.cog = cog
                self.guild_id = guild_id
                self.desafiante_id = desafiante_id
                self.oponente_id = oponente_id
                self.p1 = p1
                self.p2 = p2
                self.s1 = s1
                self.s2 = s2
                self.resultado = None

            @discord.ui.button(label="Aceitar ✅", style=discord.ButtonStyle.green)
            async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.oponente_id:
                    await interaction.response.send_message("Só o desafiado pode aceitar!", ephemeral=True)
                    return
                await interaction.response.defer()
                # Batalha
                s1 = self.s1.copy()
                s2 = self.s2.copy()
                log = []
                # Determina quem começa por speed
                turno_p1 = s1["speed"] >= s2["speed"]
                
                for round_num in range(20):
                    if turno_p1:
                        dano = max(5, s1["atk"] + random.randint(-10,10) - s2["def"]//2)
                        s2["hp"] -= dano
                        log.append(f"🔥 {self.p1['nome'].capitalize()} causou {dano} em {self.p2['nome'].capitalize()} ({s2['hp']} HP restantes)")
                        if s2["hp"] <=0:
                            vencedor_id = self.desafiante_id
                            vencedor_nome = self.p1['nome']
                            perdedor = self.p2['nome']
                            break
                    else:
                        dano = max(5, s2["atk"] + random.randint(-10,10) - s1["def"]//2)
                        s1["hp"] -= dano
                        log.append(f"💧 {self.p2['nome'].capitalize()} causou {dano} em {self.p1['nome'].capitalize()} ({s1['hp']} HP restantes)")
                        if s1["hp"] <=0:
                            vencedor_id = self.oponente_id
                            vencedor_nome = self.p2['nome']
                            perdedor = self.p1['nome']
                            break
                    turno_p1 = not turno_p1
                else:
                    # Empate por HP
                    if s1["hp"] > s2["hp"]:
                        vencedor_id = self.desafiante_id
                        vencedor_nome = self.p1['nome']
                        perdedor = self.p2['nome']
                    else:
                        vencedor_id = self.oponente_id
                        vencedor_nome = self.p2['nome']
                        perdedor = self.p1['nome']

                # Recompensas
                # XP para pokemons
                async with aiosqlite.connect(database.DB_PATH) as db2:
                    # Dá XP: +10 nivel se vencer?
                    # Simplifica: aumenta nível do vencedor em 1 com 30% chance
                    if random.random() < 0.4:
                        # Atualiza pokemon vencedor
                        import json as js
                        # Carrega lista do vencedor
                        async with db2.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (vencedor_id, self.guild_id)) as cur:
                            row = await cur.fetchone()
                            if row:
                                lista = js.loads(row[0])
                                # Acha pokemon pelo nome e nivel
                                for p in lista:
                                    if p["nome"]==vencedor_nome and p.get("nivel",0)== (s1["nivel"] if vencedor_id==self.desafiante_id else s2["nivel"]):
                                        p["nivel"] = min(100, p.get("nivel",1)+1)
                                        break
                                await db2.execute("UPDATE pokemon_users SET pokemons=? WHERE user_id=? AND guild_id=?", (js.dumps(lista), vencedor_id, self.guild_id))
                                await db2.commit()
                        lvl_msg = f"\n✨ {vencedor_nome.capitalize()} subiu para Nv {p['nivel']}!"
                    else:
                        lvl_msg = ""

                embed_res = discord.Embed(title="🏆 Batalha Pokémon Finalizada!", description=f"Vencedor: <@{vencedor_id}> com **{vencedor_nome.capitalize()}**!\nPerdedor: {perdedor.capitalize()}{lvl_msg}", color=config["cores"]["sucesso"] if vencedor_id==self.desafiante_id else config["cores"]["pokemon"])
                embed_res.add_field(name="Log", value="\n".join(log[-8:]), inline=False)
                embed_res.set_footer(text=f"{self.p1['nome']} Nv{self.p1['nivel']} vs {self.p2['nome']} Nv{self.p2['nivel']}")

                await interaction.followup.send(embed=embed_res)
                self.stop()

            @discord.ui.button(label="Recusar ❌", style=discord.ButtonStyle.red)
            async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.oponente_id:
                    await interaction.response.send_message("Só o desafiado pode recusar!", ephemeral=True)
                    return
                await interaction.response.send_message(f"{interaction.user.mention} recusou a batalha!", ephemeral=False)
                self.stop()

        view = BatalhaView(self, interaction.guild.id, interaction.user.id, oponente.id, poke1, poke2, stats1, stats2)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="pokemon-rank", description="Top treinadores Pokémon")
    @check_modulo()
    async def pokemon_rank(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT user_id, pokemons FROM pokemon_users WHERE guild_id=?", (interaction.guild.id,)) as cur:
                rows = await cur.fetchall()
        
        ranking = []
        import json as js
        for uid, poke_json in rows:
            try:
                lista = js.loads(poke_json)
                total = len(lista)
                nivel_medio = sum([p.get("nivel",1) for p in lista])/total if total else 0
                lendarios = len([p for p in lista if p.get("raridade","comum") in ["lendario","mitico"]])
                score = total*10 + nivel_medio*5 + lendarios*50
                ranking.append((uid, total, nivel_medio, lendarios, score))
            except:
                continue
        
        ranking.sort(key=lambda x: x[4], reverse=True)
        embed = discord.Embed(title="🏆 Top Treinadores Pokémon", color=config["cores"]["pokemon"])
        desc=""
        for i,(uid,total,media,lend,score) in enumerate(ranking[:10],1):
            m = interaction.guild.get_member(uid)
            nome = m.display_name if m else f"User {uid}"
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            desc+=f"{medal} {nome} - {total} pokés - Nv médio {media:.1f} - {lend} lendários - Score {int(score)}\n"
        embed.description = desc or "Ninguém tem pokémon"
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PokemonPvP(bot))
