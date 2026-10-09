"""Analisa uma conta de anúncios antes de criar o dashboard dela.

Uso:  python dashboard/analisar_conta.py act_123456789

Mostra dono da conta, campanhas, os resultados (action_type) dos últimos 30 dias
e sugere o resultado principal/secundário para DASHBOARD_RESULTADO/SECUNDARIO.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.business import Business
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ordem de prioridade para sugerir o resultado principal, com o nome exibido no dashboard.
RESULTADOS_CONHECIDOS = [
    ("omni_purchase", "Compras"),
    ("offsite_conversion.fb_pixel_purchase", "Compras"),
    ("onsite_conversion.messaging_conversation_started_7d", "Conversas iniciadas"),
    ("lead", "Leads"),
    ("onsite_conversion.lead_grouped", "Leads (formulário)"),
    ("offsite_conversion.fb_pixel_complete_registration", "Cadastros"),
    ("complete_registration", "Cadastros"),
    ("landing_page_view", "Visualizações da página"),
    ("link_click", "Cliques no link"),
    ("post_engagement", "Engajamentos"),
    ("video_view", "Visualizações de vídeo"),
]

if len(sys.argv) < 2:
    sys.exit("Uso: python dashboard/analisar_conta.py act_123456789")
conta_id = sys.argv[1] if sys.argv[1].startswith("act_") else f"act_{sys.argv[1]}"

FacebookAdsApi.init(os.getenv("META_APP_ID"), os.getenv("META_APP_SECRET"), os.getenv("META_ACCESS_TOKEN"))
conta = AdAccount(conta_id)

try:
    info = conta.api_get(fields=["name", "currency", "timezone_name", "account_status", "business"])
except FacebookRequestError as erro:
    sys.exit(f"Não consegui ler a conta {conta_id}: {erro.api_error_message()}")

dono = info.get("business") or {}
print(f"Conta: {info['name']} ({conta_id})")
print(f"Moeda: {info['currency']} | Fuso: {info['timezone_name']} | Status: {info['account_status']} (1 = ativa)")
print(f"Portfólio dono: {dono.get('name', '—')} ({dono.get('id', '—')})")

agencia = os.getenv("META_BUSINESS_ID")
if agencia:
    if dono.get("id") == agencia:
        print("Compartilhada com a agência: a conta já pertence ao portfólio da agência")
    else:
        try:
            clientes = {a["id"] for a in Business(agencia).get_client_ad_accounts(fields=["id"], params={"limit": 500})}
            print("Compartilhada com a agência:", "SIM" if conta_id in clientes else "NÃO (fazer o compartilhamento como parceiro)")
        except FacebookRequestError as erro:
            print("Compartilhada com a agência: não foi possível verificar —", erro.api_error_message())

print("\nCampanhas:")
for c in conta.get_campaigns(fields=["name", "effective_status", "objective"], params={"limit": 200}):
    print(f"  [{c['effective_status']}] {c.get('objective', '')} | {c['name']}")

linhas = list(conta.get_insights(fields=["spend", "actions"], params={"date_preset": "last_30d"}))
if not linhas:
    print("\nSem veiculação nos últimos 30 dias — confirme com o usuário qual resultado acompanhar.")
    sys.exit(0)

gasto = float(linhas[0].get("spend", 0))
acoes = {a["action_type"]: float(a["value"]) for a in linhas[0].get("actions", [])}
print(f"\nÚltimos 30 dias: gasto R$ {gasto:,.2f}")
print("Resultados (action_type → quantidade):")
for tipo, valor in sorted(acoes.items(), key=lambda x: -x[1]):
    print(f"  {tipo}: {valor:,.0f}")

sugestoes = []
for tipo, nome in RESULTADOS_CONHECIDOS:
    if acoes.get(tipo) and nome not in [n for _, n in sugestoes]:
        sugestoes.append((tipo, nome))
print("\nSugestão:")
if sugestoes:
    print(f"  DASHBOARD_RESULTADO={sugestoes[0][0]}")
    print(f"  DASHBOARD_RESULTADO_NOME={sugestoes[0][1]}")
if len(sugestoes) > 1:
    print(f"  DASHBOARD_SECUNDARIO={sugestoes[1][0]}")
    print(f"  DASHBOARD_SECUNDARIO_NOME={sugestoes[1][1]}")
