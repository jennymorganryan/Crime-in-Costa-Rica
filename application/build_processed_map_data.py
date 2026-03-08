import os
import pandas as pd
import geopandas as gpd
from application.sync_bucket import download_processed_file_from_bucket, upload_processed_file_to_bucket
import boto3

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PROCESSED_PATH = os.path.join(DATA_DIR, "processed_crime_map.geojson")
BUCKET_OBJECT_KEY = "processed_crime_map.geojson"


def normalize_column(col):
    return (
        col.str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(r"[^\w\s]", "", regex=True)
    )


def bucket_enabled():
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


def download_from_bucket():
    if not bucket_enabled():
        return False

    s3 = get_s3_client()
    bucket_name = os.environ["BUCKET"]

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        s3.download_file(bucket_name, BUCKET_OBJECT_KEY, PROCESSED_PATH)
        print(f"Downloaded {BUCKET_OBJECT_KEY} from bucket")
        return True
    except Exception as e:
        print(f"Download skipped or failed: {e}")
        return False


def upload_to_bucket():
    if not bucket_enabled():
        return

    s3 = get_s3_client()
    bucket_name = os.environ["BUCKET"]

    s3.upload_file(
        PROCESSED_PATH,
        bucket_name,
        BUCKET_OBJECT_KEY,
        ExtraArgs={"ContentType": "application/geo+json"},
    )
    print(f"Uploaded {BUCKET_OBJECT_KEY} to bucket")


def build_processed_file():
    polygon_districts = gpd.read_file(
        os.path.join(DATA_DIR, "Distritos_de_Costa_Rica.geojson")
    )

    one = pd.read_excel(
        os.path.join(DATA_DIR, "estadsticaspoliciales2021.xls"),
        engine="xlrd",
    )
    two = pd.read_excel(
        os.path.join(DATA_DIR, "estadsticaspoliciales2022.xlsx"),
        engine="openpyxl",
    )
    three = pd.read_excel(
        os.path.join(DATA_DIR, "estadsticaspoliciales2023.xlsx"),
        engine="openpyxl",
    )
    four = pd.read_excel(
        os.path.join(DATA_DIR, "estadsticaspoliciales2024.xls"),
        engine="xlrd",
    )

    one["Canton"] = normalize_column(one["Canton"])
    one["Distrito"] = normalize_column(one["Distrito"])

    two["Canton"] = normalize_column(two["Canton"])
    two["Distrito"] = normalize_column(two["Distrito"])

    three["Canton"] = normalize_column(three["Canton"])
    three["Distrito"] = normalize_column(three["Distrito"])

    four["Canton"] = normalize_column(four["Canton"])
    four["Distrito"] = normalize_column(four["Distrito"])

    polygon_districts["NOM_CANT"] = normalize_column(polygon_districts["NOM_CANT"])
    polygon_districts["NOM_DIST"] = normalize_column(polygon_districts["NOM_DIST"])

    one_total = one.groupby(["Canton", "Distrito"]).size().reset_index(name="Delitos Total 2021")
    two_total = two.groupby(["Canton", "Distrito"]).size().reset_index(name="Delitos Total 2022")
    three_total = three.groupby(["Canton", "Distrito"]).size().reset_index(name="Delitos Total 2023")
    four_total = four.groupby(["Canton", "Distrito"]).size().reset_index(name="Delitos Total 2024")

    all_data = pd.concat([one, two, three, four], ignore_index=True)
    total_crime_count = (
        all_data.groupby(["Canton", "Distrito"])
        .size()
        .reset_index(name="Crimen total desde 2021")
    )

    years_total = (
        one_total.merge(two_total, on=["Canton", "Distrito"], how="outer")
        .merge(three_total, on=["Canton", "Distrito"], how="outer")
        .merge(four_total, on=["Canton", "Distrito"], how="outer")
        .merge(total_crime_count, on=["Canton", "Distrito"], how="outer")
    )

    merged = gpd.GeoDataFrame(
        polygon_districts.merge(
            years_total,
            left_on=["NOM_CANT", "NOM_DIST"],
            right_on=["Canton", "Distrito"],
            how="left",
        ),
        geometry="geometry",
        crs=polygon_districts.crs,
    )

    merged = merged[
        [
            "NOM_DIST",
            "Crimen total desde 2021",
            "Delitos Total 2021",
            "Delitos Total 2022",
            "Delitos Total 2023",
            "Delitos Total 2024",
            "geometry",
        ]
    ].copy()

    numeric_cols = [
        "Crimen total desde 2021",
        "Delitos Total 2021",
        "Delitos Total 2022",
        "Delitos Total 2023",
        "Delitos Total 2024",
    ]
    merged[numeric_cols] = merged[numeric_cols].fillna(0)

    merged = merged.to_crs(3857)
    merged["geometry"] = merged["geometry"].simplify(200, preserve_topology=True)
    merged = merged.to_crs(4326)

    os.makedirs(DATA_DIR, exist_ok=True)
    merged.to_file(PROCESSED_PATH, driver="GeoJSON")
    print(f"Saved processed file to {PROCESSED_PATH}")

    upload_to_bucket()
    return PROCESSED_PATH


def ensure_processed_file():
    if os.path.exists(PROCESSED_PATH):
        return PROCESSED_PATH

    downloaded = download_from_bucket()
    if downloaded and os.path.exists(PROCESSED_PATH):
        return PROCESSED_PATH

    #try to sync from the Bucket (Single Source of Truth)
    print("File not found locally. Attempting to sync from Railway Bucket...")
    if download_processed_file_from_bucket():
        return OUTPUT_PATH

    #if no bucket data exists, build it and then save to bucket
    print("No data in bucket. Generating new processed file...")
    path = build_processed_file()
    
    try:
        upload_processed_file_to_bucket()
    except Exception as e:
        print(f"Could not upload new file to bucket: {e}")
        
    return path


if __name__ == "__main__":
    ensure_processed_file()