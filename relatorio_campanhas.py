import os
import sys

from dotenv import load_dotenv
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

load_dotenv()

# Uso: python relatorio_campanhas.py [date_preset]  (padrão: last_7d)
periodo = sys.argv[1] if len(sys.argv) > 1 else "last_7d"

account_id = os.getenv("META_AD_ACCOUNT_ID").strip()
if not account_id.startswith("act_"):
    account_id = f"act_{account_id}"

FacebookAdsApi.init(
    app_id=os.getenv("META_APP_ID"),
    app_secret=os.getenv("META_APP_SECRET"),
    access_token=os.getenv("META_ACCESS_TOKEN"),
)

CAMPOS = [
    "campaign_name",
    "spend",
    "impressions",
    "reach",
    "clicks",
    "ctr",
    "cpc",
    "cpm",
    "actions",
    "date_start",
    "date_stop",
]

try:
    linhas = AdAccount(account_id).get_insights(
        fields=CAMPOS,
        params={"level": "campaign", "date_preset": periodo, "limit": 500},
    )
    linhas = list(linhas)
except FacebookRequestError as erro:
    print("Erro ao buscar dados:", erro.api_error_message())
    sys.exit(1)

if not linhas:
    print(f"Nenhuma campanha com veiculação no período ({periodo}).")
    sys.exit(0)

print(f"Período: {linhas[0]['date_start']} a {linhas[0]['date_stop']}\n")

total_gasto = 0.0
total_cliques = 0
total_impressoes = 0

for linha in sorted(linhas, key=lambda l: float(l.get("spend", 0)), reverse=True):
    gasto = float(linha.get("spend", 0))
    cliques = int(linha.get("clicks", 0))
    impressoes = int(linha.get("impressions", 0))
    total_gasto += gasto
    total_cliques += cliques
    total_impressoes += impressoes

    print(f"■ {linha['campaign_name']}")
    print(f"  Gasto: R$ {gasto:,.2f} | Impressões: {impressoes:,} | Alcance: {int(linha.get('reach', 0)):,}")
    print(
        f"  Cliques: {cliques:,} | CTR: {float(linha.get('ctr', 0)):.2f}% | "
        f"CPC: R$ {float(linha.get('cpc', 0)):.2f} | CPM: R$ {float(linha.get('cpm', 0)):.2f}"
    )
    acoes = {a["action_type"]: a["value"] for a in linha.get("actions", [])}
    if acoes:
        resumo = ", ".join(f"{tipo}: {valor}" for tipo, valor in sorted(acoes.items()))
        print(f"  Ações: {resumo}")
    print()

print("TOTAL")
print(f"  Gasto: R$ {total_gasto:,.2f} | Impressões: {total_impressoes:,} | Cliques: {total_cliques:,}")
if total_impressoes:
    print(f"  CTR médio: {total_cliques / total_impressoes * 100:.2f}%")
if total_cliques:
    print(f"  CPC médio: R$ {total_gasto / total_cliques:.2f}")
