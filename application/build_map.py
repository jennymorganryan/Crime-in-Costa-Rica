import pandas as pd
import folium
from folium.plugins import Search
import geopandas as gpd
import branca
import gc
import re
import os


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# helper function to normalize column names (in our case, 'Canton' and 'Distrito')
def normalize_column(col):
    return col.str.normalize('NFKD')\
            .str.encode('ascii', errors='ignore')\
            .str.decode('utf-8')\
            .str.lower()\
            .str.strip()\
            .str.replace(r'\s+', ' ', regex=True)\
            .str.replace(r'[^\w\s]', '', regex=True)
# Helper function to capitalize the first letter of each word
def capitalize_words(col):
    return col.str.title()

# function to create and return our choropleth map         
def get_map():
    
    # Read geoJSON file for Costa Rica districts
    polygon_districts = gpd.read_file("data/Distritos_de_Costa_Rica.geojson")
    
    # Read crime data
    one = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2021.xls"), engine="xlrd")
    two = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2022.xlsx"), engine="openpyxl")
    three = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2023.xlsx"), engine="openpyxl")
    four = pd.read_excel(os.path.join(DATA_DIR, "estadsticaspoliciales2024.xls"), engine="xlrd")


    # After reading the 4 datasets we normalize the 'Canton' and 'Distrito' columns to prep for merging
    one['Canton'] = normalize_column(one['Canton'])
    one['Distrito'] = normalize_column(one['Distrito'])

    two['Canton'] = normalize_column(two['Canton'])
    two['Distrito'] = normalize_column(two['Distrito'])

    three['Canton'] = normalize_column(three['Canton'])
    three['Distrito'] = normalize_column(three['Distrito'])

    four['Canton'] = normalize_column(four['Canton'])
    four['Distrito'] = normalize_column(four['Distrito'])

    # Merge all datasets together for overall use
    df = pd.concat([one, two, three, four])

        
    # Normalize 'Canton' column in geojson
    polygon_districts['NOM_CANT'] = normalize_column(polygon_districts['NOM_CANT']) 
        

    # Normalize polygon districts in geojson
    polygon_districts['NOM_DIST'] = normalize_column(polygon_districts['NOM_DIST'])
    
        
    # Calculate total crime counts by year
    one_total = one.groupby(['Canton', 'Distrito']).size().reset_index(name='Delitos Total 2021')
    two_total = two.groupby(['Canton', 'Distrito']).size().reset_index(name='Delitos Total 2022')
    three_total = three.groupby(['Canton', 'Distrito']).size().reset_index(name='Delitos Total 2023')
    four_total = four.groupby(['Canton', 'Distrito']).size().reset_index(name='Delitos Total 2024')

    # Calculate total crime counts for all evaluated years (2021 - 2024)
    crime_count = df.groupby(['Canton', 'Distrito', 'Delito']).size().reset_index(name='Ocurencias desde 2021')
    total_crime_count = crime_count.groupby(['Canton', 'Distrito'])['Ocurencias desde 2021'].sum().reset_index(name='Crimen total desde 2021')


    # Merge totals together for each year
    years_total = pd.merge(
        pd.merge(
            pd.merge(
                pd.merge(one_total, two_total, on=['Canton', 'Distrito'], how='outer'),
                three_total, on=['Canton', 'Distrito'], how='outer'
            ),
            four_total, on=['Canton', 'Distrito'], how='outer'
        ),
        total_crime_count, on=['Canton', 'Distrito'], how='outer'
    )
    
        
    # Merge yearly totals into the GeoDataFrame
    merged_popup = gpd.GeoDataFrame(
        pd.merge(
            polygon_districts, 
            years_total, 
            left_on=['NOM_CANT', 'NOM_DIST'], 
            right_on=['Canton', 'Distrito'], 
            how='left'
        ),
        geometry='geometry'
    )
    

    # Free up some memory
    del one, two, three, four, one_total, two_total, three_total, four_total
    gc.collect()
    
    # Capitalize the first letter of each word in the 'NOM_DIST' column so we can display it in the popup
    merged_popup['NOM_DIST'] = capitalize_words(merged_popup['NOM_DIST'])
    
    # Build the Folium map
    costa_rica_coordinates = [9.7489, -83.7534]
    m = folium.Map(location=costa_rica_coordinates, zoom_start=8)

    # Define color map
    colormap = branca.colormap.LinearColormap(
        vmin=total_crime_count['Crimen total desde 2021'].quantile(0),
        vmax=total_crime_count['Crimen total desde 2021'].quantile(1),
        colors=["white", "yellow", "orange", "red", "darkred"],
        caption="Total Number of Reported Crimes Committed POST-COVID (2021-2024)"
    ).add_to(m)

    # Add GeoJson layer - 
    gj = folium.GeoJson(
        merged_popup,
        name='geojson',
        style_function=lambda x: {
            "fillColor": colormap(x["properties"]["Crimen total desde 2021"])
            if x["properties"]["Crimen total desde 2021"] is not None
            else "gray",
            "color": "black",
            "weight": 1,
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
            "Reported Crimes 2021-2024:", 
            "Reported Crimes 2021:", 
            "Reported Crimes 2022:", 
            "Reported Crimes 2023:", 
            "Reported Crimes 2024:"
        ],
        localize=True,
        labels=True,
        style="background-color: white;",
    ).add_to(gj)
    
    # Add Search plugin
    Search(
        layer=gj,
        geom_type="polygon",
        weight=0,
        search_label="NOM_DIST", 
        placeholder="Search for a district",
        collapsed=True
    ).add_to(m)

    # Add layer control to switch layers
    folium.LayerControl().add_to(m)

    return m
