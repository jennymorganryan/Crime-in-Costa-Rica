import os
import boto3
from application.build_processed_map_data import ensure_processed_file

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


def upload_processed_file_to_bucket():
    if not bucket_vars_present():
        raise RuntimeError("Bucket variables are missing")

    processed_path = ensure_processed_file()

    if not os.path.exists(processed_path):
        raise FileNotFoundError(f"Processed file not found: {processed_path}")

    s3 = get_s3_client()
    bucket_name = os.environ["BUCKET"]

    s3.upload_file(
        processed_path,
        bucket_name,
        BUCKET_OBJECT_KEY,
        ExtraArgs={"ContentType": "application/geo+json"},
    )

    print(f"Uploaded {processed_path} to s3://{bucket_name}/{BUCKET_OBJECT_KEY}")


if __name__ == "__main__":
    upload_processed_file_to_bucket()