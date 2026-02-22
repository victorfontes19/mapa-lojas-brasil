import json
import time
import requests

API_URL = "https://www.animale.com.br/api/graphql"
OP_NAME = "getStoreCity"
OP_HASH = "1b02ef08a021ef09dbc2a5da89c491eb9b7d5f46"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.animale.com.br",
    "Referer": "https://www.animale.com.br/nossas-lojas",
    "Connection": "close",
}

def show_fail(tag, r):
    ct = r.headers.get("Content-Type", "")
    print(f"[{tag}] HTTP {r.status_code} CT={ct}")
    txt = (r.text or "").strip()
    if txt:
        print("Body[0:400]:", txt[:400])
    else:
        print("Body vazio.")

def try_format_1_get(vars_):
    params = {
        "operationName": OP_NAME,
        "operationHash": OP_HASH,
        "variables": json.dumps(vars_, ensure_ascii=False),
    }
    r = requests.get(API_URL, headers=HEADERS, params=params, timeout=(10, 25))
    if r.status_code != 200:
        show_fail("GET fmt1", r)
        r.raise_for_status()
    return r.json()

def try_format_2_get_extensions(vars_):
    # extensions[persistedQuery] no querystring (muito comum em gateways)
    params = {
        "operationName": OP_NAME,
        "variables": json.dumps(vars_, ensure_ascii=False),
        "extensions[persistedQuery][version]": "1",
        "extensions[persistedQuery][sha256Hash]": OP_HASH,
    }
    r = requests.get(API_URL, headers=HEADERS, params=params, timeout=(10, 25))
    if r.status_code != 200:
        show_fail("GET fmt2", r)
        r.raise_for_status()
    return r.json()

def try_format_3_post_hash_in_url(vars_):
    # hash na URL, body só com operationName/variables
    params = {"operationName": OP_NAME, "operationHash": OP_HASH}
    body = {"operationName": OP_NAME, "variables": vars_}
    r = requests.post(API_URL, headers={**HEADERS, "Content-Type": "application/json"},
                      params=params, json=body, timeout=(10, 45))
    if r.status_code != 200:
        show_fail("POST fmt3", r)
        r.raise_for_status()
    return r.json()

def main():
    test = {"uf": "SP", "city": "Ribeirão Preto"}  # seu exemplo do print

    for fn in (try_format_1_get, try_format_2_get_extensions, try_format_3_post_hash_in_url):
        print("\nTentando:", fn.__name__)
        try:
            data = fn(test)
            print("✅ Funcionou! Top-level keys:", list(data.keys()))
            # salva retorno para você ver
            with open("animale_ok_response.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("Salvei: animale_ok_response.json")
            return
        except Exception as e:
            print("Falhou:", repr(e))
            time.sleep(0.3)

    print("\n❌ Nenhum formato funcionou.")
    print("Se no browser funciona, então falta 1 header/cookie específico (WAF) OU o variables tem outro formato.")
    print("Próximo passo: copiar do DevTools a Request URL completa (a que dá 200) e eu monto 1:1.")

if __name__ == "__main__":
    main()
