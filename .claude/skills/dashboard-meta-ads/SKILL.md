---
name: dashboard-meta-ads
description: Cria e publica o dashboard online de Meta Ads (Facebook/Instagram Ads) de uma conta de anúncios de cliente da agência — analisa a conta, escolhe as métricas certas, gera um token restrito de Usuário do sistema, testa localmente e publica no Render com senha. Use sempre que o usuário pedir dashboard, painel, relatório online, link de acompanhamento ou "tempo real" para uma conta de anúncios, cliente, BM ou portfólio — mesmo que não diga "dashboard" (ex.: "quero mandar pro cliente acompanhar as campanhas", "faz igual o da Versatilis para a Dra. Helena").
---

# Dashboard Meta Ads para um cliente

Esta pasta (`agencia`) já tem um dashboard pronto e genérico. Criar o de um novo cliente
é **configuração, não código**: descobrir a conta, escolher a métrica de resultado,
gerar um token só de leitura para aquela conta e adicionar um serviço no Render.

O usuário é dono de agência e não é programador. Fale em português simples, um passo de
cada vez, e **espere ele confirmar** antes de avançar nos passos que dependem dele
(Meta Business, GitHub, Render). Quando algo na tela dele não bater com as instruções,
peça um print.

## O que já existe

| Arquivo | Papel |
|---|---|
| `dashboard/servidor.py` | Servidor (Python puro + SDK `facebook_business`). Tudo configurado por variáveis de ambiente — ver tabela abaixo. Cache de 55 s, senha via HTTP Basic, `/saude` sem senha para o Render. |
| `dashboard/index.html` | Página: KPIs com comparação ao período anterior, gráficos por dia/hora, tabela de campanhas, filtros de período, auto-atualização a cada 60 s, tema claro/escuro. |
| `dashboard/analisar_conta.py` | `python dashboard/analisar_conta.py act_X` → dono da conta, se está compartilhada com a agência, campanhas, resultados dos últimos 30 dias e **sugestão de métricas**. |
| `dashboard/verificar_token.py` | `python dashboard/verificar_token.py VAR_DO_ENV act_X` → confere um token do `.env` sem exibi-lo. |
| `abrir_dashboard.bat` | Abre o dashboard local: `abrir_dashboard.bat act_X`. |
| `render.yaml` | Um bloco `services:` por cliente. O Render sincroniza a cada `git push`. |
| `.env` | Credenciais locais (fora do git). `META_ACCESS_TOKEN` é o token amplo da agência (enxerga todas as contas); `META_BUSINESS_ID` é o portfólio da agência (BM0). |

Rode Python sempre com `.venv\Scripts\python.exe` e `$env:PYTHONIOENCODING='utf-8'` no PowerShell.

### Variáveis de ambiente do servidor

| Variável | Exemplo | Observação |
|---|---|---|
| `DASHBOARD_CONTA` | `act_1236245618438183` | conta do cliente |
| `DASHBOARD_RESULTADO` / `_NOME` | `onsite_conversion.messaging_conversation_started_7d` / `Conversas iniciadas` | resultado principal (gráfico + KPI + custo por resultado) |
| `DASHBOARD_SECUNDARIO` / `_NOME` | `lead` / `Leads` | segundo KPI e coluna da tabela |
| `DASHBOARD_SENHA` | escolhida pelo usuário | sem ela o dashboard fica aberto |
| `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN` | — | no Render, o token é o **restrito do cliente** |
| `HOST`, `PORT` | `0.0.0.0` / definido pelo Render | só na hospedagem |

## Passo a passo

### 1. Identificar a conta

Se o usuário der só o nome do cliente ou do BM, liste as contas que o token da agência
enxerga e confirme qual é:

```python
from facebook_business.adobjects.user import User
for a in User("me").get_ad_accounts(fields=["name", "business"], params={"limit": 200}):
    print(a["id"], a["name"], (a.get("business") or {}).get("name"))
```

### 2. Analisar a conta e escolher as métricas

Rode `analisar_conta.py`. A sugestão de resultado segue o objetivo real das campanhas
(compras > conversas > leads > cadastros > visualizações de página > cliques > engajamento).
Mostre ao usuário em uma linha o que vai ser o destaque ("o principal vai ser Conversas
iniciadas, o secundário Leads — pode ser?"). Ele conhece o cliente; se disser que o que
importa é outra coisa, use o `action_type` correspondente da lista que o script imprime.

O script também diz se a conta **já está compartilhada com o portfólio da agência** —
isso decide se o passo 4a é necessário.

### 3. Pré-visualizar localmente

Suba numa porta livre, com as métricas escolhidas, e tire um print para conferir:

```powershell
$env:DASHBOARD_PORTA='8052'; $env:DASHBOARD_RESULTADO='...'; $env:DASHBOARD_RESULTADO_NOME='...'
Start-Process .\.venv\Scripts\python.exe -ArgumentList "dashboard\servidor.py","act_X","--sem-navegador" -PassThru -WindowStyle Hidden
```

Print com Edge headless: `msedge --headless=new --window-size=1280,1100 --virtual-time-budget=10000 --screenshot=<scratchpad>\x.png http://127.0.0.1:8052/`.
Encerre o processo depois. Se a conta não tiver veiculação recente, avise o usuário antes
de publicar — um dashboard zerado não é o que ele quer mandar ao cliente.

### 4. Token restrito do cliente (feito pelo usuário no Meta Business)

O token do `.env` enxerga **todas** as contas da agência; ele nunca vai para o Render.
Cada dashboard usa um token de **Usuário do sistema** que não expira, só lê, e só vê
aquela conta. Assim, se vazar, o estrago fica limitado a ler um cliente.

Passe ao usuário, um bloco por vez:

**4a. Compartilhar a conta com a agência** (pule se o script disse que já está)
- business.facebook.com/settings → seletor no canto superior esquerdo → **portfólio do cliente**.
- Contas → Contas de anúncios → a conta → **Atribuir parceiro** → ID do portfólio: valor de `META_BUSINESS_ID` do `.env`.
- **Desligar "Gerenciar contas de anúncios" (Acesso total)** — vem ligado por padrão e acinzenta o resto — e ligar só **Ver desempenho** (ou Gerenciar campanhas, se a agência for operar por ali). Atribuir.
- O aviso "A relação de negócios do parceiro já existe" é normal; clicar Atribuir mesmo assim.

**4b. Criar o Usuário do sistema no portfólio da agência (BM0)**
- Trocar para o portfólio da agência → Usuários → Usuários do sistema → Adicionar.
- Nome `dashboard-<cliente>`, função **Funcionário**.
- Atribuir ativos → Contas de anúncios → a conta do cliente → **só Ver desempenho**.
- Contas → **Apps** → Claude Code Agencia → **Atribuir pessoas** → o usuário do sistema → Desenvolver/Gerenciar app.

**4c. Gerar o token**
- Usuários do sistema → `dashboard-<cliente>` → **Gerar novo token** → app Claude Code Agencia → expiração **Nunca** → só **`ads_read`** → copiar.
- Colar no `.env` como `META_ACCESS_TOKEN_<CLIENTE>=...` e salvar. **Nunca no chat.**

Depois confira com `verificar_token.py META_ACCESS_TOKEN_<CLIENTE> act_X`: tem que dar
`SYSTEM_USER`, expira `nunca`, só `ads_read`, e listar **apenas** a conta do cliente.

Armadilhas que já aconteceram — avise antes que ele caia nelas:
- Em Apps, **"Adicionar → ID do app" é reivindicar o app** (transferir a propriedade). Não fazer; o app pertence ao BM0 e serve a todos os clientes.
- Em Contas de anúncios do BM0, **"Adicionar uma conta de anúncio existente" transfere a conta** do cliente e não pode ser desfeito. O certo é o compartilhamento como parceiro (4a).
- Se a conta não aparece ao atribuir ativos no 4b, o 4a não foi concluído.

### 5. Publicar no Render

Adicione um bloco ao `render.yaml`, copiando o da Versatilis e trocando `name`
(`<cliente>-dashboard`, vira o link `https://<cliente>-dashboard.onrender.com`),
`DASHBOARD_CONTA` e as métricas. Mantenha `sync: false` em `DASHBOARD_SENHA`,
`META_APP_ID`, `META_APP_SECRET` e `META_ACCESS_TOKEN` — segredo não entra no git.

Antes do commit, confira que nenhum token foi parar em arquivo versionado
(`git grep -nE "EAA[A-Za-z0-9]{30}"` não deve achar nada). Faça o commit.

O `git push` precisa ser feito **pelo usuário** no terminal do VS Code (`git push`) —
o login do GitHub abre no navegador e não funciona a partir daqui.

No Render, depois do push:
- O Blueprint sincroniza e cria o serviço novo. Se ele pedir os valores secretos, preencher ali; senão: serviço novo → **Environment** → preencher os 4 (`META_APP_ID` e `META_APP_SECRET` do `.env`, `META_ACCESS_TOKEN` = o token **restrito do cliente**, `DASHBOARD_SENHA` = senha nova escolhida pelo usuário) → **Save, rebuild and deploy**.
- Se o Blueprint não sincronizar sozinho: Blueprints → o blueprint → **Manual Sync**.

Teste daqui: `/saude` deve responder `200 ok` e `/` deve responder `401` sem senha.
A senha você não sabe — peça ao usuário para abrir o link e confirmar que os números aparecem.

Plano grátis: o serviço "dorme" após 15 min sem acesso (1ª abertura ~1 min) e as horas
grátis são compartilhadas entre todos os serviços da conta Render. Para um cliente que
vai abrir com frequência, sugerir o plano Starter daquele serviço.

### 6. Entregar

Dê ao usuário o link e uma mensagem pronta para o cliente, com a senha enviada separada:

> Olá! Preparamos um painel para vocês acompanharem os anúncios no Meta, atualizado automaticamente:
> 🔗 https://<cliente>-dashboard.onrender.com
> Usuário: <cliente> · Senha: [enviar em outra mensagem]
> Ele mostra investimento, <resultado principal>, custo por resultado e o desempenho de cada campanha, com filtros de período. Os números da Meta podem levar de 15 a 30 minutos para aparecer.

## Mudanças no visual ou nas métricas

`servidor.py` e `index.html` são compartilhados por todos os clientes: uma melhoria vale
para todos no próximo `git push`. Se um cliente precisar de algo realmente diferente,
prefira uma nova variável de ambiente a copiar os arquivos — duplicar o código faz as
versões divergirem e cada correção ter que ser feita N vezes.
