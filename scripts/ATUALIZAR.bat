@echo off
title Lua Tools - Atualizar SEM perder dados yna.019
echo.
echo  ============================================
echo   🌙 Lua Tools - Atualizacao Segura
echo   NAO apaga casamentos, economia, pokemons!
echo  ============================================
echo.

echo [1] Fazendo backup do banco atual...
if exist LuaTools\database.db (
    if not exist LuaTools\backups mkdir LuaTools\backups
    copy LuaTools\database.db LuaTools\backups\database_backup_antes_atualizar_%date:~-4,4%-%date:~-7,2%-%date:~-10,2%.db
    echo ✅ Backup criado em LuaTools\backups\
) else (
    echo ⚠️  Nenhum database.db encontrado (primeira instalacao?)
)

echo.
echo [2] Extraia o novo ZIP por CIMA da pasta LuaTools
echo     Quando Windows perguntar, escolha "Substituir arquivos"
echo     O database.db SERA MANTIDO (nao está no ZIP)
echo.

echo [3] Depois de extrair, rode:
echo     cd LuaTools
echo     python main.py
echo.
echo Seus dados: casamentos, economia, pokemons, itens RPG, casas, farm
echo NUNCA sao apagados se voce NAO deletar a pasta LuaTools!
echo.
echo 💡 Dica: Use INSTALADOR_Lua_Tools.py que já preserva database.db automaticamente
echo.
pause
