import os
import pandas as pd
import geopandas as gpd
import boto3

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "processed_crime_map.geojson")
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


def upload_to_bucket(file_path):
    if not bucket_vars_present():
        print("Bucket variables not found. Skipping upload.")
        return

    s3 = get_s3_client()
    bucket_name = os.environ["BUCKET"]

    s3.upload_file(
        file_path,
        bucket_name,
        BUCKET_OBJECT_KEY,
        ExtraArgs={"ContentType": "application/geo+json"},
    )

    print(f"Uploaded processed file to bucket: s3://{bucket_name}/{BUCKET_OBJECT_KEY}")


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

    for df in [one, two, three, four]:
        df["Canton"] = normalize_column(df["Canton"])
        df["Distrito"] = normalize_column(df["Distrito"])

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

    merged.to_file(OUTPUT_PATH, driver="GeoJSON")
    print(f"Saved processed file to {OUTPUT_PATH}")

    upload_to_bucket(OUTPUT_PATH)


if __name__ == "__main__":
    build_processed_file()