# 🔔⏱️ Pings e Tics - Spawns Configuráveis

## Pings

Quando algo spawna, pinga um cargo.

```
/configurar-ping modulo:pokemon cargo:@Caçadores canal:#pokemon
/configurar-ping modulo:rpg cargo:@RPG
/configurar-ping modulo:dungeon cargo:@Dungeon
/configurar-ping modulo:loot cargo:@Looters
/configurar-ping modulo:todos cargo:@Spawns (todos de uma vez)
/configurar-ping modulo:pokemon (sem cargo) -> remove
```

Teste:
```
/testar-ping modulo:pokemon
```

## Tics

Tempo de spawn configurável por ADM.

```
/configurar-ticks modulo:pokemon mensagens:10 tempo:60 chance:50 canal:#pokemon
  A cada 10 msgs + 60s cooldown, 50% chance de spawnar pokémon

/configurar-ticks modulo:rpg mensagens:15 tempo:120 chance:30 canal:#rpg
/configurar-ticks modulo:dungeon mensagens:40 tempo:600 chance:10
/configurar-ticks modulo:loot mensagens:30 tempo:400 chance:20
/configurar-ticks modulo:farm mensagens:20 tempo:200 chance:25
```

**Padrões se não configurado:**
- Pokemon: 20 msgs / 180s / 20%
- RPG: 25 / 300 / 15%
- Dungeon: 40 / 600 / 10%
- Loot: 30 / 400 / 20%

## Comandos

```
/pings - vê todos tics e pings configurados
/spawn-forcado modulo:dungeon canal:#geral [ADM]
```

## Mundo - Novos spawns

- 👹 **Mobs RPG**: Botão Atacar, ganha XP + LuaCoins
- 🏰 **Dungeon**: Entra até 3 players, divide recompensa 1000-15000
- 💰 **Loot**: 4 raridades Comum 📦 até Mítico 👑 5000-15000 + bônus itens
