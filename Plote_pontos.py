import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import folium
from folium import plugins
import branca.colormap as cm

# ============================================================
# CONFIG (AJUSTE OS CAMINHOS)
# ============================================================
UF_SHP = r"C:\Users\INFORM\Downloads\BR_UF_2024\BR_UF_2024.shp"
LOJAS_XLSX = r"C:\Users\INFORM\OneDrive - INFORM GmbH\Documentos\PycharmProjects\API Arezzo\base_data_lojas_final_excel.xlsx"
SHEET_NAME = "base_data_lojas_final_UTF8"
COL_GRUPO = "Grupo"
COL_MARCA = "Marca"
COL_LAT = "Latitude"
COL_LON = "Longitude"
OUT_PNG = r"C:\Users\INFORM\OneDrive - INFORM GmbH\Documentos\PycharmProjects\API Arezzo\mapa_lojas.png"
OUT_HTML = r"C:\Users\INFORM\OneDrive - INFORM GmbH\Documentos\PycharmProjects\API Arezzo\mapa_lojas_interativo.html"
DPI = 300

# Estilo do mapa estático
OCEAN_COLOR = "#9fb8bd"
BR_FILL = "#efefef"
BR_EDGE = "#ffffff"
POINT_EDGE = "#ffffff"

# ============================================================
# CORES DOS GRUPOS  ← altere aqui para mudar as cores!
# ============================================================
COR_AZZAS          = "#e41a1c"   # vermelho
COR_RENNER         = "#4daf4a"   # verde
COR_SANTA_LOLLA    = "#984ea3"   # roxo
COR_LUIZA_BARCELOS = "#377eb8"   # azul
# Cor padrão usada para qualquer grupo não listado acima:
COR_PADRAO         = "#ff7f00"   # laranja

# Tamanhos ajustados para destacar mais as diferenças
MIN_SIZE = 25
MAX_SIZE = 350


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def ensure_exists(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")


def pick_excel_sheet(xlsx_path: str, desired: str):
    xl = pd.ExcelFile(xlsx_path)
    if desired in xl.sheet_names:
        return desired
    return xl.sheet_names[0]


def normalize_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def size_from_counts(counts: pd.Series, min_size=MIN_SIZE, max_size=MAX_SIZE) -> pd.Series:
    """
    Escala QUADRÁTICA para enfatizar diferenças (grupos grandes ficam MUITO maiores)
    """
    import numpy as np
    c = counts.clip(lower=1).astype(float)
    # Usar potência para amplificar diferenças
    c_pow = np.power(c, 1.5)  # Ajuste o expoente (1.5 a 2.0)
    c_norm = (c_pow - c_pow.min()) / (c_pow.max() - c_pow.min() + 1e-9)
    return min_size + c_norm * (max_size - min_size)


def opacity_from_counts(counts: pd.Series) -> pd.Series:
    """
    Mais lojas = mais opaco (0.5 a 1.0)
    """
    import numpy as np
    c = counts.astype(float)
    c_norm = (c - c.min()) / (c.max() - c.min() + 1e-9)
    return 0.5 + c_norm * 0.5


# ============================================================
# MAPA ESTÁTICO MELHORADO
# ============================================================
def gerar_mapa_estatico(uf, gdf, grupos, color_map):
    xmin, ymin, xmax, ymax = uf.total_bounds
    pad_x = (xmax - xmin) * 0.08
    pad_y = (ymax - ymin) * 0.08

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.set_facecolor(OCEAN_COLOR)

    # Estados
    uf.plot(ax=ax, color=BR_FILL, edgecolor=BR_EDGE, linewidth=0.6, zorder=1)

    # Plotar grupos em ordem crescente de contagem (maiores por último = destaque)
    grupo_counts = gdf.groupby(COL_GRUPO)['n_lojas'].sum().sort_values()

    for grp in grupo_counts.index:
        sub = gdf[gdf[COL_GRUPO] == grp]
        sub.plot(
            ax=ax,
            markersize=sub["pt_size"],
            color=color_map[grp],
            edgecolor=POINT_EDGE,
            linewidth=0.8,
            alpha=sub["opacity"],
            zorder=2 + grupo_counts[grp]  # Mais lojas = maior z-order
        )

    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Título melhorado
    total_lojas = gdf['n_lojas'].sum()
    ax.set_title(f"Distribuição de {int(total_lojas)} Lojas por Grupo — Brasil",
                 fontsize=14, fontweight='bold', pad=12)

    # Legenda com número de lojas
    handles = []
    for grp in grupo_counts.index[::-1]:  # Ordem decrescente
        count = int(grupo_counts[grp])
        handles.append(
            Line2D([0], [0], marker='o', color='none',
                   label=f"{grp} ({count})",
                   markerfacecolor=color_map[grp],
                   markeredgecolor=POINT_EDGE,
                   markeredgewidth=0.8,
                   markersize=10)
        )

    leg = ax.legend(
        handles=handles,
        loc="lower left",
        frameon=True,
        framealpha=0.95,
        borderpad=1,
        labelspacing=0.7,
        handlelength=1,
        fontsize=10,
        title="Grupo (Lojas)",
        title_fontsize=11
    )
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("#cccccc")

    ax.text(0.01, 0.01, "Fonte: base de lojas + BR_UF_2024",
            transform=ax.transAxes, fontsize=8, alpha=0.7)

    plt.tight_layout()
    fig.savefig(OUT_PNG, dpi=DPI, bbox_inches="tight")
    print(f"✅ PNG gerado: {OUT_PNG}")
    plt.show()


# ============================================================
# MAPA INTERATIVO HTML (FOLIUM)
# ============================================================
def gerar_mapa_interativo(gdf, color_map):
    """
    Gera mapa HTML moderno com:
    - Hover para ver informações
    - Clusters opcionais
    - Controle de camadas
    - Popups ricos
    """
    # Centro do Brasil
    center_lat = gdf.geometry.y.mean()
    center_lon = gdf.geometry.x.mean()

    # Criar mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles='CartoDB positron',
        control_scale=True
    )

    # Adicionar tiles alternativos
    folium.TileLayer('OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB dark_matter').add_to(m)

    # Criar grupos de features para cada grupo de lojas
    grupos = sorted(gdf[COL_GRUPO].unique())
    feature_groups = {grp: folium.FeatureGroup(name=f'{grp} ({len(gdf[gdf[COL_GRUPO] == grp])})')
                      for grp in grupos}

    # Adicionar marcadores
    for idx, row in gdf.iterrows():
        grupo = row[COL_GRUPO]
        n_lojas = int(row['n_lojas'])

        # Tamanho proporcional
        radius = 3 + (row['pt_size'] / 10)

        # Popup rico
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="color: {color_map[grupo]}; margin: 0;">{grupo}</h4>
            <hr style="margin: 5px 0;">
            <p style="margin: 5px 0;"><b>Lojas neste local:</b> {n_lojas}</p>
            <p style="margin: 5px 0;"><b>Lat:</b> {row.geometry.y:.4f}</p>
            <p style="margin: 5px 0;"><b>Lon:</b> {row.geometry.x:.4f}</p>
        </div>
        """

        # Tooltip (hover)
        tooltip = f"<b>{grupo}</b><br>{n_lojas} loja(s)"

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=tooltip,
            color='white',
            weight=1.5,
            fill=True,
            fillColor=color_map[grupo],
            fillOpacity=0.7,
        ).add_to(feature_groups[grupo])

    # Adicionar grupos ao mapa em ordem crescente de lojas
    # (menor primeiro → maior por cima = AZZAS fica em destaque visual)
    grupo_totais = gdf.groupby(COL_GRUPO)['n_lojas'].sum().sort_values(ascending=True)
    for grp in grupo_totais.index:
        feature_groups[grp].add_to(m)

    # Controle de camadas
    folium.LayerControl(collapsed=False).add_to(m)

    # Plugin de tela cheia
    plugins.Fullscreen().add_to(m)

    # Minimap
    plugins.MiniMap().add_to(m)

    # ── LEGENDA CUSTOMIZADA ─────────────────────────────────────────────────
    # Ordenar grupos por total de lojas (decrescente) para a legenda
    grupo_totais_desc = gdf.groupby(COL_GRUPO)['n_lojas'].sum().sort_values(ascending=False)

    legend_items = ""
    for grp, total in grupo_totais_desc.items():
        color = color_map[grp]
        legend_items += (
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<svg width="16" height="16" style="margin-right:8px;flex-shrink:0;">'
            f'<circle cx="8" cy="8" r="7" fill="{color}" stroke="white" stroke-width="1.5"/>'
            f'</svg>'
            f'<span style="font-size:13px;color:#333;">{grp} '
            f'<span style="color:#666;">({int(total)})</span></span>'
            f'</div>'
        )

    legend_html = (
        '<div id="map-legend" style="'
        'position:fixed;bottom:30px;left:10px;z-index:1000;'
        'background:rgba(255,255,255,0.96);border:1px solid #ccc;'
        'border-radius:8px;padding:12px 16px;'
        'box-shadow:0 2px 8px rgba(0,0,0,0.18);'
        'font-family:Arial,sans-serif;min-width:200px;">'
        '<div style="font-size:14px;font-weight:bold;margin-bottom:10px;'
        'border-bottom:1px solid #eee;padding-bottom:6px;color:#222;">'
        'Grupo (Lojas)</div>'
        + legend_items +
        '</div>'
    )

    m.get_root().html.add_child(folium.Element(legend_html))

    # Salvar
    m.save(OUT_HTML)
    print(f"[OK] HTML interativo gerado: {OUT_HTML}")
    print(f"     Abra no navegador para visualizar!")


# ============================================================
# MAIN
# ============================================================
def main():
    ensure_exists(UF_SHP)
    ensure_exists(LOJAS_XLSX)

    # 1) LER UFs
    uf = gpd.read_file(UF_SHP)
    if uf.crs is None:
        uf = uf.set_crs("EPSG:4674")
    uf = uf.to_crs("EPSG:4326")

    # 2) LER LOJAS
    sheet = pick_excel_sheet(LOJAS_XLSX, SHEET_NAME)
    df = pd.read_excel(LOJAS_XLSX, sheet_name=sheet)

    for c in [COL_GRUPO, COL_LAT, COL_LON]:
        if c not in df.columns:
            raise ValueError(f"Coluna '{c}' não encontrada")

    # 3) NORMALIZAR COORDENADAS
    df[COL_LAT] = normalize_numeric(df[COL_LAT])
    df[COL_LON] = normalize_numeric(df[COL_LON])
    df = df.dropna(subset=[COL_LAT, COL_LON]).copy()

    if df.empty:
        raise ValueError("Nenhuma coordenada válida encontrada")

    # 4) AGRUPAR E CONTAR
    group_cols = [COL_GRUPO, COL_LAT, COL_LON]
    df_agg = df.groupby(group_cols, dropna=False).size().reset_index(name="n_lojas")

    # 5) GEODATAFRAME
    gdf = gpd.GeoDataFrame(
        df_agg,
        geometry=gpd.points_from_xy(df_agg[COL_LON], df_agg[COL_LAT]),
        crs="EPSG:4326"
    )

    # 6) CORES  (variáveis definidas na seção CONFIG no topo do arquivo)
    grupos = sorted(gdf[COL_GRUPO].astype(str).unique())
    _cores_config = {
        "AZZAS":          COR_AZZAS,
        "RENNER":         COR_RENNER,
        "SANTA LOLLA":    COR_SANTA_LOLLA,
        "LUIZA BARCELOS": COR_LUIZA_BARCELOS,
    }
    color_map = {grp: _cores_config.get(grp, COR_PADRAO) for grp in grupos}

    # 7) TAMANHO E OPACIDADE
    gdf["pt_size"] = size_from_counts(gdf["n_lojas"])
    gdf["opacity"] = opacity_from_counts(gdf["n_lojas"])

    # 8) GERAR MAPAS
    print("\n📊 Gerando mapa estático...")
    gerar_mapa_estatico(uf, gdf, grupos, color_map)

    print("\n🌐 Gerando mapa interativo HTML...")
    gerar_mapa_interativo(gdf, color_map)

    print("\n✅ CONCLUÍDO!")
    print(f"   - Mapa estático: {OUT_PNG}")
    print(f"   - Mapa interativo: {OUT_HTML}")


if __name__ == "__main__":
    main()