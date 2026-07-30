@echo off
title Lua Tools - Instalador V3 FINAL
color 0B
echo.
echo  ============================================
echo   🌙 Lua Tools V3 ULTIMATE - FINAL
echo   Instalador Automatico
echo  ============================================
echo.

echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado! Instale Python 3.10+ de python.org
    pause
    exit /b
)
echo ✅ Python encontrado

echo.
echo [2/4] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erro ao instalar dependencias
    pause
    exit /b
)
echo ✅ Dependencias instaladas (discord.py, aiosqlite, Flask)

echo.
echo [3/4] Configurando .env...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo ⚠️  Arquivo .env criado! Voce PRECISA editar e colocar seu token!
        echo.
        echo Abra o arquivo .env e coloque:
        echo DISCORD_TOKEN=seu_token_aqui
        echo.
        notepad .env
    ) else (
        echo DISCORD_TOKEN=COLOQUE_SEU_TOKEN_AQUI > .env
        notepad .env
    )
) else (
    echo ✅ .env ja existe
)

echo.
echo [4/4] Iniciando Lua Tools...
echo.
echo 🌙 Bot: python main.py
echo 🌐 Dashboard: python dashboard/app.py (em outro cmd)
echo 📊 Ambos usam mesmo database.db
echo.
echo Pressione qualquer tecla para iniciar o BOT...
pause >nul

python main.py

pause
