import folium
import branca
import geopandas as gpd
from folium.plugins import Search
from application.build_processed_map_data import ensure_processed_file


def get_map():
    processed_path = ensure_processed_file()
    merged_popup = gpd.read_file(processed_path)

    costa_rica_coordinates = [9.7489, -83.7534]
    m = folium.Map(location=costa_rica_coordinates, zoom_start=8)

    colormap = branca.colormap.LinearColormap(
        vmin=merged_popup["Crimen total desde 2021"].min(),
        vmax=merged_popup["Crimen total desde 2021"].max(),
        colors=["white", "yellow", "orange", "red", "darkred"],
        caption="Total Number of Reported Crimes Committed POST COVID (2021 to 2024)"
    ).add_to(m)

    gj = folium.GeoJson(
        processed_path,
        name="geojson",
        smooth_factor=2,
        style_function=lambda x: {
            "fillColor": colormap(x["properties"]["Crimen total desde 2021"])
            if x["properties"]["Crimen total desde 2021"] is not None
            else "gray",
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.4,
        }
    ).add_to(m)

    folium.GeoJsonPopup(
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
            "Reported Crimes 2021 to 2024:",
            "Reported Crimes 2021:",
            "Reported Crimes 2022:",
            "Reported Crimes 2023:",
            "Reported Crimes 2024:"
        ],
        localize=True,
        labels=True,
        style="background-color: white;",
    ).add_to(gj)

    Search(
        layer=gj,
        geom_type="polygon",
        weight=0,
        search_label="NOM_DIST",
        placeholder="Search for a district",
        collapsed=True
    ).add_to(m)

    folium.LayerControl().add_to(m)

    return m