# 🗺️ Mapa de Lojas por Grupo — Brasil

Projeto de **visualização geográfica interativa** que coleta dados de lojas via APIs de múltiplas marcas, georreferencia os endereços e plota os pontos em um mapa do Brasil com análise por grupo varejista.

---

## 📌 Funcionalidades

- **Coleta de dados via API** de múltiplas marcas (Arezzo, Farm, Schutz, Hering, Animale, Reserva)
- **Georreferenciamento** de endereços com Google Maps API
- **Mapa estático (PNG)** com matplotlib + geopandas, com bolhas proporcionais ao número de lojas
- **Mapa interativo (HTML)** com Folium/Leaflet:
  - Controle de camadas por grupo
  - Popup com informações ao clicar
  - Tooltip ao passar o mouse
  - Legenda com total de lojas por grupo
  - Minimap e modo tela cheia
  - 3 estilos de mapa (claro, escuro, OpenStreetMap)

---

## 🛠️ Tecnologias

| Biblioteca | Uso |
|---|---|
| `pandas` | Manipulação de dados |
| `geopandas` | Dados geoespaciais |
| `matplotlib` | Mapa estático PNG |
| `folium` | Mapa interativo HTML |
| `requests` | Chamadas às APIs das marcas |

---

## 📁 Estrutura do Projeto

```
API Arezzo/
│
├── Plote_pontos.py          # Script principal — gera os mapas
├── API_AREZZO.py            # Coleta de lojas Arezzo via API
├── API_FARM.py              # Coleta de lojas Farm via API
├── API_SCHUTZ.py            # Coleta de lojas Schutz via API
├── API_HERING.py            # Coleta de lojas Hering via API
├── API_ANIMALE.py           # Coleta de lojas Animale via API
├── API_RESERVA.py           # Coleta de lojas Reserva via API
├── API_googleMaps.py        # Georreferenciamento via Google Maps API
└── GeoPackage.py            # Exportação para formato GeoPackage (QGIS)
```

> ⚠️ **Os arquivos de dados (`.xlsx`, `.csv`, `.json`) não estão incluídos** neste repositório por conterem informações proprietárias. Execute os scripts de API para gerar os dados locais.

---

## 🚀 Como Executar

### Pré-requisitos
```bash
pip install pandas geopandas matplotlib folium branca openpyxl requests
```

### Gerar os mapas
```bash
python Plote_pontos.py
```

Serão gerados:
- `mapa_lojas.png` — mapa estático de alta resolução
- `mapa_lojas_interativo.html` — mapa interativo (abrir no navegador)

### Personalizar cores dos grupos
No topo do arquivo `Plote_pontos.py`, edite as variáveis:
```python
COR_AZZAS          = "#e41a1c"   # vermelho
COR_RENNER         = "#4daf4a"   # verde
COR_SANTA_LOLLA    = "#984ea3"   # roxo
COR_LUIZA_BARCELOS = "#377eb8"   # azul
```

---

## 📊 Resultados

O mapa distribui **~2.300+ lojas** de 4 grupos varejistas pelo Brasil, com bolhas proporcionais ao número de pontos de venda por localidade.

---

## 👤 Autor

Desenvolvido como projeto de análise de dados geoespaciais com foco em inteligência de mercado para o varejo de moda.
