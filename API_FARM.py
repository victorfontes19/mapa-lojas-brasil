import requests
import re
import json
import pandas as pd
from urllib.parse import urljoin

BASE_PAGE = "https://www.farmrio.com.br/nossas-lojas"
OUT_XLSX = "lojas_farm.xlsx"

session = requests.Session()

HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

HEADERS_JS = {
    "User-Agent": HEADERS_HTML["User-Agent"],
    "Accept": "*/*",
    "Accept-Language": HEADERS_HTML["Accept-Language"],
    "Referer": BASE_PAGE,
    "Connection": "keep-alive",
}

def bracket_extract_array(text: str, start_idx: int) -> str:
    """Extrai substring de array JSON começando em '[' (contando colchetes, respeitando strings)."""
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "[":
        raise ValueError("start_idx não aponta para '['")

    i = start_idx
    bracket = 0
    in_str = False
    esc = False

    while i < len(text):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                bracket += 1
            elif ch == "]":
                bracket -= 1
                if bracket == 0:
                    return text[start_idx:i+1]
        i += 1

    raise RuntimeError("Não consegui fechar o array a partir do '[' encontrado.")

def extract_store_array_from_js(js_text: str):
    """
    Procura pelo marcador típico 'storeSellerId' no JS e volta para achar o '[' do array.
    Depois faz json.loads no array extraído.
    """
    marker = '"storeSellerId"'
    pos = js_text.find(marker)
    if pos == -1:
        return None

    # tenta achar um '[' antes do marcador e extrair um array válido
    search_from = pos
    for _ in range(400):
        start = js_text.rfind("[", 0, search_from)
        if start == -1:
            break
        try:
            arr_str = bracket_extract_array(js_text, start)
            data = json.loads(arr_str)
            if isinstance(data, list) and data and isinstance(data[0], dict):
                keys = set(data[0].keys())
                if "name" in keys and ("storeSellerId" in keys or "postalCode" in keys):
                    return data
        except Exception:
            pass
        search_from = start
    return None

def main():
    # 1) baixa HTML da página
    r = session.get(BASE_PAGE, headers=HEADERS_HTML, timeout=30)
    r.raise_for_status()
    html = r.text

    # 2) extrai todos scripts
    script_srcs = re.findall(r'<script[^>]+src="([^"]+)"', html)
    script_urls = [urljoin(BASE_PAGE, s) for s in script_srcs]

    if not script_urls:
        raise RuntimeError("Não encontrei <script src=...> no HTML. Talvez a página esteja diferente/bloqueada.")

    print(f"Encontrados {len(script_urls)} scripts. Vou varrer até achar a lista de lojas...")

    stores = None
    checked = 0

    for url in script_urls:
        checked += 1
        try:
            jsr = session.get(url, headers=HEADERS_JS, timeout=60)
            if jsr.status_code >= 400:
                continue

            ctype = jsr.headers.get("Content-Type", "")
            text = jsr.text

            # filtro rápido: só tenta parsear se tiver o marcador
            if "storeSellerId" not in text:
                continue

            found = extract_store_array_from_js(text)
            if found is not None:
                stores = found
                print(f"✅ Lista encontrada no script #{checked}: {url}")
                break

        except requests.RequestException:
            continue

    if stores is None:
        raise RuntimeError(
            "Não encontrei a lista de lojas em nenhum script carregado pela página. "
            "Isso pode acontecer se a FARM mudou o bundle ou se os dados vêm via request separado."
        )

    # 3) normaliza e salva excel
    df = pd.json_normalize(stores)

    # 'horario' como string para não quebrar o excel
    if "horario" in df.columns:
        df["horario"] = df["horario"].apply(
            lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x
        )

    df.to_excel(OUT_XLSX, index=False)
    print(f"OK: gerado {OUT_XLSX} com {len(df)} lojas.")
    print("Colunas:", list(df.columns))

if __name__ == "__main__":
    main()
