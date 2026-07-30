# 💾 Sistema Anti-Perda de Dados

Lua Tools **NUNCA** apaga casamentos, economia, pokemons, casas, farm ao atualizar.

## Como funciona

1. `database.py` faz backup automático pré-init:
   - Se último backup tem +10min, cria novo em `backups/database_backup_auto_DATA.db`
   - Mantém últimos 15 backups

2. Instalador **NÃO inclui** `database.db` - quando extrai por cima, DB antigo continua

3. Auto backup a cada 1h via `cogs/backup.py`

## Comandos

```
/backup [ADM] - backup manual + stats (quantos users, casamentos, etc)
/backups-lista - lista 10 últimos backups com data/tamanho
/exportar-dados - vê seus dados atuais
```

## Como atualizar sem perder

**NUNCA delete a pasta LuaTools!**

Windows:
- Extraia novo ZIP **por CIMA** da pasta, substituindo arquivos
- Quando perguntar, "Substituir arquivos"
- `database.db` será mantido

Ou use script:
```
scripts/ATUALIZAR.bat
scripts/ATUALIZAR.sh
```

## Restaurar backup manual

Copie arquivo de `backups/` para `database.db`:
```bash
cp backups/database_backup_2024-01-01_12-00.db database.db
```

## Local dos dados

- `database.db` - banco principal SQLite
- `backups/` - backups automáticos
- Tudo ignorado no .gitignore (.env e .db não sobem pro GitHub)
