import requests
import pandas as pd
from pathlib import Path
import json

# CONFIGURAÇÕES
ARQUIVO_SAIDA = "lojas_hering_completo.xlsx"


def tentar_todas_lojas_metodo1():
    """
    Tenta buscar todas as lojas sem filtro de cidade
    """
    url = "https://www.hering.com.br/api/graphql"

    params = {
        "operationName": "storeLocatorNeighborhoodQuery",
        "operationHash": "fa142a0c74d7bf541f7f7d9c094f61f3fa0255b0",
        "variables": '{}'  # Sem filtro
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.hering.com.br/store/hering/pt/lojas"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def tentar_todas_lojas_metodo2():
    """
    Tenta buscar todas as lojas com cidade vazia ou null
    """
    url = "https://www.hering.com.br/api/graphql"

    variacoes = [
        '{"cidade":""}',
        '{"cidade":null}',
        '{}',
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.hering.com.br/store/hering/pt/lojas"
    }

    for variables in variacoes:
        params = {
            "operationName": "storeLocatorNeighborhoodQuery",
            "operationHash": "fa142a0c74d7bf541f7f7d9c094f61f3fa0255b0",
            "variables": variables
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data
        except:
            continue

    return None


def tentar_endpoint_alternativo():
    """
    Tenta buscar um endpoint alternativo que pode retornar todas as lojas
    """
    endpoints = [
        "https://www.hering.com.br/api/dataentities/LJ/search?_fields=_all",
        "https://www.hering.com.br/api/catalog_system/pub/stores/list",
        "https://www.hering.com.br/api/io/_v/private/store/list",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            continue

    return None


def buscar_graphql_completo():
    """
    Tenta fazer uma query GraphQL mais completa
    """
    url = "https://www.hering.com.br/api/graphql"

    # Query GraphQL completa pedindo todos os dados
    queries = [
        {
            "operationName": "getAllStores",
            "variables": {},
            "query": "query getAllStores { stores { id name address city state } }"
        },
        {
            "operationName": "storeLocatorNeighborhoodQuery",
            "variables": {},
        }
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://www.hering.com.br/store/hering/pt/lojas"
    }

    for query_data in queries:
        try:
            # Tenta POST
            response = requests.post(url, json=query_data, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data
        except:
            pass

    return None


def processar_resposta(data):
    """
    Processa a resposta da API e extrai as lojas
    """
    lojas = []

    if not data:
        return lojas

    # Tenta diferentes estruturas de resposta
    if "data" in data:
        if "getStoreLocatorNeighborhood" in data["data"]:
            neighborhoods = data["data"]["getStoreLocatorNeighborhood"].get("neighborhoods", [])
            for neighborhood in neighborhoods:
                lojas.append({
                    "nome": neighborhood.get("nome", ""),
                    "cidade": neighborhood.get("cidade", ""),
                    "bairro": neighborhood.get("bairro", ""),
                    "rua": neighborhood.get("rua", ""),
                    "cep": neighborhood.get("cep", ""),
                    "telefones": neighborhood.get("telefones", ""),
                    "whatsapp": neighborhood.get("whatsapp", ""),
                    "idSeller": neighborhood.get("idSeller", "")
                })
        elif "stores" in data["data"]:
            for store in data["data"]["stores"]:
                lojas.append(store)

    elif isinstance(data, list):
        lojas = data

    return lojas


def main():
    print("=" * 60)
    print("Tentando extrair TODAS as lojas Hering de uma só vez...")
    print("=" * 60)

    # Tenta diferentes métodos
    print("\n[1] Tentando método sem filtro de cidade...")
    data = tentar_todas_lojas_metodo1()
    lojas = processar_resposta(data)

    if not lojas:
        print("   ✗ Não retornou lojas")
        print("\n[2] Tentando com variações de parâmetros vazios...")
        data = tentar_todas_lojas_metodo2()
        lojas = processar_resposta(data)

    if not lojas:
        print("   ✗ Não retornou lojas")
        print("\n[3] Tentando endpoints alternativos...")
        data = tentar_endpoint_alternativo()
        lojas = processar_resposta(data)

    if not lojas:
        print("   ✗ Não retornou lojas")
        print("\n[4] Tentando query GraphQL completa...")
        data = buscar_graphql_completo()
        lojas = processar_resposta(data)

    if lojas:
        # Salva em Excel
        df = pd.DataFrame(lojas)
        df_unique = df.drop_duplicates(keep='first')

        caminho_saida = Path(ARQUIVO_SAIDA)
        df_unique.to_excel(caminho_saida, index=False, engine='openpyxl')

        print(f"\n{'=' * 60}")
        print(f"✓ SUCESSO!")
        print(f"✓ Total de lojas encontradas: {len(df_unique)}")
        print(f"✓ Arquivo gerado: {caminho_saida.resolve()}")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print("⚠ ATENÇÃO: Não foi possível extrair todas as lojas de uma vez.")
        print("\nA API da Hering provavelmente requer o filtro por cidade.")
        print("Você tem duas opções:")
        print("1. Usar o script anterior que consulta cidade por cidade")
        print("2. Investigar manualmente a API no DevTools do navegador")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()