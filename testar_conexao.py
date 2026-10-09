import os
import sys

from dotenv import load_dotenv
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

load_dotenv()

OBRIGATORIOS = ["META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"]

faltando = [nome for nome in OBRIGATORIOS if not os.getenv(nome)]
if faltando:
    print("Campos vazios no .env:", ", ".join(faltando))
    sys.exit(1)

account_id = os.getenv("META_AD_ACCOUNT_ID").strip()
if not account_id.startswith("act_"):
    account_id = f"act_{account_id}"

FacebookAdsApi.init(
    app_id=os.getenv("META_APP_ID"),
    app_secret=os.getenv("META_APP_SECRET"),
    access_token=os.getenv("META_ACCESS_TOKEN"),
)

try:
    conta = AdAccount(account_id).api_get(
        fields=["name", "account_status", "currency", "timezone_name"]
    )
except FacebookRequestError as erro:
    print("Falha na conexão:", erro.api_error_message())
    sys.exit(1)

print("Conexão OK!")
print("Conta:", conta["name"])
print("Moeda:", conta["currency"])
print("Fuso:", conta["timezone_name"])
print("Status:", conta["account_status"], "(1 = ativa)")
