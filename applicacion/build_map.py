import pandas as pd
import folium
import geopandas as gpd
import branca
import gc

# Read data
one = pd.read_excel("https://www.dropbox.com/scl/fi/20qkrvlcrjv4ur5rknm6o/estadsticaspoliciales2021.xls?rlkey=ldvgqoh7ml3p3ivpjpmk6ebmm&st=3jz9kkyy&dl=1", engine='xlrd')
two = pd.read_excel("https://www.dropbox.com/scl/fi/t0q93ydab9yqder6umvk3/estadsticaspoliciales2022.xlsx?rlkey=34dr2an4wfqlcsrln1yhxanc5&st=jjt8nq46&dl=1", engine='openpyxl')
three = pd.read_excel("https://www.dropbox.com/scl/fi/45k4w5kde9cn7h5edkdsx/estadsticaspoliciales2023.xlsx?rlkey=zxaepnht3b13bswfyw19raoql&st=3fpz2b2j&dl=1", engine='openpyxl')
four = pd.read_excel("https://www.dropbox.com/scl/fi/vi8gaw6f0npk27rh7i4u8/estadsticaspoliciales2024.xls?rlkey=nugn9gwiyv36f5mxbevgwnvw2&st=txwpbc3x&dl=1", engine='xlrd')

# Merge datasets
df = pd.concat([one, two, three, four])

# Load polygons
polygon_districts = gpd.read_file("Distritos_de_Costa_Rica.geojson")

# Crime calculations
crime_count = df.groupby(['Distrito', 'Delito']).size().reset_index(name='Ocurencias desde 2021')
total_crime_count = crime_count.groupby('Distrito')['Ocurencias desde 2021'].sum().reset_index(name='Crimen total desde 2021')

one_total = one.groupby('Distrito').size().reset_index(name='Delitos Total 2021')
two_total = two.groupby('Distrito').size().reset_index(name='Delitos Total 2022')
three_total = three.groupby('Distrito').size().reset_index(name='Delitos Total 2023')
four_total = four.groupby('Distrito').size().reset_index(name='Delitos Total 2024')

years_total = pd.merge(pd.merge(pd.merge(one_total, two_total, on='Distrito'), three_total, on='Distrito'), total_crime_count, on='Distrito')
merged_popup = gpd.GeoDataFrame(
    pd.merge(polygon_districts, years_total, left_on='NOM_DIST', right_on='Distrito', how='inner'),
    geometry='geometry'
)

# Free up memory
del one, two, three, four, one_total, two_total, three_total, four_total
gc.collect()

# Build map
costa_rica_coordinates = [9.7489, -83.7534]
m = folium.Map(location=costa_rica_coordinates, zoom_start=8)

colormap = branca.colormap.LinearColormap(
    vmin=total_crime_count['Crimen total desde 2021'].quantile(0),
    vmax=total_crime_count['Crimen total desde 2021'].quantile(1),
    colors=["white", "yellow", "orange", "red", "darkred"],
    caption="Total Crime from 2021 (post-COVID)"
).add_to(m)

gj = folium.GeoJson(
    merged_popup,
    name='geojson',
    style_function=lambda x: {
        "fillColor": colormap(x["properties"]["Crimen total desde 2021"])
        if x["properties"]["Crimen total desde 2021"] is not None
        else "transparent",
        "color": "black",
        "fillOpacity": 0.4,
    }
).add_to(m)

popup = folium.GeoJsonPopup(
    name="Crime",
    fields=["NOM_DIST", "Crimen total desde 2021", "Delitos Total 2021", "Delitos Total 2022", "Delitos Total 2023"],
    aliases=["District:", "Total Crime 2021-2024", "2021", "2022", "2023"],
    localize=True,
    labels=True,
    style="background-color: white;"
).add_to(gj)

folium.LayerControl().add_to(m)

# Export map object
def get_map():
    return m
