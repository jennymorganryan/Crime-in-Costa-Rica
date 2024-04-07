import matplotlib.pyplot as plt
import pandas as pd
import folium
import numpy as np
from geopy.geocoders import ArcGIS
import geopandas as gpd
from branca.colormap import LinearColormap
from folium.features import GeoJsonPopup
import branca
from flask import Flask
from flask import Flask, render_template

import arcgis
import arcgis.geoanalytics
from arcgis.gis import GIS



#dataframes
one = pd.read_excel('../cr_crimen/estadsticaspoliciales2021.xls')
two = pd.read_excel('../cr_crimen/estadsticaspoliciales2022.xlsx')
three = pd.read_excel('../cr_crimen/estadsticaspoliciales2023.xlsx')
four = pd.read_excel('../cr_crimen/estadsticaspoliciales2024.xls')
df = pd.concat([one, two, three, four]) # raw crime info data frames
polygon_districts = gpd.read_file('../cr_crimen/Distritos_de_Costa_Rica.geojson') #polygon lat. & long. coordinates for each district in CR
crime_count = df.groupby(['Distrito', 'Delito']).size().reset_index(name='Ocurencias desde 2021') # dataframe with amount of crimes in each district grouped by type of crime
total_crime_count = crime_count.groupby('Distrito')['Ocurencias desde 2021'].sum().reset_index(name='Crimen total desde 2021') # dataframe with the total amount of crimes in each district
one_total = one.groupby('Distrito').size().reset_index(name='Delitos Total 2021') # dataframe with the total amount of crimes in 2021
two_total = two.groupby('Distrito').size().reset_index(name='Delitos Total 2022')# dataframe with the total amount of crimes in 2022
three_total = three.groupby('Distrito').size().reset_index(name='Delitos Total 2023')# dataframe with the total amount of crimes in 2023
four_total = four.groupby('Distrito').size().reset_index(name='Delitos Total 2024') # dataframe with the total amount of crimes in 2024
years_total = pd.merge(pd.merge(pd.merge(one_total, two_total, on='Distrito', how='inner'), three_total, on='Distrito', how='inner'), total_crime_count, on='Distrito', how='inner')
merged_popup = gpd.GeoDataFrame(
    pd.merge(polygon_districts, years_total, left_on='NOM_DIST', right_on='Distrito', how='inner'),
    geometry='geometry'
)
pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns


# connect to ArcGIS Enterprise Organization 
gis = GIS('https://pythonapi.playground.esri.com/portal', 'arcgis_python', 'amazing_arcgis_123')


# Costa Rica country coordinates & creation of the map object
costa_rica_coordinates = [9.7489, -83.7534]
cr = folium.Map(location=costa_rica_coordinates, zoom_start=8)

#colormap and color scale
colormap = branca.colormap.LinearColormap(
vmin=total_crime_count['Crimen total desde 2021'].quantile(0),
vmax=total_crime_count['Crimen total desde 2021'].quantile(1),
colors=["white", "yellow", "orange", "red", "darkred"],
caption="Crimen total desde 2021 (post-COVID)",
).add_to(cr)

# Add GeoJson layer to map with popup
gj=folium.GeoJson(
    merged_popup,
    name='geojson',
    style_function=lambda x: {
        "fillColor": colormap(x["properties"]["Crimen total desde 2021"])
        if x["properties"]["Crimen total desde 2021"] is not None
        else "transparent",
        "color": "black",
        "fillOpacity": 0.4,
    },
).add_to(cr)
popup = folium.GeoJsonPopup(
    name="crimen",
    fields=["NOM_DIST", "Crimen total desde 2021", "Delitos Total 2021", "Delitos Total 2022", "Delitos Total 2023"],
    aliases=["Distrito:", "Crimen Total 2021-Marzo 2024", 'Crimen Total en 2021', 'Crimen Total en 2022', 'Crimen Total en 2023'],
    localize=True,
    labels=True,
    style="background-color: white;",
).add_to(gj)

#layer control
folium.LayerControl().add_to(cr)

cr
#converts folium map to an HTML object

html_map = cr._repr_html_()  
app = Flask(__name__)
@app.route("/")
def index():
    return render_template("index.html", map=html_map)
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)