"""Dashboard de Meta Ads.

Uso local:  python dashboard/servidor.py [act_ID_DA_CONTA]   → http://127.0.0.1:8050

Na hospedagem, configure por variáveis de ambiente:
  META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN  credenciais da Meta
  DASHBOARD_CONTA   ID da conta de anúncios (act_...)
  DASHBOARD_SENHA   senha de acesso (o navegador pede usuário e senha; o usuário é livre)
  HOST=0.0.0.0 e PORT (a maioria das hospedagens define PORT sozinha)
"""
import base64
import hmac
import json
import os
import sys
import threading
import time
import webbrowser
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

PASTA = Path(__file__).resolve().parent
load_dotenv(PASTA.parent / ".env")

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CONTA = ARGS[0] if ARGS else os.getenv("DASHBOARD_CONTA", "act_1236245618438183")
if not CONTA.startswith("act_"):
    CONTA = f"act_{CONTA}"
HOST = os.getenv("HOST", "127.0.0.1")
PORTA = int(os.getenv("PORT") or os.getenv("DASHBOARD_PORTA", "8050"))
SENHA = os.getenv("DASHBOARD_SENHA", "")
CACHE_SEGUNDOS = 55
FORCAR_MINIMO_SEGUNDOS = 15
PERIODOS = {"hoje", "ontem", "7d", "14d", "30d", "mes"}
FUSO = timezone(timedelta(hours=-3))  # America/Sao_Paulo (sem horário de verão)

# Resultado principal e secundário (action_type da Meta) — mudam conforme o objetivo do cliente.
RESULTADO = os.getenv("DASHBOARD_RESULTADO", "onsite_conversion.messaging_conversation_started_7d")
RESULTADO_NOME = os.getenv("DASHBOARD_RESULTADO_NOME", "Conversas iniciadas")
SECUNDARIO = os.getenv("DASHBOARD_SECUNDARIO", "lead")
SECUNDARIO_NOME = os.getenv("DASHBOARD_SECUNDARIO_NOME", "Leads")
CAMPOS = ["spend", "impressions", "reach", "inline_link_clicks", "actions"]
CAMPOS_HORA = ["spend", "impressions", "inline_link_clicks", "actions"]
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

FacebookAdsApi.init(
    app_id=os.getenv("META_APP_ID"),
    app_secret=os.getenv("META_APP_SECRET"),
    access_token=os.getenv("META_ACCESS_TOKEN"),
)
conta = AdAccount(CONTA)


def intervalo(periodo):
    hoje = datetime.now(FUSO).date()
    if periodo == "hoje":
        inicio = fim = hoje
    elif periodo == "ontem":
        inicio = fim = hoje - timedelta(days=1)
    elif periodo == "mes":
        inicio, fim = hoje.replace(day=1), hoje
    else:
        dias = {"7d": 7, "14d": 14, "30d": 30}.get(periodo, 7)
        inicio, fim = hoje - timedelta(days=dias - 1), hoje
    duracao = (fim - inicio).days + 1
    fim_ant = inicio - timedelta(days=1)
    return inicio, fim, fim_ant - timedelta(days=duracao - 1), fim_ant


def faixa(inicio, fim):
    return {"since": inicio.isoformat(), "until": fim.isoformat()}


def acao(linha, tipo):
    return sum(float(a["value"]) for a in linha.get("actions", []) if a["action_type"] == tipo)


def resumo(linha):
    gasto = float(linha.get("spend", 0) or 0)
    impressoes = int(linha.get("impressions", 0) or 0)
    cliques = int(linha.get("inline_link_clicks", 0) or 0)
    resultados = acao(linha, RESULTADO)
    secundarios = acao(linha, SECUNDARIO)
    return {
        "gasto": gasto,
        "impressoes": impressoes,
        "alcance": int(linha.get("reach", 0) or 0),
        "cliques": cliques,
        "resultados": resultados,
        "secundarios": secundarios,
        "ctr": cliques / impressoes * 100 if impressoes else None,
        "cpc": gasto / cliques if cliques else None,
        "cpm": gasto / impressoes * 1000 if impressoes else None,
        "custo_resultado": gasto / resultados if resultados else None,
        "custo_secundario": gasto / secundarios if secundarios else None,
    }


def insights(campos, params):
    return [dict(l) for l in conta.get_insights(fields=campos, params={"limit": 500, **params})]


def totais(inicio, fim):
    linhas = insights(CAMPOS, {"time_range": faixa(inicio, fim)})
    return resumo(linhas[0] if linhas else {})


def ate_a_mesma_hora(dia):
    """Totais de `dia` somando só as horas já passadas hoje (comparação justa para 'hoje')."""
    hora_atual = datetime.now(FUSO).hour
    linhas = insights(CAMPOS_HORA, {
        "time_range": faixa(dia, dia),
        "breakdowns": ["hourly_stats_aggregated_by_advertiser_time_zone"],
    })
    soma = {"spend": 0.0, "impressions": 0, "inline_link_clicks": 0, "actions": []}
    for l in linhas:
        if int(l["hourly_stats_aggregated_by_advertiser_time_zone"][:2]) > hora_atual:
            continue
        soma["spend"] += float(l.get("spend", 0) or 0)
        soma["impressions"] += int(l.get("impressions", 0) or 0)
        soma["inline_link_clicks"] += int(l.get("inline_link_clicks", 0) or 0)
        soma["actions"] += l.get("actions", [])
    total = resumo(soma)
    total["alcance"] = None  # alcance não é somável por hora
    return total


def serie(inicio, fim):
    if inicio == fim:
        linhas = insights(CAMPOS_HORA, {
            "time_range": faixa(inicio, fim),
            "breakdowns": ["hourly_stats_aggregated_by_advertiser_time_zone"],
        })
        por_hora = {int(l["hourly_stats_aggregated_by_advertiser_time_zone"][:2]): resumo(l) for l in linhas}
        agora = datetime.now(FUSO)
        ultima = agora.hour if inicio == agora.date() else 23
        return "hora", [
            {"rotulo": f"{h:02d}h", "dica": f"{h:02d}:00–{h:02d}:59", **por_hora.get(h, resumo({}))}
            for h in range(ultima + 1)
        ]
    linhas = insights(CAMPOS, {"time_range": faixa(inicio, fim), "time_increment": 1})
    por_dia = {l["date_start"]: resumo(l) for l in linhas}
    pontos, dia = [], inicio
    while dia <= fim:
        pontos.append({
            "rotulo": dia.strftime("%d/%m"),
            "dica": f"{DIAS_SEMANA[dia.weekday()]}, {dia.strftime('%d/%m/%Y')}",
            **por_dia.get(dia.isoformat(), resumo({})),
        })
        dia += timedelta(days=1)
    return "dia", pontos


def campanhas(inicio, fim):
    status = {
        c["id"]: c for c in conta.get_campaigns(
            fields=["name", "effective_status", "objective"], params={"limit": 200}
        )
    }
    linhas = insights(CAMPOS + ["campaign_id", "campaign_name"], {
        "level": "campaign", "time_range": faixa(inicio, fim),
    })
    resultado, vistos = [], set()
    for l in linhas:
        c = status.get(l["campaign_id"], {})
        vistos.add(l["campaign_id"])
        resultado.append({"nome": l["campaign_name"], "status": c.get("effective_status", "—"), **resumo(l)})
    for id_, c in status.items():
        if id_ not in vistos and c["effective_status"] == "ACTIVE":
            resultado.append({"nome": c["name"], "status": "ACTIVE", **resumo({})})
    return sorted(resultado, key=lambda c: c["gasto"], reverse=True)


_cache, _trava = {}, threading.Lock()
_info_conta = {}


def dados(periodo, forcar=False):
    with _trava:
        guardado = _cache.get(periodo)
        if guardado:
            idade = time.time() - guardado[0]
            if idade < (FORCAR_MINIMO_SEGUNDOS if forcar else CACHE_SEGUNDOS):
                return guardado[1]
        if not _info_conta:
            _info_conta.update(dict(conta.api_get(fields=["name", "currency", "timezone_name"])))
        inicio, fim, inicio_ant, fim_ant = intervalo(periodo)
        granularidade, pontos = serie(inicio, fim)
        payload = {
            "conta": {"id": CONTA, "nome": _info_conta.get("name"), "moeda": _info_conta.get("currency")},
            "metricas": {"resultado": RESULTADO_NOME, "secundario": SECUNDARIO_NOME},
            "periodo": {
                "chave": periodo, "inicio": inicio.isoformat(), "fim": fim.isoformat(),
                "anterior_inicio": inicio_ant.isoformat(), "anterior_fim": fim_ant.isoformat(),
                "granularidade": granularidade,
                "comparacao": "ontem até a mesma hora" if periodo == "hoje" else "período anterior",
            },
            "totais": totais(inicio, fim),
            "anteriores": ate_a_mesma_hora(inicio_ant) if periodo == "hoje" else totais(inicio_ant, fim_ant),
            "serie": pontos,
            "campanhas": campanhas(inicio, fim),
            "atualizado_em": datetime.now(FUSO).isoformat(timespec="seconds"),
        }
        _cache[periodo] = (time.time(), payload)
        return payload


class Handler(BaseHTTPRequestHandler):
    def _enviar(self, codigo, corpo, tipo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _autorizado(self):
        if not SENHA:
            return True
        cabecalho = self.headers.get("Authorization", "")
        if cabecalho.startswith("Basic "):
            try:
                _, _, senha = base64.b64decode(cabecalho[6:]).decode("utf-8").partition(":")
            except ValueError:
                senha = ""
            if hmac.compare_digest(senha.encode(), SENHA.encode()):
                return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Dashboard Meta Ads", charset="UTF-8"')
        self.end_headers()
        return False

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/saude":  # verificação de saúde da hospedagem, sem dados
            self._enviar(200, b"ok", "text/plain")
            return
        if not self._autorizado():
            return
        if url.path in ("/", "/index.html"):
            self._enviar(200, (PASTA / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/dados":
            q = parse_qs(url.query)
            periodo = q.get("periodo", ["7d"])[0]
            if periodo not in PERIODOS:
                periodo = "7d"
            try:
                corpo = dados(periodo, forcar=q.get("forcar", ["0"])[0] == "1")
                self._enviar(200, json.dumps(corpo).encode(), "application/json")
            except FacebookRequestError as erro:
                msg = {"erro": erro.api_error_message(), "codigo": erro.api_error_code()}
                self._enviar(502, json.dumps(msg).encode(), "application/json")
        else:
            self._enviar(404, b"nao encontrado", "text/plain")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    local = HOST in ("127.0.0.1", "localhost")
    endereco = f"http://127.0.0.1:{PORTA}"
    print(f"Dashboard da conta {CONTA} em {HOST}:{PORTA}" + (" (com senha)" if SENHA else ""), flush=True)
    servidor = ThreadingHTTPServer((HOST, PORTA), Handler)
    if local and "--sem-navegador" not in sys.argv:
        threading.Timer(1.0, webbrowser.open, args=[endereco]).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")
