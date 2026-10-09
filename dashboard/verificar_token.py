"""Confere um token salvo no .env sem exibi-lo.

Uso:  python dashboard/verificar_token.py NOME_DA_VARIAVEL [act_123456789]

Mostra tipo (o ideal é SYSTEM_USER), expiração, permissões, contas visíveis
e testa a leitura de insights da conta informada.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if len(sys.argv) < 2:
    sys.exit("Uso: python dashboard/verificar_token.py NOME_DA_VARIAVEL [act_123456789]")
token = (os.getenv(sys.argv[1]) or "").strip()
if not token:
    sys.exit(f"{sys.argv[1]} está vazio ou não existe no .env (o arquivo foi salvo?)")


def get(caminho, params):
    url = f"https://graph.facebook.com/v23.0/{caminho}?{urllib.parse.urlencode(params)}"
    try:
        return json.load(urllib.request.urlopen(url))
    except urllib.error.HTTPError as erro:
        return json.load(erro)


def data(ts):
    return "nunca" if not ts else datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y")


app_token = f"{os.getenv('META_APP_ID')}|{os.getenv('META_APP_SECRET')}"
d = get("debug_token", {"input_token": token, "access_token": app_token}).get("data", {})
print(f"Tipo: {d.get('type')} | Válido: {d.get('is_valid')} | App: {d.get('application')}")
print(f"Expira: {data(d.get('expires_at'))} | Acesso a dados expira: {data(d.get('data_access_expires_at'))}")
print(f"Permissões: {d.get('scopes')}")

contas = get("me/adaccounts", {"access_token": token, "fields": "name", "limit": 200})
print("Contas visíveis:", [f"{c['name']} ({c['id']})" for c in contas.get("data", [])] or contas.get("error"))

if len(sys.argv) > 2:
    conta = sys.argv[2] if sys.argv[2].startswith("act_") else f"act_{sys.argv[2]}"
    r = get(f"{conta}/insights", {"access_token": token, "fields": "spend", "date_preset": "last_7d"})
    print("Teste de leitura (7 dias):", r.get("data") if "data" in r else r.get("error", {}).get("message"))
