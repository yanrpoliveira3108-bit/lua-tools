import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
import database

load_dotenv()

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Pega owner do .env
OWNER_ID = os.getenv("OWNER_ID")

class LuaToolsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config["prefix"]),
            intents=intents,
            help_command=None,
            owner_id=int(OWNER_ID) if OWNER_ID and OWNER_ID.isdigit() else None,
            activity=discord.Activity(type=discord.ActivityType.watching, name=f"Lua Tools | /ajuda | {TAG} | yna.019")
        )
        self.config = config

    async def setup_hook(self):
        await database.init_db()
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and file != "__init__.py" and not file.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                    print(f"[COG] ✅ {file} carregado - {TAG}")
                except Exception as e:
                    import traceback
                    print(f"[ERRO] ❌ Falha ao carregar {file}: {e}")
                    traceback.print_exc()
        try:
            synced = await self.tree.sync()
            print(f"[SYNC] {len(synced)} comandos slash sincronizados - Marca: {TAG}")
        except Exception as e:
            print(f"[ERRO SYNC] {e}")

    async def on_ready(self):
        print(f"✅ {MARCA} - Online como {self.user} | {len(self.guilds)} servidores")
        print(f"🌙 Moeda: {config['economia']['moeda_nome']} | Dono: {TAG} | Owner ID: {OWNER_ID}")

bot = LuaToolsBot()

@bot.tree.command(name="ajuda", description="Central de ajuda Lua Tools - 80+ comandos")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title=f"🌙 {config['nome']} V3 - Todos comandos", description=f"Dev: **{TAG}** | Insta: {config['dono']['insta']} | DC: {config['dono']['discord']}\n{config['dono']['marca_dagua']}", color=config["cores"]["principal"])
    embed.add_field(name="💸 Economia", value="`/carteira` `/daily` `/banco` `/trabalho` `/mochila` `/loja` `/comprar` `/rank`\n`/coinflip` `/apostar` `/loteria` `/doar` `/presentear`", inline=False)
    embed.add_field(name="⚔️ RPG + Poções", value="`/rpg criar/perfil/loja/equipar/cacada/batalhar`\n`/usar item:pocao_vida` `/inventario-usavel`", inline=False)
    embed.add_field(name="🔮 Pokémon + PvP", value="`/pokeloja` `/bolsa` `/capturar` `/pokedex` `/meus-pokemons`\n`/pokemon-batalhar @user` `/pokemon-rank`", inline=False)
    embed.add_field(name="💍 Família", value="`/casar @pessoa` `/aceitar-casamento` `/divorciar` `/familia` `/ter-filho` `/heranca`", inline=False)
    embed.add_field(name="👑 Cargos VIP", value="`/loja-cargos` `/comprar-cargo` `/config-cargo` [ADM]", inline=False)
    embed.add_field(name="🏠 Casa/Móveis", value="`/casa` `/casa-loja` `/comprar-casa` `/moveis-loja` `/comprar-movel`", inline=False)
    embed.add_field(name="⛏️ Farm", value="`/farm minerar` `/farm inventario` `/farm vender` `/farm rank`", inline=False)
    embed.add_field(name="🎉 Eventos", value="`/eventos` `/iniciar-evento` [ADM]", inline=False)
    embed.add_field(name="🎮 Diversão + Utilidades", value="`/8ball` `/ship` `/beijar` `/tapa` `/ppt` `/dado` `/piada` `/meme` `/avatar` `/userinfo` `/afk` `/calcular`", inline=False)
    embed.add_field(name="🔒 Dono yna.019", value="`/dono painel` `/dono addmoney` `/dono setmoney` `/dono anunciar` `/dono reload` `/dev`", inline=False)
    embed.add_field(name="🛠️ Config Modulos", value="`/configurar modulo:nome canal:#canal acao:ativar/desativar`\n`/modulos` - onde cada módulo é ativo\n🌐 Dashboard: `dashboard/app.py`", inline=False)
    embed.set_footer(text=MARCA)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Latência Lua Tools - yna.019")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(title="🏓 Pong!", description=f"Latência: {round(bot.latency*1000)}ms\n{MARCA}", color=config["cores"]["principal"])
    embed.set_footer(text=MARCA)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token or token.startswith("SEU_TOKEN"):
        print(f"❌ {MARCA} - Defina DISCORD_TOKEN no .env")
        print(f"💡 E OWNER_ID no .env também! Seu ID: pegue com modo desenvolvedor Discord")
    else:
        bot.run(token)
