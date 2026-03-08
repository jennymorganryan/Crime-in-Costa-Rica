import os
import folium
import branca
import geopandas as gpd
import boto3
from folium.plugins import Search
from application.build_processed_map_data import build_processed_file

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PROCESSED_PATH = os.path.join(DATA_DIR, "processed_crime_map.geojson")
BUCKET_OBJECT_KEY = "processed_crime_map.geojson"


def bucket_vars_present():
    bucket = os.environ.get("BUCKET")
    access_key_id = os.environ.get("ACCESS_KEY_ID")
    secret_access_key = os.environ.get("SECRET_ACCESS_KEY")
    region = os.environ.get("REGION")
    endpoint = os.environ.get("ENDPOINT")

    if not bucket:
        return False
    if not access_key_id:
        return False
    if not secret_access_key:
        return False
    if not region:
        return False
    if not endpoint:
        return False

    return True


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["ENDPOINT"],
        aws_access_key_id=os.environ["ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["SECRET_ACCESS_KEY"],
        region_name=os.environ["REGION"],
    )


def download_processed_file_from_bucket():
    if not bucket_vars_present():
        print("Bucket variables not found. Skipping download.")
        return

    bucket_name = os.environ["BUCKET"]
    s3 = get_s3_client()

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        s3.download_file(bucket_name, BUCKET_OBJECT_KEY, PROCESSED_PATH)
        print(f"Downloaded processed file from bucket: s3://{bucket_name}/{BUCKET_OBJECT_KEY}")
    except Exception as e:
        print(f"Bucket download skipped or failed: {e}")


def ensure_processed_file_exists():
    if os.path.exists(PROCESSED_PATH):
        return

    download_processed_file_from_bucket()

    if not os.path.exists(PROCESSED_PATH):
        build_processed_file()


def get_map():
    ensure_processed_file_exists()
    merged_popup = gpd.read_file(PROCESSED_PATH)

    costa_rica_coordinates = [9.7489, -83.7534]
    m = folium.Map(location=costa_rica_coordinates, zoom_start=8)

    colormap = branca.colormap.LinearColormap(
        vmin=merged_popup["Crimen total desde 2021"].min(),
        vmax=merged_popup["Crimen total desde 2021"].max(),
        colors=["white", "yellow", "orange", "red", "darkred"],
        caption="Total Number of Reported Crimes Committed POST COVID (2021 to 2024)"
    ).add_to(m)

    gj = folium.GeoJson(
        PROCESSED_PATH,
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