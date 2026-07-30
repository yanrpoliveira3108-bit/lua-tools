#!/bin/bash
echo ""
echo "============================================"
echo " 🌙 Lua Tools - Atualização Segura yna.019"
echo " NÃO apaga casamentos, economia, pokemons!"
echo "============================================"
echo ""

echo "[1] Backup do banco atual..."
if [ -f LuaTools/database.db ]; then
    mkdir -p LuaTools/backups
    cp LuaTools/database.db LuaTools/backups/database_backup_antes_atualizar_$(date +%F_%H-%M).db
    echo "✅ Backup em LuaTools/backups/"
else
    echo "⚠️ Nenhum database.db (primeira instalação?)"
fi

echo ""
echo "[2] Para atualizar, extraia o novo ZIP por CIMA da pasta LuaTools"
echo "    database.db NÃO está no ZIP, então será mantido!"
echo ""
echo "[3] Depois:"
echo "    cd LuaTools"
echo "    pip install -r requirements.txt"
echo "    python main.py"
echo ""
echo "Seus dados são salvos em database.db + backups/ automáticos a cada 1h"
echo "NUNCA delete a pasta LuaTools se não quer perder dados!"
echo ""
