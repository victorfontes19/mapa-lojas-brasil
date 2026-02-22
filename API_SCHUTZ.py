import time
import random
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, List, Tuple

BASE_URL = "https://www.schutz.com.br/arezzocoocc/v2/schutz/stores"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "application/xml, text/xml, application/json, text/plain, */*",
    "Referer": "https://www.schutz.com.br/store-finder",
})

# =========================
# Helpers
# =========================
def safe_text(node: Optional[ET.Element], default: Optional[str] = None) -> Optional[str]:
    if node is None:
        return default
    txt = (node.text or "").strip()
    return txt if txt != "" else default

def to_int(x: Any, default: int = 0) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        return default

def to_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default

def safe_get(d: Any, path: List[str], default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def is_zip_error(body: str) -> bool:
    b = (body or "").lower()
    return "zipcode must have" in b or "zip code must have" in b or "zipcode must have [7]" in b

# =========================
# Parse XML -> dict
# =========================
def parse_xml_payload(xml_text: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_text)

    pag = root.find("pagination")
    pagination = {
        "currentPage": to_int(safe_text(pag.find("currentPage")) if pag is not None else None, 0),
        "pageSize": to_int(safe_text(pag.find("pageSize")) if pag is not None else None, 20),
        "sort": safe_text(pag.find("sort")) if pag is not None else None,
        "totalPages": to_int(safe_text(pag.find("totalPages")) if pag is not None else None, 1),
        "totalResults": to_int(safe_text(pag.find("totalResults")) if pag is not None else None, 0),
    }

    stores: List[Dict[str, Any]] = []

    store_nodes = root.findall(".//store")
    if not store_nodes:
        store_nodes = root.findall("stores")

    for s in store_nodes:
        addr = s.find("address")
        region = addr.find("region") if addr is not None else None
        country = addr.find("country") if addr is not None else None
        geo = s.find("geoPoint")

        store_obj = {
            "name": safe_text(s.find("name")),
            "displayName": safe_text(s.find("displayName")),
            "formattedDistance": safe_text(s.find("formattedDistance")),
            "franchise": (safe_text(s.find("franchise")) == "true") if s.find("franchise") is not None else None,
            "exchangeOmniEnable": (safe_text(s.find("exchangeOmniEnable")) == "true") if s.find("exchangeOmniEnable") is not None else None,
            "address": {
                "id": safe_text(addr.find("id")) if addr is not None else None,
                "formattedAddress": safe_text(addr.find("formattedAddress")) if addr is not None else None,
                "streetName": safe_text(addr.find("streetName")) if addr is not None else None,
                "streetNumber": safe_text(addr.find("streetNumber")) if addr is not None else None,
                "complement": safe_text(addr.find("complement")) if addr is not None else None,
                "district": safe_text(addr.find("district")) if addr is not None else None,
                "town": safe_text(addr.find("town")) if addr is not None else None,
                "postalCode": safe_text(addr.find("postalCode")) if addr is not None else None,
                "phone": safe_text(addr.find("phone")) if addr is not None else None,
                "country": {"isocode": safe_text(country.find("isocode")) if country is not None else None},
                "region": {
                    "isocode": safe_text(region.find("isocode")) if region is not None else None,
                    "name": safe_text(region.find("name")) if region is not None else None,
                }
            },
            "geoPoint": {
                "latitude": to_float(safe_text(geo.find("latitude")) if geo is not None else None),
                "longitude": to_float(safe_text(geo.find("longitude")) if geo is not None else None),
            }
        }
        stores.append(store_obj)

    return {"pagination": pagination, "stores": stores}

def decode_payload(r: requests.Response) -> Dict[str, Any]:
    ct = (r.headers.get("Content-Type") or "").lower()
    body = (r.text or "").strip()
    if "json" in ct or body.startswith("{"):
        return r.json()
    return parse_xml_payload(body)

# =========================
# HTTP GET robusto
# =========================
def robust_get(url: str, params: Dict[str, Any], timeout: int = 30, max_retries: int = 6) -> requests.Response:
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            r = SESSION.get(url, params=params, timeout=timeout)

            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(12, 0.6 * (2 ** (attempt - 1))) + random.uniform(0, 0.35)
                print(f"[retry] HTTP {r.status_code} attempt={attempt} wait={wait:.2f}s")
                time.sleep(wait)
                continue

            return r
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            wait = min(12, 0.6 * (2 ** (attempt - 1))) + random.uniform(0, 0.35)
            print(f"[retry] {type(e).__name__} attempt={attempt} wait={wait:.2f}s")
            time.sleep(wait)

    if last_exc:
        raise last_exc
    raise RuntimeError("robust_get falhou (inesperado).")

# =========================
# Params base
# =========================
def base_params(page: Any, page_size: int) -> Dict[str, Any]:
    return {
        "currentPage": page,
        "pageSize": page_size,
        "sort": "name",
        "fields": "FULL",
        "lang": "pt",
        "curr": "BRL",
    }

# =========================
# Fetch com workaround page=1
# =========================
def fetch_page(page: int, page_size: int) -> Dict[str, Any]:
    """
    Estratégia:
    1) tenta normal (currentPage=int)
    2) se der 400 zipCode:
       - (A) currentPage como string com 7 chars: "0000001"
       - (B) usar 'page' no lugar de currentPage
       - (C) usar offset/startIndex se suportar
    """
    # tentativas (cada item: params, label)
    attempts: List[Tuple[Dict[str, Any], str]] = []

    # normal
    attempts.append((base_params(page, page_size), "normal currentPage"))

    if page == 1:
        # Workaround 1: currentPage com 7 caracteres (passa validação “7 chars” se o backend estiver lendo o param errado)
        attempts.append((base_params("0000001", page_size), "page==1 currentPage='0000001'"))

        # Workaround 2: usar 'page' ao invés de currentPage
        p2 = base_params(page, page_size)
        p2.pop("currentPage", None)
        p2["page"] = page
        attempts.append((p2, "page==1 usando param 'page'"))

        # Workaround 3: offset/startIndex (alguns backends aceitam)
        offset = page * page_size  # 20
        p3 = base_params(0, page_size)  # currentPage irrelevante, tenta offset
        p3["startIndex"] = offset
        attempts.append((p3, "page==1 usando startIndex=20"))

        p4 = base_params(0, page_size)
        p4["offset"] = offset
        attempts.append((p4, "page==1 usando offset=20"))

    last = None
    for params, label in attempts:
        r = robust_get(BASE_URL, params=params, timeout=30)
        last = r

        if r.status_code == 200:
            print(f"[ok] page={page} via: {label}")
            return decode_payload(r)

        if r.status_code == 400 and is_zip_error(r.text):
            # log curto e tenta próxima
            print(f"[zip-error] page={page} via: {label} -> tentando outra variação")
            continue

        # outro erro 4xx/5xx: log e tenta próxima (ou explode se for a última)
        print("\n==============================")
        print(f"[HTTP {r.status_code}] page={page} via: {label}")
        print("URL:", r.url)
        print("Content-Type:", r.headers.get("Content-Type"))
        print("Body (primeiros 1200 chars):")
        print((r.text or "")[:1200])
        print("==============================\n")
        # tenta próxima (se tiver)
        continue

    # se caiu aqui, nenhuma tentativa funcionou
    if last is not None:
        print("\n==============================")
        print(f"[FALHA] page={page}: nenhuma variação funcionou")
        print("Última URL:", last.url)
        print("Último body (primeiros 1200 chars):")
        print((last.text or "")[:1200])
        print("==============================\n")
        last.raise_for_status()

    raise RuntimeError("fetch_page: falha sem resposta (inesperado).")

# =========================
# Normalize
# =========================
def normalize_store(s: Dict[str, Any]) -> Dict[str, Any]:
    addr = s.get("address", {}) or {}
    region = addr.get("region", {}) or {}
    country = addr.get("country", {}) or {}
    geop = s.get("geoPoint", {}) or {}

    stable_id = addr.get("id") or s.get("id") or s.get("name") or s.get("displayName")

    return {
        "id": stable_id,
        "nome": s.get("displayName") or s.get("name"),
        "endereco_formatado": addr.get("formattedAddress"),
        "logradouro": addr.get("streetName"),
        "numero": addr.get("streetNumber"),
        "complemento": addr.get("complement"),
        "bairro": addr.get("district"),
        "cidade": addr.get("town"),
        "estado": region.get("isocode") or region.get("name"),
        "cep": addr.get("postalCode"),
        "pais": country.get("isocode"),
        "telefone": addr.get("phone") or s.get("phoneNumber"),
        "lat": geop.get("latitude"),
        "lon": geop.get("longitude"),
        "distancia_formatada": s.get("formattedDistance"),
        "franquia": s.get("franchise"),
        "omni_troca": s.get("exchangeOmniEnable"),
    }

# =========================
# Main
# =========================
def main():
    page_size = 20  # o único estável pelo que vimos

    print("Buscando primeira página...")
    first = fetch_page(page=0, page_size=page_size)

    total_pages = int(safe_get(first, ["pagination", "totalPages"], 1))
    total_results = safe_get(first, ["pagination", "totalResults"], None)

    print(f"Total páginas (API): {total_pages}")
    print(f"Total results (API): {total_results}")

    all_rows: List[Dict[str, Any]] = []
    seen = set()

    def ingest(payload: Dict[str, Any]):
        for st in (safe_get(payload, ["stores"], []) or []):
            row = normalize_store(st)
            if not row.get("id"):
                continue
            if row["id"] not in seen:
                seen.add(row["id"])
                all_rows.append(row)

    ingest(first)

    for page in range(1, total_pages):
        time.sleep(0.35)
        print(f"Buscando page={page}/{total_pages - 1} ...")
        data = fetch_page(page=page, page_size=page_size)
        ingest(data)

    df = pd.DataFrame(all_rows)

    csv_name = "schutz_lojas.csv"
    xlsx_name = "schutz_lojas.xlsx"

    df.to_csv(csv_name, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_name, index=False)

    print("\n==============================")
    print("FINALIZADO ✅")
    print("Total results (API):", total_results)
    print("Total lojas coletadas (deduplicadas):", len(df))
    print(f"Arquivos gerados: {csv_name} / {xlsx_name}")
    print("==============================\n")


if __name__ == "__main__":
    main()
