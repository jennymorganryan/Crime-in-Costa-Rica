import pandas as pd
import folium
import geopandas as gpd
import branca
import gc
import re

# --- Normalize helper ---
def normalize(series):
    return series\
        .astype(str)\
        .str.normalize('NFKD')\
        .str.encode('ascii', errors='ignore')\
        .str.decode('utf-8')\
        .str.lower()\
        .str.strip()\
        .apply(lambda x: re.sub(r'\s+', ' ', x) if isinstance(x, str) else x)\
        .apply(lambda x: re.sub(r'[^\w\s]', '', x) if isinstance(x, str) else x)

# --- Read data ---
one = pd.read_excel(
    "https://www.dropbox.com/scl/fi/20qkrvlcrjv4ur5rknm6o/estadsticaspoliciales2021.xls?rlkey=ldvgqoh7ml3p3ivpjpmk6ebmm&st=3jz9kkyy&dl=1", 
    engine='xlrd'
)
two = pd.read_excel(
    "https://www.dropbox.com/scl/fi/t0q93ydab9yqder6umvk3/estadsticaspoliciales2022.xlsx?rlkey=34dr2an4wfqlcsrln1yhxanc5&st=jjt8nq46&dl=1", 
    engine='openpyxl'
)
three = pd.read_excel(
    "https://www.dropbox.com/scl/fi/45k4w5kde9cn7h5edkdsx/estadsticaspoliciales2023.xlsx?rlkey=zxaepnht3b13bswfyw19raoql&st=3fpz2b2j&dl=1", 
    engine='openpyxl'
)
four = pd.read_excel(
    "https://www.dropbox.com/scl/fi/lsbld4k8htzd06m7njbar/estadsticaspoliciales2024.xls?rlkey=4g8tv502w00wekw0gbsywyr1j&st=zsld1emk&dl=1", 
    engine='xlrd'
)

# 🔥 Fix 2024 file: rename 'Cantón' to 'Canton'
four.rename(columns=lambda x: x.strip(), inplace=True)
four.rename(columns={'Cantón': 'Canton'}, inplace=True)

# --- Merge all datasets together
df = pd.concat([one, two, three, four])

# --- Load polygons ---
polygon_districts = gpd.read_file("Distritos_de_Costa_Rica.geojson")

# --- Normalize columns ---
polygon_districts['NOM_DIST'] = normalize(polygon_districts['NOM_DIST'])
polygon_districts['NOM_CANT'] = normalize(polygon_districts['NOM_CANT'])

df['Distrito'] = normalize(df['Distrito'])
df['Canton'] = normalize(df['Canton'])  

# --- Crime Calculations ---

# Total crimes grouped
crime_count = df.groupby(['Distrito', 'Canton', 'Delito']).size().reset_index(name='Ocurencias desde 2021')
total_crime_count = crime_count.groupby(['Distrito', 'Canton'])['Ocurencias desde 2021'].sum().reset_index(name='Crimen total desde 2021')

# Totals per year
one_total = one.groupby(['Distrito', 'Canton']).size().reset_index(name='Delitos Total 2021')
two_total = two.groupby(['Distrito', 'Canton']).size().reset_index(name='Delitos Total 2022')
three_total = three.groupby(['Distrito', 'Canton']).size().reset_index(name='Delitos Total 2023')
four_total = four.groupby(['Distrito', 'Canton']).size().reset_index(name='Delitos Total 2024')

# Merge yearly totals together
years_total = pd.merge(
    pd.merge(
        pd.merge(
            pd.merge(one_total, two_total, on=['Distrito', 'Canton']),
            three_total, on=['Distrito', 'Canton']
        ),
        four_total, on=['Distrito', 'Canton']
    ),
    total_crime_count, on=['Distrito', 'Canton']
)

# --- Merge polygons with crime data based on District+Canton ---

# Create key for matching
polygon_districts['district_canton'] = polygon_districts['NOM_DIST'] + " - " + polygon_districts['NOM_CANT']
years_total['district_canton'] = years_total['Distrito'] + " - " + years_total['Canton']

merged_popup = gpd.GeoDataFrame(
    pd.merge(polygon_districts, years_total, on='district_canton', how='left'),
    geometry='geometry'
)

# Fill missing fields
columns_to_fill = [
    "Crimen total desde 2021",
    "Delitos Total 2021",
    "Delitos Total 2022",
    "Delitos Total 2023",
    "Delitos Total 2024"
]
merged_popup[columns_to_fill] = merged_popup[columns_to_fill].fillna("No Data")


# --- Build the Map ---

costa_rica_coordinates = [9.7489, -83.7534]
m = folium.Map(location=costa_rica_coordinates, zoom_start=8)

# Define color map
colormap = branca.colormap.LinearColormap(
    vmin=total_crime_count['Crimen total desde 2021'].quantile(0),
    vmax=total_crime_count['Crimen total desde 2021'].quantile(1),
    colors=["white", "yellow", "orange", "red", "darkred"],
    caption="Total Crime from 2021-2024 (post-COVID)"
).add_to(m)

# Add GeoJson layer
gj = folium.GeoJson(
    merged_popup,
    name='geojson',
    style_function=lambda x: {
        "fillColor": colormap(x["properties"]["Crimen total desde 2021"])
        if x["properties"]["Crimen total desde 2021"] != "No Data"
        else "transparent",
        "color": "black",
        "fillOpacity": 0.4,
    }
).add_to(m)

# Popups
popup = folium.GeoJsonPopup(
    name="Crime",
    fields=[
        "NOM_DIST", 
        "Crimen total desde 2021", 
        "Delitos Total 2021", 
        "Delitos Total 2022", 
        "Delitos Total 2023", 
        "Delitos Total 2024"
    ],
    aliases=[
        "District:", 
        "Total Crime 2021-2024", 
        "2021", 
        "2022", 
        "2023", 
        "2024"
    ],
    localize=True,
    labels=True,
    style="background-color: white;"
).add_to(gj)

# Add layer control
folium.LayerControl().add_to(m)

# Export the map
def get_map():
    return m
