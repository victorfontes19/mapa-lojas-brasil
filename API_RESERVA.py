import json
import requests
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

URL = (
    "https://www.usereserva.com/_v/private/graphql/v1"
    "?workspace=master&maxAge=long&appsEtag=remove&domain=store&locale=pt-BR"
)

COOKIE = r"""VtexWorkspace=master%3A-; _fbp=fb.1.1770595014460.836162932467584483.AQYCAQIB; channel=other; gbuuid=f087bb89-c177-4c16-bc08-fe4f16e89b7f; vtex_segment=eyJjYW1wYWlnbnMiOm51bGwsImNoYW5uZWwiOiIxIiwicHJpY2VUYWJsZXMiOm51bGwsInJlZ2lvbklkIjpudWxsLCJ1dG1fY2FtcGFpZ24iOm51bGwsInV0bV9zb3VyY2UiOm51bGwsInV0bWlfY2FtcGFpZ24iOm51bGwsImN1cnJlbmN5Q29kZSI6IkJSTCIsImN1cnJlbmN5U3ltYm9sIjoiUiQiLCJjb3VudHJ5Q29kZSI6IkJSQSIsImN1bHR1cmVJbmZvIjoicHQtQlIiLCJjaGFubmVsUHJpdmFjeSI6InB1YmxpYyJ9; vtex-search-session=31f922d5116e47ff98ffcdaa38d11ee8; vtex-search-anonymous=50ee5feb719f44138c04f3d22c5842a6; checkout.vtex.com=__ofid=83cc08ab9c4349dea9093161ad63148a; rskxRunCookie=0; rCookie=xmrrb79uo2iecv4vl2exvbmleek2aj; VtexRCSessionIdv7=0efbbff0-7ea4-493b-aae2-9d78187a0b64; VtexRCMacIdv7=4143e52b-9f77-4b1d-ac16-ec9aa1f84693; __kdtv=t%3D1770595021366%3Bi%3D49dd8105ed85f145be7eee5a59beb2f2f90af1bd; _kdt=%7B%22t%22%3A1770595021366%2C%22i%22%3A%2249dd8105ed85f145be7eee5a59beb2f2f90af1bd%22%7D; _hjSession_123238=eyJpZCI6IjdiZjNiNDA2LWNjNmMtNGU4YS1iODFmLTU0MDdkYjgyMDc1YyIsImMiOjE3NzA1OTUwMjE1NTQsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MH0=; moe_uuid=8add268a-d2e5-4558-a1c8-f94cd8ee15f9; originalReferrer=https%3A%2F%2Fwww.bing.com%2F; AwinChannelCookie=other; _gcl_au=1.1.1884121142.1770595022; __gtm_referrer=https%3A%2F%2Fwww.bing.com%2F; _rtbhouse_source_=organic; custom_utm_source=undefined; blueID=5a748547-2bb5-45e1-b451-daca5963ab09; _ga=GA1.1.1154153927.1770595022; _tt_enable_cookie=1; _ttp=01KGZTZXHHKFRQK5BD1M9VY8W8_.tt.1; user_unic_ac_id=68d0c7a6-4222-8855-a5cf-e11dc33b9cf3; advcake_trackid=3ad02a69-e754-2dc7-f6ef-5a81805c7a7b; _pin_unauth=dWlkPU9EQTRaV1JpTXpVdE16Tm1ZeTAwTkdVd0xUazNaREl0T0RNM1pXTXlNVE5oTTJVeg; voxusmediamanager_id=17562237367050.11603742192021105gx2lh8jpgrb; voxusmediamanager_acs=true; OptanonAlertBoxClosed=2026-02-08T23:57:27.941Z; vtex_session=eyJhbGciOiJFUzI1NiIsImtpZCI6ImI2ZTQwYjA3LTc2MjEtNDUyZS05MjRkLWMxMzY0YjcwOWZiNSIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50LmlkIjpbXSwiaWQiOiJiMzVkZjFlZC1mYTI2LTQxZjItYWM4Mi1iOWNlMmE3NGE0MjIiLCJ2ZXJzaW9uIjozLCJzdWIiOiJzZXNzaW9uIiwiYWNjb3VudCI6InNlc3Npb24iLCJleHAiOjE3NzEyODYyNzQsImlhdCI6MTc3MDU5NTA3NCwianRpIjoiNmQ4Y2IxMjgtMTkwNi00NmVjLWFiNDUtYjYwMjNjNGRjOWI5IiwiaXNzIjoic2Vzc2lvbi9kYXRhLXNpZ25lciJ9.sk1VMb4HE_h2dJlz6GXiixcaZN389_nJ3zBCthm6OLAFgHg008iId4qGnBe1Bj0CTrn0vjUty7f0ogCXCKxjxg; vtex_binding_address=lojausereserva.myvtex.com/; _hjSessionUser_123238=eyJpZCI6ImUxY2U1NTQ3LWEyMjItNTI5ZC04NWMyLWJhZDViYjIwMGE1YyIsImNyZWF0ZWQiOjE3NzA1OTUwMjE1NTMsImV4aXN0aW5nIjp0cnVlfQ==; sp-variant=null-null; cto_bundle=umEW-F9acCUyQmxBeWFPa20xV0k3JTJCazdjd2JhNndWd0lOYUxsSUdPTENMekppNiUyQlJrSkpXREFsQTRBRG1CWGlwQWpnS2hSZ0tROXlaVUVRczdVMjdSM2hxNkJQcXhZeiUyQlo5OUo0Zlkzd002JTJGN01MMFM3JTJCMEdkTHpaVTFZTWdQTW9PTWhuZGQ3N1VSNXBIdDZENmg1bHNQbnpHUnclM0QlM0Q; lastRskxRun=1770595696094; OptanonConsent=isGpcEnabled=0&datestamp=Sun+Feb+08+2026+21%3A08%3A17+GMT-0300+(Hor%C3%A1rio+Padr%C3%A3o+de+Bras%C3%ADlia)&version=202510.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=038c1796-f654-4c91-9548-a9155334e1b4&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A0%2CC0003%3A0%2CC0002%3A0%2CS0004%3A0&intType=3&geolocation=BR%3BSP&AwaitingReconsent=false; CheckoutOrderFormOwnership=; dcuc=true; _uetsid=dcb37120054911f1bc1f6bca1b35584a; _uetvid=dcb398d0054911f18c34cb5dd8109438; _ga_BBG5S14GMY=GS2.1.s1770595021$o1$g1$t1770595702$j49$l0$h0; _ga_X08W8VEGLB=GS2.1.s1770595022$o1$g1$t1770595702$j49$l0$h0; _ga_LX0VRD17T0=GS2.1.s1770595022$o1$g1$t1770595702$j49$l0$h0; _ga_N09SCX2BYC=GS2.1.s1770595022$o1$g1$t1770595703$j48$l0$h1059476839; __rtbh.uid=%7B%22eventType%22%3A%22uid%22%2C%22id%22%3A%22unknown%22%2C%22expiryDate%22%3A%222027-02-09T00%3A08%3A23.062Z%22%7D; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22b0EtoryXw9smGR8mL2lf%22%2C%22expiryDate%22%3A%222027-02-09T00%3A08%3A23.062Z%22%7D; ttcsid=1770595022394::rN3K4XpypZtQ5y1vWRaT.1.1770595705021.0; ttcsid_CENFUCRC77U6CQIV38M0=1770595022393::es9SaUcbk6LDwBb2l8pk.1.1770595705021.1""".strip()

PAYLOAD = {
    "operationName": "getStoresLocation",
    "variables": {},
    "extensions": {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "18a726a51784210f56bdabc59b89384725a7666247557101522e91625ad50d61",
            "sender": "lojausereserva.lojausereserva-theme@7.x",
            "provider": "vtex.store-locator@0.x",
        }
    }
}

STORE_KEYS_HINT = {"address", "name", "friendlyName", "storeId", "id", "geoCoordinates", "isActive", "storeType"}

def looks_like_store(d: Dict[str, Any]) -> bool:
    if not isinstance(d, dict):
        return False
    hits = 0
    for k in STORE_KEYS_HINT:
        if k in d:
            hits += 1
    # address costuma ser dict com city/state/postalCode
    if "address" in d and isinstance(d.get("address"), dict):
        hits += 2
    return hits >= 2  # tolerante

def find_store_list(obj: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Procura recursivamente por uma lista que pareça ser lista de lojas.
    """
    if isinstance(obj, list):
        # lista de dicts
        dicts = [x for x in obj if isinstance(x, dict)]
        if dicts:
            # se uma fração razoável parecer loja, retornamos
            score = sum(1 for x in dicts[:20] if looks_like_store(x))
            if score >= max(1, len(dicts[:20]) // 3):
                return dicts
        # senão, tenta procurar dentro de cada item
        for x in obj:
            res = find_store_list(x)
            if res:
                return res
        return None

    if isinstance(obj, dict):
        # primeira tentativa: procurar por chaves óbvias
        for key in ("stores", "items", "locations", "results", "pickupPoints", "points"):
            v = obj.get(key)
            if isinstance(v, list):
                res = find_store_list(v)
                if res:
                    return res

        # varre tudo
        for _, v in obj.items():
            res = find_store_list(v)
            if res:
                return res

    return None

def normalize_store(s: Dict[str, Any]) -> Dict[str, Any]:
    addr = s.get("address") or {}
    if not isinstance(addr, dict):
        addr = {}

    geo = addr.get("geoCoordinates") or s.get("geoCoordinates") or []
    lon = geo[0] if isinstance(geo, list) and len(geo) > 0 else None
    lat = geo[1] if isinstance(geo, list) and len(geo) > 1 else None

    return {
        "id": s.get("id") or s.get("storeId") or addr.get("addressId"),
        "nome": s.get("name") or s.get("friendlyName") or s.get("title"),
        "tipo": s.get("storeType") or s.get("type"),
        "ativo": s.get("isActive") if "isActive" in s else None,
        "logradouro": addr.get("street"),
        "numero": addr.get("number"),
        "complemento": addr.get("complement"),
        "bairro": addr.get("neighborhood"),
        "cidade": addr.get("city"),
        "estado": addr.get("state"),
        "cep": addr.get("postalCode"),
        "pais": addr.get("country"),
        "telefone": addr.get("phone"),
        "latitude": lat,
        "longitude": lon,
        "raw": json.dumps(s, ensure_ascii=False),
    }

def main():
    if not COOKIE or "COLE_AQUI" in COOKIE:
        raise SystemExit("Cole o COOKIE completo na variável COOKIE antes de rodar.")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        ),
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://www.usereserva.com",
        "Referer": "https://www.usereserva.com/",
        "Cookie": COOKIE,
    }

    r = requests.post(URL, headers=headers, json=PAYLOAD, timeout=40)

    if r.status_code != 200:
        print(f"[HTTP {r.status_code}] URL: {r.url}")
        print(r.text[:2000])
        r.raise_for_status()

    resp = r.json()

    # Sempre salva debug (ajuda MUITO)
    with open("reserva_debug_response.json", "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)

    if isinstance(resp, dict) and resp.get("errors"):
        raise RuntimeError("GraphQL errors: " + json.dumps(resp["errors"], ensure_ascii=False)[:2000])

    data = resp.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Response sem campo 'data'. Veja reserva_debug_response.json")

    stores = find_store_list(data)
    if not stores:
        # imprime chaves do topo pra ajudar
        print("Chaves no topo de data:", list(data.keys()))
        raise RuntimeError(
            "Ainda não encontrei a lista de lojas no response. "
            "O JSON completo foi salvo em 'reserva_debug_response.json'."
        )

    rows = [normalize_store(s) for s in stores if isinstance(s, dict)]
    df = pd.DataFrame(rows)

    df.to_csv("reserva_lojas.csv", index=False, encoding="utf-8-sig")
    df.to_excel("reserva_lojas.xlsx", index=False)

    print("Total de lojas encontradas:", len(df))
    print("Arquivos gerados: reserva_lojas.csv / reserva_lojas.xlsx")
    print("Debug salvo: reserva_debug_response.json")

if __name__ == "__main__":
    main()
