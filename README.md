![Lua Tools Banner](dashboard/static/banner.png)

# 🌙 Lua Tools | Discord Bot Ultimato BR

<p align="center">
  <img src="https://img.shields.io/badge/version-V3%20ULTIMATE%20yna.019-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/discord.py-2.4%2B-7289da?style=for-the-badge&logo=discord" />
  <img src="https://img.shields.io/badge/dev-yna.019-ff69b4?style=for-the-badge" />
  <img src="https://img.shields.io/badge/status-Online-success?style=for-the-badge" />
</p>

<p align="center">
  <a href="https://github.com/yanrpoliveira3108-bit/lua-tools"><img src="https://img.shields.io/github/stars/yanrpoliveira3108-bit/lua-tools?style=social" /></a>
  <a href="https://github.com/yanrpoliveira3108-bit/lua-tools/fork"><img src="https://img.shields.io/github/forks/yanrpoliveira3108-bit/lua-tools?style=social" /></a>
  <a href="https://github.com/yanrpoliveira3108-bit/lua-tools/issues"><img src="https://img.shields.io/github/issues/yanrpoliveira3108-bit/lua-tools" /></a>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
</p>

> **🌙 Lua Tools | Dev: yna.019 | Insta: yna.019 | DC: yna.019 | Anti-Roubo System**  
> O bot Discord mais completo do Brasil - 80+ slash commands, 10 módulos configuráveis, dashboard web, pings, tics, backup anti-perda.

<p align="center">
  <a href="https://railway.app/new/template?template=https://github.com/yanrpoliveira3108-bit/lua-tools"><img src="https://railway.app/button.svg" /></a>
  <a href="https://render.com/deploy?repo=https://github.com/yanrpoliveira3108-bit/lua-tools"><img src="https://render.com/images/deploy-to-render-button.svg" /></a>
</p>

---

## ✨ Features

| Módulo | Descrição | Comandos |
|--------|-----------|----------|
| 💸 Economia | Carteira, banco, 6 empregos com nível, loja, coinflip, loteria | 13 |
| ⚔️ RPG | Classes, 10 equips, caçada PvE, PvP, poções | 7+ |
| 🔮 Pokémon | Spawn com raridade, 5 bolas, PvP, ping cargo | 10 |
| 💍 Família | Casamento, filhos, herança | 6 |
| 👑 Cargos | Loja VIP com dinheiro, expiração auto | 4 |
| 🏠 Casa | 4 casas, 7 móveis, conforto, renda passiva | 6 |
| ⛏️ Farm | 6 recursos, 3 ferramentas, rank | 6 |
| 🎉 Eventos | Hora feliz 2x, chuva pokémon 3x | 3 |
| 🎮 Diversão | 8ball, ship, beijar, ppt, meme +11 | 11 |
| 🛠️ Utilidades | avatar, userinfo, afk, calcular | 7 |
| 🔨 Moderação | limpar, ban, kick, lock | 6 |
| 🌍 Mundo | Mobs RPG, dungeons, loots com pings | 6 |
| 💾 Backup | Anti-perda, auto backup 1h, export | 3 |

**Total: 80+ slash commands | 18 cogs | 18 tabelas**

---

## 🛡️ Anti-Roubo yna.019

Todos embeds, status e dashboard contêm:
```
🌙 Lua Tools | Dev: yna.019 | Insta: yna.019 | DC: yna.019 | Anti-Roubo
```
Comando `/dev` prova autenticidade. Se remover, é cópia.

---

## 🚀 Instalação

### 1 Click (Windows)
```
scripts/INSTALAR_E_RODAR.bat
```

### Manual
```bash
git clone https://github.com/yanrpoliveira3108-bit/lua-tools.git
cd lua-tools
cp .env.example .env
# Edite .env com DISCORD_TOKEN e OWNER_ID
pip install -r requirements.txt
python main.py

# Dashboard em outro terminal:
python dashboard/app.py
# http://localhost:5000
```

Veja mais em [docs/INSTALACAO.md](docs/INSTALACAO.md)

---

## 🔑 .env

```env
DISCORD_TOKEN=seu_token
OWNER_ID=seu_id (Modo desenvolvedor > Copiar ID)
OWNER_TAG=yna.019
OWNER_INSTA=yna.019
OWNER_DISCORD=yna.019
```

---

## 🛠️ Modular - Onde cada módulo é ativo?

```bash
/configurar modulo:economia acao:desativar canal:#geral
/configurar modulo:pokemon acao:ativar canal:#pokemon-go
/modulos -> mapa completo
```

Também no dashboard web: `http://localhost:5000/guild/SEU_ID`

Veja [docs/MODULOS.md](docs/MODULOS.md)

---

## 🔔⏱️ Pings e Tics (Novo!)

```bash
/configurar-ping modulo:pokemon cargo:@Caçadores canal:#pokemon
/configurar-ticks modulo:pokemon mensagens:10 tempo:60 chance:50 canal:#pokemon
/pings -> lista tudo
/testar-ping modulo:pokemon
/spawn-forcado modulo:dungeon canal:#geral [ADM]
```

Veja [docs/PINGS_TICS.md](docs/PINGS_TICS.md)

---

## 💾 Anti-Perda de Dados

NUNCA perca casamentos, economia, pokémons!

- Backup auto pré-init + a cada 1h em `backups/`
- Instalador NÃO sobrescreve `database.db`
- `/backup` / `/backups-lista` / `/exportar-dados`

Veja [docs/BACKUP.md](docs/BACKUP.md)

Atualizar sem perder: [scripts/ATUALIZAR.bat](scripts/ATUALIZAR.bat)

---

## 📋 Comandos

Lista completa em [docs/COMANDOS.md](docs/COMANDOS.md)

---

## 📸 Preview

![Bot Online](https://img.shields.io/badge/bot-online-success)  
Comandos: `/ajuda` `/carteira` `/rpg perfil` `/pokeloja` `/casar @user` `/casa` `/farm minerar` `/pings` `/modulos` `/dev`

---

## 🤝 Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 Licença

MIT - Mantenha créditos `yna.019`

---

<p align="center"><b>🌙 Lua Tools V3 - Dev yna.019 | Insta yna.019 | DC yna.019 | Anti-Roubo System</b></p>
