# 🌙 Lua Tools - Como subir pro GitHub

Repositório local já foi criado e commitado! ✅
```
Commit: 🌙 Lua Tools V3 ULTIMATE FINAL - 70+ comandos, 8 modulos, dashboard, 15 tabelas
Branch: main
29 files
```

## Passo 1: Criar repositório no GitHub
1. Acesse https://github.com/new
2. Nome do repositório: `lua-tools` ou `Lua-Tools` (como quiser)
3. Descrição: `🌙 Lua Tools - Bot Discord mais completo BR - 70+ comandos, economia, rpg, pokemon, familia, casa, farm, eventos, dashboard`
4. **NÃO marque** "Add README" (já temos)
5. Deixe Public ou Private como preferir
6. Clique **Create repository**

## Passo 2: Conectar e subir (copie e cole no terminal na pasta do bot)

GitHub vai mostrar comandos, use esses:

```bash
# Dentro da pasta LuaTools (onde está o .git)
git remote add origin https://github.com/SEU_USUARIO/lua-tools.git
git push -u origin main
```

**Substitua SEU_USUARIO pelo seu usuário GitHub!**

Exemplo se seu usuário é `yanrpoliveira31`:
```bash
git remote add origin https://github.com/yanrpoliveira31/lua-tools.git
git push -u origin main
```

Vai pedir seu login GitHub:
- Username: seu usuário
- Password: **Use Personal Access Token (PAT)** - não é sua senha normal!
  Crie em: https://github.com/settings/tokens/new
  - Note: Lua Tools Deploy
  - Expiration: 90 days
  - Selecione: `repo` (tudo)
  - Generate token -> Copie e cole como senha

## Passo 3: Pronto!

Seu bot agora estará em:
`https://github.com/SEU_USUARIO/lua-tools`

## Comandos úteis depois:

```bash
# Ver status
git status

# Adicionar mais alterações e subir de novo
git add .
git commit -m "Atualização: novos comandos"
git push

# Baixar em outro PC
git clone https://github.com/SEU_USUARIO/lua-tools.git
```

## Opcional: Tornar bot privado mas instalável

Adicione colaboradores em Settings > Collaborators

## Opcional: Criar página GitHub Pages pro Dashboard

Settings > Pages > Source: main branch /docs
(Precisa mover dashboard pra docs)

---

## Arquivos que NÃO vão pro GitHub (já no .gitignore):
- .env (seu token secreto!)
- database.db (banco local)
- __pycache__
- *.zip

**NUNCA suba seu .env com token!** Use sempre .env.example como modelo.

---

## Quer que eu faça o push automático?

Se você me der um Personal Access Token temporário (pode apagar depois), eu posso fazer o push pra você agora. Mas recomendo fazer manualmente pelos passos acima por segurança.
