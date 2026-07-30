import discord
from discord.ext import commands
from discord import app_commands
import json
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

class Configuracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configurar", description=f"[ADM] Configure onde cada módulo funciona - Lua Tools {TAG}")
    @app_commands.describe(
        modulo="Qual módulo? (economia, rpg, pokemon, familia, casa, farm, eventos, diversao, todos)",
        acao="O que fazer?",
        canal="Canal específico (vazio = global na guild toda)"
    )
    @app_commands.choices(
        modulo=[
            app_commands.Choice(name="💸 Economia", value="economia"),
            app_commands.Choice(name="⚔️ RPG", value="rpg"),
            app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
            app_commands.Choice(name="👨‍👩‍👧 Família", value="familia"),
            app_commands.Choice(name="🏠 Casa", value="casa"),
            app_commands.Choice(name="⛏️ Farm/Mineração", value="farm"),
            app_commands.Choice(name="🎉 Eventos", value="eventos"),
            app_commands.Choice(name="🎮 Diversão+Utilidades", value="diversao"),
            app_commands.Choice(name="🔨 Moderação", value="moderacao"),
            app_commands.Choice(name="📦 TODOS os módulos", value="todos"),
        ],
        acao=[
            app_commands.Choice(name="✅ Ativar", value="ativar"),
            app_commands.Choice(name="❌ Desativar", value="desativar"),
            app_commands.Choice(name="📋 Ver status completo", value="listar"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def configurar(self, interaction: discord.Interaction, modulo: str, acao: str, canal: discord.TextChannel = None):
        """
        CORREÇÃO: Antes o comando pedia modulo:economia sem ação e dava erro. Agora:
        Exemplo correto:
        /configurar modulo:economia acao:desativar canal:#geral
        /configurar modulo:pokemon acao:ativar canal:#pokemon
        /configurar modulo:todos acao:listar
        """
        guild_id = interaction.guild.id
        canal_alvo = canal or interaction.channel

        # LISTAR status
        if acao == "listar":
            await interaction.response.defer(ephemeral=True)
            status = await database.get_modulos_status(guild_id)
            embed = discord.Embed(title=f"📋 Status Completo - {interaction.guild.name}", description=f"Use `/configurar modulo:X acao:ativar/desativar canal:#canal`\n{TAG} | {MARCA}", color=config["cores"]["principal"])
            for mod, dados in status.items():
                global_status = "✅ Ativo" if dados["global"] else "❌ Desativado"
                canais_txt = ""
                for ch_id, hab in dados["canais"].items():
                    ch = interaction.guild.get_channel(ch_id)
                    ch_nome = f"#{ch.name}" if ch else f"ID:{ch_id}"
                    canais_txt += f"{ch_nome}: {'✅' if hab else '❌'}\n"
                valor = f"**Global:** {global_status}\n"
                if canais_txt:
                    valor += f"**Por canal:**\n{canais_txt}"
                else:
                    valor += "_Sem exceção por canal (vale global)_"
                # Emoji por modulo
                emoji = {"economia":"💸","rpg":"⚔️","pokemon":"🔮","familia":"👨‍👩‍👧","casa":"🏠","farm":"⛏️","eventos":"🎉","diversao":"🎮","moderacao":"🔨","utilidades":"🛠️"}.get(mod,"📦")
                embed.add_field(name=f"{emoji} {mod.capitalize()}", value=valor, inline=False)
            embed.set_footer(text=f"{MARCA} | Ex: /configurar modulo:economia acao:desativar canal:#geral")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # ATIVAR/DESATIVAR
        habilitado = acao == "ativar"
        modulos_alvo = config["modulos"] if modulo=="todos" else [modulo]

        try:
            async with aiosqlite.connect(database.DB_PATH) as db:
                for mod in modulos_alvo:
                    # Garante guild_config existe
                    await db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
                    # Se tem canal especifico -> por canal, senão global
                    if canal:
                        await db.execute("INSERT OR REPLACE INTO modulos_config (guild_id, modulo, channel_id, habilitado) VALUES (?, ?, ?, ?)", (guild_id, mod, canal_alvo.id, 1 if habilitado else 0))
                    else:
                        # Tenta atualizar global, se coluna não existir ignora (migração antiga)
                        try:
                            await db.execute(f"UPDATE guild_config SET {mod}_enabled=? WHERE guild_id=?", (1 if habilitado else 0, guild_id))
                        except Exception as e:
                            # Coluna não existe, cria via ALTER e tenta de novo
                            try:
                                await db.execute(f"ALTER TABLE guild_config ADD COLUMN {mod}_enabled INTEGER DEFAULT 1")
                                await db.execute(f"UPDATE guild_config SET {mod}_enabled=? WHERE guild_id=?", (1 if habilitado else 0, guild_id))
                            except:
                                pass
                await db.commit()

            emoji_status = "✅" if habilitado else "❌"
            cor = config["cores"]["sucesso"] if habilitado else config["cores"]["erro"]
            desc = f"{emoji_status} **{modulo.upper()}** foi **{acao.upper()}**"
            if modulo=="todos":
                desc += f" (todos os {len(modulos_alvo)} módulos)"
            if canal:
                desc += f"\n📍 Canal: {canal_alvo.mention}\nIsso é uma exceção por canal."
            else:
                desc += f"\n🌐 Global na guild toda\nAfeta todos canais sem exceção."

            embed = discord.Embed(title=f"{emoji_status} Configuração Atualizada!", description=desc, color=cor)
            embed.add_field(name="Comando usado", value=f"`/configurar modulo:{modulo} acao:{acao} {f'canal:{canal_alvo.name}' if canal else 'global'}`", inline=False)
            embed.add_field(name="Verificar", value="Use `/modulos` para ver mapa completo\nUse `/configurar modulo:... acao:listar` para detalhes", inline=False)
            embed.set_footer(text=MARCA)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao configurar: {e}\n{MARCA}", ephemeral=True)

    @app_commands.command(name="modulos", description=f"Veja onde cada módulo está ativo - Lua Tools {TAG}")
    async def modulos_status(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        await interaction.response.defer(ephemeral=True)
        status = await database.get_modulos_status(guild_id)
        
        embed = discord.Embed(
            title=f"📍 Mapa - Onde cada módulo é ativo | {interaction.guild.name}",
            description=f"ADMs configurem com `/configurar`\nEx: `/configurar modulo:economia acao:desativar canal:#geral`\nDev: {TAG} | {MARCA}",
            color=config["cores"]["principal"]
        )
        
        for mod_key in ["economia","rpg","pokemon","familia","casa","farm","eventos","diversao"]:
            dados = status.get(mod_key, {"global": True, "canais": {}})
            emoji = {"economia":"💸","rpg":"⚔️","pokemon":"🔮","familia":"💍","casa":"🏠","farm":"⛏️","eventos":"🎉","diversao":"🎮"}.get(mod_key,"📦")
            global_txt = "✅ Ativo" if dados.get("global") else "❌ Desativado GLOBAL"
            canais = dados.get("canais", {})
            if canais:
                txt = f"**Global:** {global_txt}\n**Exceções:**\n"
                for ch_id, hab in list(canais.items())[:5]:
                    ch = interaction.guild.get_channel(ch_id)
                    nome = ch.mention if ch else f"<#{ch_id}>"
                    txt += f"{nome} {'✅' if hab else '❌'}\n"
                if len(canais)>5:
                    txt += f"+{len(canais)-5} canais..."
            else:
                txt = f"**Global:** {global_txt}\n_Ativo em todos canais (se global ativo)_"
            embed.add_field(name=f"{emoji} {mod_key.capitalize()}", value=txt, inline=True)
        
        embed.add_field(
            name="💡 Como funciona?",
            value="**Global** = vale pra guild toda\n**Por canal** = exceção específica\nSem config = ✅ permitido por padrão\n\n**Exemplos:**\n`/configurar modulo:pokemon acao:ativar canal:#pokemon`\n`/configurar modulo:economia acao:desativar canal:#geral`\n`/configurar modulo:todos acao:listar`",
            inline=False
        )
        embed.set_footer(text=f"{MARCA} | /configurar")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="modulo-info", description="Ajuda sobre sistema modular")
    async def modulo_info(self, interaction: discord.Interaction):
        embed = discord.Embed(title="❓ Como funciona módulos?", description=f"Sistema modular Lua Tools - {TAG}", color=config["cores"]["principal"])
        embed.add_field(name="Comando base", value="`/configurar modulo:<nome> acao:<ativar/desativar/listar> canal:#canal(Opcional)`", inline=False)
        embed.add_field(name="Exemplo prático", value="Servidor com #geral, #economia, #pokemon:\n`/configurar modulo:economia acao:desativar canal:#geral`\n`/configurar modulo:economia acao:ativar canal:#economia`\n`/configurar modulo:pokemon acao:ativar canal:#pokemon`\nPronto! Economia só funciona no #economia, Pokemon só no #pokemon", inline=False)
        embed.add_field(name="Ver mapa", value="`/modulos` - mostra onde cada sistema é ativo\n`/configurar modulo:todos acao:listar` - lista detalhada", inline=False)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Configuracao(bot))
