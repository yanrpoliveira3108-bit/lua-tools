import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import aiohttp
import aiosqlite
import database
import asyncio

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

POKEBOLAS = config["pokemon"]["pokebolas"]
MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "pokemon", interaction.channel.id):
            embed = discord.Embed(title="❌ Desativado", description=f"**Pokémon** desativado aqui. Use /modulos\n{MARCA}", color=config["cores"]["erro"])
            embed.set_footer(text=MARCA)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# Lista base caso API falhe (primeiros 151 + alguns lendários)
POKEMONS_FALLBACK = [
    {"id": i, "nome": n, "raridade": "comum"} for i, n in enumerate([
        "bulbasaur","ivysaur","venusaur","charmander","charmeleon","charizard","squirtle","wartortle","blastoise","caterpie",
        "metapod","butterfree","weedle","kakuna","beedrill","pidgey","pidgeotto","pidgeot","rattata","raticate",
        "spearow","fearow","ekans","arbok","pikachu","raichu","sandshrew","sandslash","nidoran-f","nidorina"
    ], start=1)
] + [
    {"id": 25, "nome": "pikachu", "raridade": "raro"},
    {"id": 150, "nome": "mewtwo", "raridade": "lendario"},
    {"id": 149, "nome": "dragonite", "raridade": "raro"},
    {"id": 6, "nome": "charizard", "raridade": "raro"},
    {"id": 130, "nome": "gyarados", "raridade": "raro"},
    {"id": 144, "nome": "articuno", "raridade": "lendario"},
    {"id": 145, "nome": "zapdos", "raridade": "lendario"},
    {"id": 146, "nome": "moltres", "raridade": "lendario"},
    {"id": 151, "nome": "mew", "raridade": "mitico"},
    {"id": 249, "nome": "lugia", "raridade": "lendario"},
    {"id": 250, "nome": "ho-oh", "raridade": "lendario"},
    {"id": 384, "nome": "rayquaza", "raridade": "mitico"},
    {"id": 382, "nome": "kyogre", "raridade": "lendario"},
    {"id": 483, "nome": "dialga", "raridade": "mitico"},
    {"id": 484, "nome": "palkia", "raridade": "mitico"},
    {"id": 1000, "nome": "gholdengo", "raridade": "raro"},
]

RARIDADE_PESO = {"comum": 0.55, "raro": 0.28, "lendario": 0.13, "mitico": 0.04}
RARIDADE_COR = {"comum": 0x95a5a6, "raro": 0x3498db, "lendario": 0xf1c40f, "mitico": 0x9b59b6}
RARIDADE_EMOJI = {"comum":"⚪ Comum","raro":"🔵 Raro","lendario":"🟡 Lendário","mitico":"🟣 Mítico"}

# Cache detalhado
POKEMON_CACHE_DETALHADO = {}

class Pokemon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_counts = {}
        self.all_pokemons = []  # Lista com 1010 pokemons da API
        self.bot.loop.create_task(self.load_all_pokemons())

    async def load_all_pokemons(self):
        """Carrega todos os 1010 pokémons da PokéAPI na inicialização - yna.019"""
        await self.bot.wait_until_ready()
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://pokeapi.co/api/v2/pokemon?limit=1010"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        self.all_pokemons = []
                        for idx, entry in enumerate(results, start=1):
                            # name já vem, id é idx
                            self.all_pokemons.append({"id": idx, "nome": entry["name"]})
                        print(f"[POKEMON] {len(self.all_pokemons)} pokémons carregados (1-1010) - yna.019")
                    else:
                        print(f"[POKEMON] Falha ao carregar lista, status {resp.status}, usando fallback")
                        self.all_pokemons = POKEMONS_FALLBACK
        except Exception as e:
            print(f"[POKEMON] Erro load_all_pokemons: {e} - usando fallback")
            self.all_pokemons = POKEMONS_FALLBACK

    async def fetch_pokemon_detalhado(self, pokemon_id_or_nome):
        """Busca detalhes completos do pokémon com foto, gif, vida, ataque, etc - yna.019"""
        cache_key = str(pokemon_id_or_nome).lower()
        if cache_key in POKEMON_CACHE_DETALHADO:
            return POKEMON_CACHE_DETALHADO[cache_key]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://pokeapi.co/api/v2/pokemon/{cache_key}") as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    
                    # Extrai stats
                    stats = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
                    # Tipos
                    tipos = [t["type"]["name"] for t in data.get("types", [])]
                    
                    # Raridade baseada no total de stats ou se é lendário (vamos buscar species)
                    total_stats = sum(stats.values())
                    raridade = "comum"
                    if total_stats >= 600:
                        raridade = "lendario"
                    elif total_stats >= 500:
                        raridade = "raro"
                    elif total_stats >= 670:
                        raridade = "mitico"
                    
                    # Para pokémons específicos lendários/míticos, força raridade
                    lendarios = {150,151,144,145,146,249,250,377,378,379,380,381,382,383,384,483,484,487,643,644,646,716,717,718,800,888,889,890,898,1001,1002,1003,1004}
                    miticos = {151,251,385,386,489,490,491,492,493,494,647,648,719,720,721,801,802,807,808,809,893,1025}
                    if data["id"] in miticos:
                        raridade = "mitico"
                    elif data["id"] in lendarios:
                        raridade = "lendario"
                    
                    # Sprites
                    sprites = data.get("sprites", {})
                    official_artwork = sprites.get("other", {}).get("official-artwork", {}).get("front_default") or sprites.get("front_default")
                    showdown_gif = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/{data['id']}.gif"
                    # Gif animado front
                    animated_front = sprites.get("other", {}).get("showdown", {}).get("front_default") or showdown_gif
                    # Sprite normal
                    front_default = sprites.get("front_default")
                    
                    detalhado = {
                        "id": data["id"],
                        "nome": data["name"],
                        "altura": data["height"] / 10,
                        "peso": data["weight"] / 10,
                        "tipos": tipos,
                        "stats": stats,
                        "total_stats": total_stats,
                        "raridade": raridade,
                        "artwork": official_artwork,
                        "gif": showdown_gif,
                        "animated": animated_front,
                        "sprite": front_default,
                        "base_experience": data.get("base_experience", 0)
                    }
                    POKEMON_CACHE_DETALHADO[cache_key] = detalhado
                    return detalhado
        except Exception as e:
            print(f"[POKEMON] Erro fetch detalhado {cache_key}: {e}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not await database.is_modulo_enabled(message.guild.id, "pokemon", message.channel.id):
            return
        key = f"{message.guild.id}_{message.channel.id}"
        self.message_counts[key] = self.message_counts.get(key, 0) + 1
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemon_nome FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (message.guild.id, message.channel.id)) as cur:
                if await cur.fetchone():
                    return

        tic = await database.get_spawn_tic(message.guild.id, message.channel.id, "pokemon")
        if not tic:
            tic = await database.get_spawn_tic(message.guild.id, 0, "pokemon")
        if not tic:
            tic = {"mensagens": config["pokemon"]["messages_para_spawn"], "tempo_seg": 180, "chance": config["pokemon"]["spawn_chance"]}

        if self.message_counts[key] >= tic["mensagens"]:
            if random.randint(1,100) <= tic["chance"] or self.message_counts[key] >= tic["mensagens"]*1.5:
                await self.spawn_pokemon(message.guild, message.channel)
                self.message_counts[key] = 0

    async def spawn_pokemon(self, guild, channel):
        # Escolhe Pokémon aleatório de TODOS os 1010 - yna.019
        if self.all_pokemons and len(self.all_pokemons) > 100:
            escolhido = random.choice(self.all_pokemons)
            poke_id = escolhido["id"]
            poke_nome = escolhido["nome"]
        else:
            escolhido = random.choice(POKEMONS_FALLBACK)
            poke_id = escolhido["id"]
            poke_nome = escolhido["nome"]
        
        # Busca detalhes completos com foto, gif, vida, ataque, etc
        detalhes = await self.fetch_pokemon_detalhado(poke_id)
        if not detalhes:
            # Fallback sem API
            detalhes = {
                "id": poke_id,
                "nome": poke_nome,
                "tipos": ["desconhecido"],
                "stats": {"hp": random.randint(40,100), "attack": random.randint(40,120), "defense": random.randint(40,100), "speed": random.randint(40,100)},
                "total_stats": random.randint(200,600),
                "raridade": random.choices(list(RARIDADE_PESO.keys()), weights=list(RARIDADE_PESO.values()))[0],
                "artwork": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{poke_id}.png",
                "gif": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/{poke_id}.gif",
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png",
                "altura": random.uniform(0.5, 2.0),
                "peso": random.uniform(5, 100)
            }
        
        raridade = detalhes["raridade"]
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO pokemon_spawns (guild_id, channel_id, pokemon_nome, pokemon_id, raridade) VALUES (?, ?, ?, ?, ?)", (guild.id, channel.id, detalhes["nome"], detalhes["id"], raridade))
            await db.commit()
        
        # Ping role configurado
        role_id = await database.get_ping_role(guild.id, channel.id, "pokemon") or await database.get_ping_role(guild.id, 0, "pokemon")
        ping_text = f"<@&{role_id}> " if role_id else ""
        
        # Monta embed LINDO com foto, gif, vida, ataque, etc - yna.019
        cor = RARIDADE_COR.get(raridade, config["cores"]["pokemon"])
        emoji_rar = RARIDADE_EMOJI.get(raridade, "⚪ Comum")
        
        stats = detalhes["stats"]
        hp = stats.get("hp", 0)
        atk = stats.get("attack", 0)
        defe = stats.get("defense", 0)
        speed = stats.get("speed", 0)
        sp_atk = stats.get("special-attack", 0)
        sp_def = stats.get("special-defense", 0)
        
        embed = discord.Embed(
            title=f"{emoji_rar} - {detalhes['nome'].capitalize()} #{detalhes['id']} apareceu!",
            description=f"{ping_text}Um Pokémon selvagem de **TODOS os 1010** surgiu!\n\n**Dica:** Nome começa com `{detalhes['nome'][0].upper()}` e tem {len(detalhes['nome'])} letras\nUse `/capturar nome:{detalhes['nome']} bola:ultra_bola`",
            color=cor
        )
        # Foto oficial grande
        if detalhes.get("artwork"):
            embed.set_image(url=detalhes["artwork"])
        # Thumbnail com sprite
        if detalhes.get("sprite"):
            embed.set_thumbnail(url=detalhes["sprite"])
        
        # Tipos
        tipos_txt = ", ".join([t.capitalize() for t in detalhes["tipos"]]) if detalhes["tipos"] else "Desconhecido"
        embed.add_field(name="🔷 Tipo", value=tipos_txt, inline=True)
        embed.add_field(name="📏 Altura/Peso", value=f"{detalhes['altura']}m / {detalhes['peso']}kg", inline=True)
        embed.add_field(name="⭐ Raridade", value=emoji_rar, inline=True)
        
        # Vida, Ataque, Defesa, etc
        embed.add_field(name="❤️ Vida", value=f"{hp}", inline=True)
        embed.add_field(name="⚔️ Ataque", value=f"{atk} (Sp: {sp_atk})", inline=True)
        embed.add_field(name="🛡️ Defesa", value=f"{defe} (Sp: {sp_def})", inline=True)
        embed.add_field(name="💨 Velocidade", value=f"{speed}", inline=True)
        embed.add_field(name="📊 Total Stats", value=f"{detalhes['total_stats']}", inline=True)
        embed.add_field(name="🎯 Captura", value=f"Use pokébola! Chance base 60-100% mas {raridade} reduz!", inline=True)
        
        embed.add_field(name="🎬 GIF Animado", value=f"[Clique pra ver GIF]({detalhes['gif']}) - Enviarei GIF abaixo!", inline=False)
        
        embed.set_footer(text=f"#{channel.name} | /pokeloja | {MARCA} | Todos 1010 Pokémons - yna.019")
        
        try:
            allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
            # Mensagem principal com embed
            await channel.send(content=ping_text if ping_text else None, embed=embed, allowed_mentions=allowed)
            # Segunda mensagem com GIF animado (se for diferente da artwork)
            if detalhes.get("gif") and detalhes["gif"] != detalhes.get("artwork"):
                try:
                    embed_gif = discord.Embed(title=f"🎬 {detalhes['nome'].capitalize()} animado!", color=cor)
                    embed_gif.set_image(url=detalhes["gif"])
                    embed_gif.set_footer(text=f"GIF Showdown - {MARCA}")
                    await channel.send(embed=embed_gif)
                except:
                    pass
            print(f"[POKEMON] Spawn {detalhes['nome']} #{detalhes['id']} {raridade} em #{channel.name} Ping={ping_text} Stats={detalhes['total_stats']}")
        except Exception as e:
            print(f"[POKEMON] Erro spawn: {e}")
            try:
                await channel.send(embed=embed)
            except:
                pass

    @app_commands.command(name="pokeloja", description="Loja de Pokébolas - todos 1010 pokémons")
    @check_modulo()
    async def pokeloja(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"🏪 Loja Pokémon - {len(self.all_pokemons) if self.all_pokemons else 1010} Pokémons disponíveis!", description=f"Agora com TODOS os 1010 Pokémons (1-1010)!\nUse `/comprar item:<nome>`\n{MARCA}", color=config["cores"]["pokemon"])
        for ball_id, info in POKEBOLAS.items():
            embed.add_field(name=f"{info['emoji']} {info['nome']} - {info['preco']} {config['economia']['moeda_emoji']}", value=f"Chance: {int(info['chance']*100)}% | ID: `{ball_id}`", inline=False)
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id, "pokemon")
        if inv:
            txt = "\n".join([f"{POKEBOLAS.get(k,{}).get('emoji','')} {k}: {v}" for k,v in inv.items()])
            embed.add_field(name="🎒 Suas Pokébolas", value=txt[:1024], inline=False)
        embed.set_footer(text=f"Todos 1010 Pokémons | {MARCA}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bolsa", description="Suas pokébolas")
    @check_modulo()
    async def bolsa(self, interaction: discord.Interaction):
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id, "pokemon")
        if not inv:
            await interaction.response.send_message(f"🎒 Bolsa vazia! Compre em `/pokeloja`\nGanhe 2 grátis no `/daily`\n{MARCA}", ephemeral=True)
            return
        embed = discord.Embed(title="🎒 Bolsa Pokémon", color=config["cores"]["pokemon"])
        for ball_id, qtd in inv.items():
            info = POKEBOLAS.get(ball_id, {"nome": ball_id, "emoji": "🔴"})
            embed.add_field(name=f"{info['emoji']} {info['nome']}", value=f"Qtd: {qtd}", inline=True)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="capturar", description="Capture o pokémon (todos 1010)")
    @app_commands.describe(nome="Nome do pokémon", bola="Qual pokébola usar")
    @app_commands.choices(bola=[
        app_commands.Choice(name="🔴 Pokébola (60%) - 100", value="pokebola"),
        app_commands.Choice(name="🔵 Grande Bola (80%) - 300", value="grande_bola"),
        app_commands.Choice(name="🟡 Ultra Bola (92%) - 800", value="ultra_bola"),
        app_commands.Choice(name="🟣 Master Bola (100%) - 5000", value="master_bola"),
    ])
    @check_modulo()
    async def capturar(self, interaction: discord.Interaction, nome: str, bola: str = "pokebola"):
        if bola not in POKEBOLAS:
            await interaction.response.send_message(f"Pokébola inválida! Use `/pokeloja`\n{MARCA}", ephemeral=True)
            return
        if not await database.has_item(interaction.user.id, interaction.guild.id, bola, 1):
            await interaction.response.send_message(f"❌ Você não tem {POKEBOLAS[bola]['nome']}! Compre com `/comprar item:{bola}`\n{MARCA}", ephemeral=True)
            return

        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemon_nome, pokemon_id, raridade FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (interaction.guild.id, interaction.channel.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message(f"❌ Nenhum pokémon aqui! Continue conversando.\n{MARCA}", ephemeral=True)
                    return
                nome_correto, poke_id, raridade = row
                if nome.lower() != nome_correto.lower():
                    await interaction.response.send_message(f"❌ Nome errado! Dica: começa com `{nome_correto[0].upper()}` e tem {len(nome_correto)} letras\n{MARCA}", ephemeral=True)
                    return

                await database.remove_item(interaction.user.id, interaction.guild.id, bola, 1)
                base_chance = POKEBOLAS[bola]["chance"]
                mod_raridade = {"comum":1.0,"raro":0.8,"lendario":0.5,"mitico":0.3}.get(raridade,1.0)
                chance_final = base_chance * mod_raridade
                sucesso = random.random() < chance_final

                if sucesso:
                    await db.execute("DELETE FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (interaction.guild.id, interaction.channel.id))
                    async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur2:
                        r2 = await cur2.fetchone()
                        import json as js
                        lista = js.loads(r2[0]) if r2 else []
                        # Pega nivel aleatorio baseado na raridade
                        nivel = random.randint(5,30) if raridade=="comum" else random.randint(20,50) if raridade=="raro" else random.randint(40,70) if raridade=="lendario" else random.randint(60,100)
                        lista.append({"id": poke_id, "nome": nome_correto, "raridade": raridade, "nivel": nivel})
                        await db.execute("INSERT OR REPLACE INTO pokemon_users (user_id, guild_id, pokemons) VALUES (?, ?, ?)", (interaction.user.id, interaction.guild.id, js.dumps(lista)))
                    await db.commit()
                    detalhes = await self.fetch_pokemon_detalhado(poke_id)
                    embed = discord.Embed(title=f"🎉 Capturado! {nome_correto.capitalize()} #{poke_id}", description=f"{interaction.user.mention} capturou **{nome_correto.capitalize()}** [{raridade.upper()}]\nUsou {POKEBOLAS[bola]['emoji']} {POKEBOLAS[bola]['nome']}\nChance {int(chance_final*100)}%\n\n**Stats:** {detalhes['tipos'] if detalhes else ''} | Total {detalhes['total_stats'] if detalhes else ''}\n{MARCA}", color=config["cores"]["sucesso"])
                    if detalhes and detalhes.get("artwork"):
                        embed.set_thumbnail(url=detalhes["artwork"])
                    embed.set_footer(text=MARCA)
                    await interaction.response.send_message(embed=embed)
                else:
                    fugiu = random.random() < 0.3
                    if fugiu:
                        await db.execute("DELETE FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (interaction.guild.id, interaction.channel.id))
                        await db.commit()
                        await interaction.response.send_message(f"💨 **{nome_correto.capitalize()}** escapou! {POKEBOLAS[bola]['emoji']} falhou ({int(chance_final*100)}%) e fugiu!\n{MARCA}")
                    else:
                        await db.commit()
                        await interaction.response.send_message(f"❌ Quase! {POKEBOLAS[bola]['emoji']} falhou ({int(chance_final*100)}%). Tente de novo! Continua ali.\n{MARCA}")

    @app_commands.command(name="pokedex", description="Info completa de qualquer dos 1010 pokémons")
    @check_modulo()
    async def pokedex(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer()
        detalhes = await self.fetch_pokemon_detalhado(nome.lower())
        if not detalhes:
            await interaction.followup.send(f"Pokémon `{nome}` não encontrado! Tente ID 1-1010 ou nome exato.\n{MARCA}")
            return
        
        cor = RARIDADE_COR.get(detalhes["raridade"], config["cores"]["pokemon"])
        embed = discord.Embed(title=f"📖 #{detalhes['id']} {detalhes['nome'].capitalize()} - {RARIDADE_EMOJI.get(detalhes['raridade'])}", description=f"**Tipo:** {', '.join([t.capitalize() for t in detalhes['tipos']])}\n**Altura:** {detalhes['altura']}m | **Peso:** {detalhes['peso']}kg\n{MARCA}", color=cor)
        if detalhes.get("artwork"):
            embed.set_thumbnail(url=detalhes["artwork"])
            embed.set_image(url=detalhes["artwork"])
        
        stats = detalhes["stats"]
        embed.add_field(name="❤️ HP", value=stats.get("hp",0), inline=True)
        embed.add_field(name="⚔️ ATK", value=stats.get("attack",0), inline=True)
        embed.add_field(name="🛡️ DEF", value=stats.get("defense",0), inline=True)
        embed.add_field(name="💨 Speed", value=stats.get("speed",0), inline=True)
        embed.add_field(name="🔮 Sp. ATK", value=stats.get("special-attack",0), inline=True)
        embed.add_field(name="🔰 Sp. DEF", value=stats.get("special-defense",0), inline=True)
        embed.add_field(name="📊 Total", value=detalhes["total_stats"], inline=False)
        embed.add_field(name="🎬 GIF", value=f"[Showdown GIF]({detalhes['gif']})", inline=False)
        embed.set_footer(text=f"Todos 1010 Pokémons | {MARCA}")
        
        # Envia com GIF
        await interaction.followup.send(embed=embed)
        try:
            embed_gif = discord.Embed(color=cor)
            embed_gif.set_image(url=detalhes["gif"])
            await interaction.followup.send(embed=embed_gif)
        except:
            pass

    @app_commands.command(name="meus-pokemons", description="Sua coleção - todos 1010 disponíveis")
    @check_modulo()
    async def meus_pokemons(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message(f"Nenhum pokémon! Continue ativo no chat para spawnar um dos 1010.\n{MARCA}", ephemeral=True)
                    return
                import json as js
                lista = js.loads(row[0])
        if not lista:
            await interaction.response.send_message(f"Nenhum ainda :(\n{MARCA}", ephemeral=True)
            return
        from collections import Counter
        rar_count = Counter([p.get("raridade","comum") for p in lista])
        desc = f"**Total:** {len(lista)}/1010 ({len(lista)/1010*100:.1f}%) | " + " | ".join([f"{rar}: {qtd}" for rar,qtd in rar_count.items()]) + "\n\n"
        for p in lista[-15:]:
            emoji_rar = {"comum":"⚪","raro":"🔵","lendario":"🟡","mitico":"🟣"}.get(p.get("raridade","comum"),"⚪")
            desc += f"{emoji_rar} `#{p['id']}` **{p['nome'].capitalize()}** Nv {p['nivel']}\n"
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name} ({len(lista)}/1010)", description=desc, color=config["cores"]["pokemon"])
        embed.set_footer(text=f"Todos 1010 capturáveis | {MARCA}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pokemon-spawn", description="[ADM] Forçar spawn de Pokémon aleatório dentre 1010")
    @app_commands.default_permissions(manage_guild=True)
    async def force_spawn(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.spawn_pokemon(interaction.guild, interaction.channel)
        await interaction.followup.send(f"✅ Spawn forçado de Pokémon aleatório dentre 1010! {MARCA}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pokemon(bot))
