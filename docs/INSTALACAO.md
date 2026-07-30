# 🚀 Instalação Lua Tools

## Requisitos
- Python 3.10+
- Git
- Token Discord: https://discord.com/developers/applications

## 1️⃣ Clone
```bash
git clone https://github.com/yanrpoliveira3108-bit/lua-tools.git
cd lua-tools
```

## 2️⃣ Configure .env
```bash
cp .env.example .env
# Edite .env
DISCORD_TOKEN=seu_token_aqui
OWNER_ID=seu_id_discord (Modo desenvolvedor > Copiar ID)
OWNER_TAG=yna.019
```

## 3️⃣ Instale
```bash
pip install -r requirements.txt
```

## 4️⃣ Rode
```bash
python main.py
# Outro terminal:
python dashboard/app.py
# http://localhost:5000
```

## Windows rápido
Duplo clique `scripts/INSTALAR_E_RODAR.bat`

## Linux rápido
```bash
chmod +x scripts/INSTALAR_E_RODAR.sh
./scripts/INSTALAR_E_RODAR.sh
```

## Atualizar sem perder dados
```bash
# scripts/ATUALIZAR.bat ou .sh
# OU manualmente:
# Extraia novo ZIP por CIMA da pasta, não delete database.db
```

## Deploy Railway/Render
[![Deploy with Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/yanrpoliveira3108-bit/lua-tools)
- Variáveis: DISCORD_TOKEN, OWNER_ID
- Start Command: python main.py
