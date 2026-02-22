import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET

BASE_URL = "https://www.arezzo.com.br/arezzocoocc/v2/arezzo/stores"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    # Aceita XML também (porque o “modo lista” costuma voltar XML)
    "Accept": "application/xml, text/xml, application/json, text/plain, */*",
    "Referer": "https://www.arezzo.com.br/store-finder",
})

def safe_text(node, default=None):
    if node is None:
        return default
    txt = (node.text or "").strip()
    return txt if txt != "" else default

def parse_xml_payload(xml_text: str) -> dict:
    """
    Converte o XML do endpoint para um dict parecido com o seu JSON:
    {
      "pagination": {"totalPages": int, "totalResults": int, ...},
      "stores": [ { ... }, ...]
    }
    """
    root = ET.fromstring(xml_text)

    # pagination
    pag = root.find("pagination")
    pagination = {
        "currentPage": int(safe_text(pag.find("currentPage"), "0")),
        "pageSize": int(safe_text(pag.find("pageSize"), "20")),
        "sort": safe_text(pag.find("sort")),
        "totalPages": int(safe_text(pag.find("totalPages"), "1")),
        "totalResults": int(safe_text(pag.find("totalResults"), "0")),
    }

    stores = []
    for s in root.findall("stores"):
        # address
        addr = s.find("address")
        region = addr.find("region") if addr is not None else None
        country = addr.find("country") if addr is not None else None

        # geo
        geo = s.find("geoPoint")

        store_obj = {
            # no XML, costuma vir <name> e <displayName>
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
                "latitude": float(safe_text(geo.find("latitude"), "0")) if geo is not None else None,
                "longitude": float(safe_text(geo.find("longitude"), "0")) if geo is not None else None,
            }
        }
        stores.append(store_obj)

    return {"pagination": pagination, "stores": stores}

def fetch_page(page: int, page_size: int = 20) -> dict:
    """
    Modo LISTA (todas as lojas), paginado por nome.
    Repare que NÃO usamos latitude/longitude (ou pode mandar, mas não precisa).
    """
    params = {
        "currentPage": page,
        "pageSize": page_size,
        "sort": "name",
    }
    r = SESSION.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    ct = (r.headers.get("Content-Type") or "").lower()
    body = r.text.strip()

    # tenta JSON se for json (ou se começar com '{')
    if "json" in ct or body.startswith("{"):
        return r.json()

    # senão, trata como XML (seu caso do totalResults=654)
    return parse_xml_payload(body)

def safe_get(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def normalize_store(s: dict) -> dict:
    addr = s.get("address", {}) or {}
    region = addr.get("region", {}) or {}
    country = addr.get("country", {}) or {}
    geop = s.get("geoPoint", {}) or {}

    # melhor id: address.id (no XML ele existe e é bem estável)
    stable_id = addr.get("id") or s.get("id") or s.get("name") or s.get("displayName")

    return {
        "id": stable_id,
        "nome": s.get("displayName"),
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

def main():
    first = fetch_page(page=0, page_size=20)

    total_pages = safe_get(first, ["pagination", "totalPages"], 1)
    total_results = safe_get(first, ["pagination", "totalResults"], None)

    all_rows = []
    seen = set()

    def ingest(payload: dict):
        for st in safe_get(payload, ["stores"], []) or []:
            row = normalize_store(st)
            if not row["id"]:
                continue
            if row["id"] not in seen:
                seen.add(row["id"])
                all_rows.append(row)

    ingest(first)

    for page in range(1, int(total_pages)):
        time.sleep(0.35)
        data = fetch_page(page=page, page_size=20)
        ingest(data)

    df = pd.DataFrame(all_rows)

    df.to_csv("arezzo_lojas_654.csv", index=False, encoding="utf-8-sig")
    df.to_excel("arezzo_lojas_654.xlsx", index=False)

    print("Total páginas:", total_pages)
    print("Total results (API):", total_results)
    print("Total lojas coletadas (deduplicadas):", len(df))
    print("Arquivos gerados: arezzo_lojas_654.csv / arezzo_lojas_654.xlsx")

if __name__ == "__main__":
    main()
