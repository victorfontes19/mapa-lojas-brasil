import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# ========= CONFIG =========
INPUT_FILE = r"C:\Users\INFORM\OneDrive - INFORM GmbH\Documentos\PycharmProjects\API Arezzo\base_data_lojas_final_excel.xlsx"

# Se quiser fixar a aba, coloque exatamente o nome:
# SHEET_NAME = "base_data_lojas_final_UTF8"
# Se deixar None, o código vai usar a primeira aba automaticamente (sheet 0)
SHEET_NAME = None

LAT_COL = "Latitude"
LON_COL = "Longitude"

OUT_GPKG = r"C:\Users\INFORM\OneDrive - INFORM GmbH\Documentos\PycharmProjects\API Arezzo\lojas_pontos.gpkg"
LAYER_NAME = "lojas_pontos"


def main():
    # 1) Ler Excel (garantindo DataFrame, não dict)
    if SHEET_NAME is None:
        df = pd.read_excel(INPUT_FILE, sheet_name=0)  # <<< primeira aba
    else:
        df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # Se alguém rodar com sheet_name=None sem querer, ainda assim corrigimos:
    if isinstance(df, dict):
        first_sheet = next(iter(df.keys()))
        df = df[first_sheet]
        print(f"⚠️ sheet_name=None retornou dict. Usando a primeira aba: {first_sheet}")

    print("✅ Colunas encontradas:", list(df.columns))

    # 2) Converter coords para numérico
    df[LAT_COL] = pd.to_numeric(df[LAT_COL], errors="coerce")
    df[LON_COL] = pd.to_numeric(df[LON_COL], errors="coerce")

    # 3) Filtrar linhas válidas
    before = len(df)
    df = df.dropna(subset=[LAT_COL, LON_COL]).copy()
    after = len(df)
    print(f"Linhas lidas: {before} | Linhas com coordenadas válidas: {after}")

    if after == 0:
        raise ValueError("Nenhuma coordenada válida após conversão. Verifique se Latitude/Longitude estão preenchidas.")

    # 4) Criar GeoDataFrame (X=Longitude, Y=Latitude)
    geometry = [Point(xy) for xy in zip(df[LON_COL], df[LAT_COL])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # 5) Exportar para GeoPackage
    gdf.to_file(OUT_GPKG, layer=LAYER_NAME, driver="GPKG")
    print(f"✅ GeoPackage gerado: {OUT_GPKG} (layer: {LAYER_NAME})")

    print("\nNo QGIS:")
    print("Camada → Adicionar Camada → Adicionar Camada Vetorial → selecione o .gpkg")


if __name__ == "__main__":
    main()