import pandas as pd
import folium
import geopandas
import geopandas as gpd
import branca
from flask import Flask
from flask import Flask, render_template
import arcgis
import arcgis.geoanalytics
from arcgis.gis import GIS
import requests
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import urllib

#TRANSLATIONS: distrito = district, crimen = crime, delitos = crimes

#read date
one = pd.read_excel("https://www.dropbox.com/scl/fi/20qkrvlcrjv4ur5rknm6o/estadsticaspoliciales2021.xls?rlkey=ldvgqoh7ml3p3ivpjpmk6ebmm&st=3jz9kkyy&dl=1", engine='xlrd')
two = pd.read_excel("https://www.dropbox.com/scl/fi/t0q93ydab9yqder6umvk3/estadsticaspoliciales2022.xlsx?rlkey=34dr2an4wfqlcsrln1yhxanc5&st=jjt8nq46&dl=1", engine='openpyxl')
three = pd.read_excel("https://www.dropbox.com/scl/fi/45k4w5kde9cn7h5edkdsx/estadsticaspoliciales2023.xlsx?rlkey=zxaepnht3b13bswfyw19raoql&st=3fpz2b2j&dl=1", engine='openpyxl')
four = pd.read_excel("https://www.dropbox.com/scl/fi/vi8gaw6f0npk27rh7i4u8/estadsticaspoliciales2024.xls?rlkey=nugn9gwiyv36f5mxbevgwnvw2&st=txwpbc3x&dl=1", engine='xlrd')

# Concatenate DataFrames
df = pd.concat([one, two, three, four])

#polygon coordinates dataframe
url = "https://www.dropbox.com/scl/fi/evnmc70nvkq4t00cdhsf2/Distritos_de_Costa_Rica.geojson?rlkey=eagdt1l1hcldychenhxboxfxy&st=m02k7d4n&dl=0"

try:
    polygon_districts = gpd.read_file(url)
except Exception:
    # Extract filename from URL
    filename = urllib.parse.urlparse(url).path.split("/")[-1]
    
    # Download the file
    r = requests.get(url, stream=True, headers={"User-Agent": "XY"})
    
    # Save the file locally
    with open(filename, "wb") as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
    
    try:
        # Attempt to extract if the file is a ZIP
        zfile = ZipFile(filename)
        zfile.extractall()
        # Read the extracted GeoJSON file
        polygon_districts = gpd.read_file(filename.split(".")[0])
    except BadZipFile:
        # If it's not a ZIP or extraction fails, print the content of the file
        with open(filename) as fh:
            print(fh.read())
        # Assign an empty GeoDataFrame to polygon_districts
        polygon_districts = gpd.GeoDataFrame()
    
# dataframe with amount of crimes in each district grouped by type of crime
crime_count = df.groupby(['Distrito', 'Delito']).size().reset_index(name='Ocurencias desde 2021') 
 # dataframe with the total amount of crimes in each district
total_crime_count = crime_count.groupby('Distrito')['Ocurencias desde 2021'].sum().reset_index(name='Crimen total desde 2021')
# dataframe with the total amount of crimes in 2021
one_total = one.groupby('Distrito').size().reset_index(name='Delitos Total 2021')
# dataframe with the total amount of crimes in 2022
two_total = two.groupby('Distrito').size().reset_index(name='Delitos Total 2022')
# dataframe with the total amount of crimes in 2023
three_total = three.groupby('Distrito').size().reset_index(name='Delitos Total 2023')
# dataframe with the total amount of crimes in 2024
four_total = four.groupby('Distrito').size().reset_index(name='Delitos Total 2024') 
years_total = pd.merge(pd.merge(pd.merge(one_total, two_total, on='Distrito', how='inner'), three_total, on='Distrito', how='inner'), total_crime_count, on='Distrito', how='inner')
merged_popup = gpd.GeoDataFrame(
    pd.merge(polygon_districts, years_total, left_on='NOM_DIST', right_on='Distrito', how='inner'),
    geometry='geometry'
)
pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns



# Costa Rica country coordinates & creation of the map object
costa_rica_coordinates = [9.7489, -83.7534]
cr = folium.Map(location=costa_rica_coordinates, zoom_start=8)

#colormap and color scale
colormap = branca.colormap.LinearColormap(
vmin=total_crime_count['Crimen total desde 2021'].quantile(0),
vmax=total_crime_count['Crimen total desde 2021'].quantile(1),
colors=["white", "yellow", "orange", "red", "darkred"],
caption="Total Crime from 2021 (post-COVID)",
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
    name="Crime",
    fields=["NOM_DIST", "Crimen total desde 2021", "Delitos Total 2021", "Delitos Total 2022", "Delitos Total 2023"],
    aliases=["District:", "Total Crime 2021-March 2024", '2021 Total Crime', '2022 Total Crime', '2023 Total Crime'],
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
@app.route("/index")
def index():
    return render_template("index.html", map=html_map)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)