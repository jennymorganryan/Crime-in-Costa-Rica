import pandas as pd
import folium
import geopandas as gpd
import branca
import gc
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Read polygons
polygon_districts = gpd.read_file(os.path.join(DATA_DIR, "Distritos_de_Costa_Rica.geojson"))


def get_map():
    # Read crime data
    one = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2021.xls"), engine="xlrd")
    two = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2022.xlsx"), engine="openpyxl")
    three = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2023.xlsx"), engine="openpyxl")
    four = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2024.xls"), engine="xlrd")

    # Merge all datasets together for overall use
    df = pd.concat([one, two, three, four])

    # Load polygon shapes
    polygon_districts = gpd.read_file("data/Distritos_de_Costa_Rica.geojson")

    # Calculate crime counts
    crime_count = df.groupby(['Distrito', 'Delito']).size().reset_index(name='Ocurencias desde 2021')
    total_crime_count = crime_count.groupby('Distrito')['Ocurencias desde 2021'].sum().reset_index(name='Crimen total desde 2021')

    # Calculate per-year totals
    one_total = one.groupby('Distrito').size().reset_index(name='Delitos Total 2021')
    two_total = two.groupby('Distrito').size().reset_index(name='Delitos Total 2022')
    three_total = three.groupby('Distrito').size().reset_index(name='Delitos Total 2023')
    four_total = four.groupby('Distrito').size().reset_index(name='Delitos Total 2024')

    # Merge all yearly totals together
    years_total = pd.merge(
        pd.merge(
            pd.merge(
                pd.merge(one_total, two_total, on='Distrito'),
                three_total, on='Distrito'
            ),
            four_total, on='Distrito'
        ),
        total_crime_count, on='Distrito'
    )
    # Normalize polygon districts
    polygon_districts['NOM_DIST'] = polygon_districts['NOM_DIST']\
        .str.normalize('NFKD')\
        .str.encode('ascii', errors='ignore')\
        .str.decode('utf-8')\
        .str.lower()\
        .str.strip()\
        .apply(lambda x: re.sub(r'\s+', ' ', x))\
        .apply(lambda x: re.sub(r'[^\w\s]', '', x))

    # Normalize crime data districts
    years_total['Distrito'] = years_total['Distrito']\
        .str.normalize('NFKD')\
        .str.encode('ascii', errors='ignore')\
        .str.decode('utf-8')\
        .str.lower()\
        .str.strip()\
        .apply(lambda x: re.sub(r'\s+', ' ', x))\
        .apply(lambda x: re.sub(r'[^\w\s]', '', x))
        
        
    # Merge yearly totals into the GeoDataFrame
    merged_popup = gpd.GeoDataFrame(
        pd.merge(polygon_districts, years_total, left_on='NOM_DIST', right_on='Distrito', how='left'),
        geometry='geometry'
    )


    # Free memory
    del one, two, three, four, one_total, two_total, three_total, four_total
    gc.collect()

    # Build the Folium map
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
            if x["properties"]["Crimen total desde 2021"] is not None
            else "transparent",
            "color": "black",
            "fillOpacity": 0.4,
        }
    ).add_to(m)

    # Define popups for districts
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

    # Add layer control to switch layers
    folium.LayerControl().add_to(m)

    return m