"""
Geocodificação de endereços (Google Geocoding API) com 3 tentativas automáticas + cache

O que faz:
- Lê base_data_lojas.xlsx (coluna "Endereço")
- Para cada endereço, tenta:
  T1) endereço original
  T2) endereço original + ", Brasil"
  T3) endereço simplificado + ", Brasil"  (remove "Loja", "Sala", "Piso", etc.)
- Salva Latitude, Longitude, Endereço Padronizado
- Salva auditoria: Geocode_Status, Geocode_Tentativa, Geocode_Consulta_Usada
- Usa cache local (geocode_cache_google.json) para economizar requisições/custo
- Gera base_data_lojas_geocoded.xlsx

Dependências:
pip install pandas requests openpyxl
"""

import os
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# ==========================
# CONFIG
# ==========================
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") 

INPUT_FILE = "base_data_lojas.xlsx"
OUTPUT_FILE = "base_data_lojas_geocoded.xlsx"

ENDERECO_COL = "Endereço"

LAT_COL = "Latitude"
LON_COL = "Longitude"
PADRAO_COL = "Endereço Padronizado"

STATUS_COL = "Geocode_Status"
TRY_COL = "Geocode_Tentativa"
QUERY_COL = "Geocode_Consulta_Usada"

CACHE_FILE = "geocode_cache_google.json"  # cache local (economiza requisições)
SLEEP_SECONDS = 0.12  # aumente (ex: 0.3) se aparecer OVER_QUERY_LIMIT


# ==========================
# CACHE HELPERS
# ==========================
def load_cache(file_path: str) -> dict:
    p = Path(file_path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(file_path: str, cache: dict) -> None:
    Path(file_path).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ==========================
# STRING HELPERS
# ==========================
def normalize_spaces(s: str) -> str:
    s = str(s or "").strip()
    s = s.replace("\u200b", "").replace("\ufeff", "")
    s = " ".join(s.split())
    return s


def simplify_address(address: str) -> str:
    """
    Remove tokens que frequentemente atrapalham geocoding (quando vêm no meio do endereço),
    mantendo a parte essencial.
    """
    a = normalize_spaces(address)

    # remove termos comuns (case-insensitive)
    patterns = [
        r"\bLoja\s*[-:]?\s*[A-Za-z0-9]+\b",
        r"\bSala\s*[-:]?\s*[A-Za-z0-9]+\b",
        r"\bPiso\s*[-:]?\s*[A-Za-z0-9]+\b",
        r"\bQuadra\s*[-:]?\s*[A-Za-z0-9]+\b",
        r"\bLote\s*[-:]?\s*[A-Za-z0-9]+\b",
        r"\bBloco\s*[-:]?\s*[A-Za-z0-9]+\b",
        r"\bEdif(ício)?\s*[-:]?\s*[\wÀ-ÿ]+\b",
        r"\bEstacionamento\s*[-:]?\s*[\wÀ-ÿ]+\b",
        r"\bKM\s*[-:]?\s*[A-Za-z0-9\.]+\b",
        r"\bkm\s*[-:]?\s*[A-Za-z0-9\.]+\b",
    ]
    for ptn in patterns:
        a = re.sub(ptn, "", a, flags=re.IGNORECASE)

    # limpa pontuação duplicada
    a = re.sub(r"\s*,\s*,", ", ", a)
    a = re.sub(r"\s{2,}", " ", a).strip(" ,;-")
    return a


# ==========================
# GOOGLE GEOCODING
# ==========================
def geocode_google(query: str, session: requests.Session) -> dict:
    """
    Retorna dict:
      {
        "status": "...",
        "lat": float|None,
        "lon": float|None,
        "formatted_address": str|None
      }
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": query,
        "key": API_KEY,
        "region": "br"
    }

    try:
        resp = session.get(url, params=params, timeout=30)
        data = resp.json()

        status = data.get("status", "UNKNOWN")

        if status == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            formatted = data["results"][0].get("formatted_address")
            return {
                "status": "OK",
                "lat": float(loc["lat"]),
                "lon": float(loc["lng"]),
                "formatted_address": formatted
            }

        return {"status": status, "lat": None, "lon": None, "formatted_address": None}

    except Exception as e:
        return {"status": f"ERROR_{type(e).__name__}", "lat": None, "lon": None, "formatted_address": None}


def geocode_with_3_attempts(original_address: str, session: requests.Session, cache: dict) -> dict:
    """
    Tenta 3 versões:
      T1: original
      T2: original + ", Brasil"
      T3: simplify(original) + ", Brasil"

    Cache é aplicado por 'query' (string enviada ao Google).
    """
    orig = normalize_spaces(original_address)
    t1 = orig
    t2 = f"{orig}, Brasil"
    t3 = f"{simplify_address(orig)}, Brasil"

    attempts = [("T1", t1), ("T2", t2), ("T3", t3)]
    last_status = None

    for tag, q in attempts:
        query = normalize_spaces(q)
        if not query:
            last_status = "EMPTY_QUERY"
            continue

        # cache
        if query in cache:
            res = cache[query]
        else:
            res = geocode_google(query, session)
            cache[query] = res

        last_status = res.get("status")

        if res.get("status") == "OK" and res.get("lat") is not None and res.get("lon") is not None:
            res = dict(res)  # evita referência direta do cache
            res["attempt"] = tag
            res["query_used"] = query
            return res

        time.sleep(SLEEP_SECONDS)

    return {
        "status": last_status or "FAILED_ALL",
        "lat": None,
        "lon": None,
        "formatted_address": None,
        "attempt": "NONE",
        "query_used": None
    }


# ==========================
# MAIN
# ==========================
def main():
    if API_KEY == "SUA_API_KEY_AQUI" or not API_KEY.strip():
        raise ValueError("Você precisa preencher a variável API_KEY com sua chave do Google.")

    df = pd.read_excel(INPUT_FILE)

    if ENDERECO_COL not in df.columns:
        raise ValueError(f"Coluna '{ENDERECO_COL}' não encontrada. Colunas disponíveis: {list(df.columns)}")

    # garante colunas de saída
    for c in [LAT_COL, LON_COL, PADRAO_COL, STATUS_COL, TRY_COL, QUERY_COL]:
        if c not in df.columns:
            df[c] = None

    cache = load_cache(CACHE_FILE)
    session = requests.Session()

    total = len(df)
    for idx, endereco in enumerate(df[ENDERECO_COL].tolist()):
        row_num = idx + 1
        addr = normalize_spaces(endereco)

        print(f"[{row_num}/{total}] Buscando: {addr}")

        if not addr:
            df.at[idx, STATUS_COL] = "EMPTY_ADDRESS"
            df.at[idx, TRY_COL] = "NONE"
            df.at[idx, QUERY_COL] = None
            continue

        res = geocode_with_3_attempts(addr, session, cache)

        df.at[idx, LAT_COL] = res.get("lat")
        df.at[idx, LON_COL] = res.get("lon")
        df.at[idx, PADRAO_COL] = res.get("formatted_address")
        df.at[idx, STATUS_COL] = res.get("status")
        df.at[idx, TRY_COL] = res.get("attempt")
        df.at[idx, QUERY_COL] = res.get("query_used")

        # salva cache incrementalmente para não perder progresso
        if row_num % 25 == 0:
            save_cache(CACHE_FILE, cache)

    save_cache(CACHE_FILE, cache)
    df.to_excel(OUTPUT_FILE, index=False)

    print("\n✅ Concluído!")
    print(f"Arquivo salvo: {OUTPUT_FILE}")
    print(f"Cache salvo: {CACHE_FILE}")


if __name__ == "__main__":
    main()