# 📦 Sistema Modular - Onde cada módulo é ativo

Lua Tools é 100% modular. Escolha em quais canais cada sistema funciona.

## Comandos

### Configurar
```
/configurar modulo:economia acao:desativar canal:#geral
/configurar modulo:pokemon acao:ativar canal:#pokemon-go
/configurar modulo:todos acao:listar
```

**Parâmetros:**
- `modulo`: economia, rpg, pokemon, familia, casa, farm, eventos, diversao, moderacao, todos
- `acao`: ativar, desativar, listar
- `canal`: #canal (vazio = global)

### Ver mapa
```
/modulos
```
Mostra onde cada módulo está ativo por canal.

### Ajuda
```
/modulo-info
```

## Exemplo prático

Servidor com #geral, #economia, #pokemon, #rpg:

```
/configurar modulo:economia acao:desativar canal:#geral
/configurar modulo:economia acao:ativar canal:#economia

/configurar modulo:pokemon acao:ativar canal:#pokemon
/configurar modulo:pokemon acao:desativar canal:#geral

/configurar modulo:rpg acao:ativar canal:#rpg
```

Resultado:
- #geral = só diversão
- #economia = só economia
- #pokemon = só pokemon
- #rpg = só rpg

## Dashboard Web

```
python dashboard/app.py
# http://localhost:5000/guild/SEU_ID
```
Configure pela web também, mesmo banco.
