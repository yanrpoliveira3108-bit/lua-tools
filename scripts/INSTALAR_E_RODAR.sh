#!/bin/bash
echo ""
echo "============================================"
echo " 🌙 Lua Tools V3 ULTIMATE - FINAL"
echo " Instalador Automatico Linux"
echo "============================================"
echo ""

echo "[1/4] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado! Instale python3"
    exit 1
fi
echo "✅ Python3 encontrado: $(python3 --version)"

echo ""
echo "[2/4] Instalando dependências..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Erro ao instalar, tentando com --break-system-packages..."
    pip3 install -r requirements.txt --break-system-packages
fi
echo "✅ Dependências instaladas"

echo ""
echo "[3/4] Configurando .env..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  .env criado! Edite e coloque seu token Discord"
        echo "Abra com: nano .env"
    else
        echo "DISCORD_TOKEN=COLOQUE_SEU_TOKEN_AQUI" > .env
    fi
    echo "📝 Edite agora seu .env? (s/n)"
    read -r resp
    if [ "$resp" = "s" ]; then
        nano .env
    fi
else
    echo "✅ .env já existe"
fi

echo ""
echo "[4/4] Pronto! Como iniciar:"
echo "🌙 Bot: python3 main.py"
echo "🌐 Dashboard: python3 dashboard/app.py (outro terminal) -> http://localhost:5000"
echo ""
echo "Deseja iniciar o BOT agora? (s/n)"
read -r start
if [ "$start" = "s" ]; then
    python3 main.py
fi
