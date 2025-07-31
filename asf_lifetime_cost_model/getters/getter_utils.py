import io
from typing import Optional, Tuple

import boto3
import pandas as pd
import requests


def _read_s3_csv_to_dataframe(
    bucket_name: str,
    s3_key: str,
) -> pd.DataFrame:
    """
    Get dataframe from .csv file stored in S3.

    Args:
        bucket_name (str): S3 bucket name
        s3_key (str): Key of file in S3 bucket

    Returns:
        pd.DataFrame: Dataframe of content in .csv file
    """
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
    content = io.BytesIO(obj["Body"].read())
    return pd.read_csv(content)


def _read_excel_to_dataframe(file_url: str) -> Optional[dict[str, pd.DataFrame]]:
    """
    Get a dictionary of dataframes from content in an Excel workbook stored at specified URL.

    Args:
        file_url (str): URL of target file.

    Returns:
        Optional[dict[str, pd.DataFrame]]: Dictionary of dataframes where each key-value pair is Excel sheet name-content.
    """
    try:
        response = requests.get(file_url)
        if response.status_code == 200:
            file_content = io.BytesIO(response.content)
            # Read all sheets into a dictionary
            all_sheets = pd.read_excel(file_content, sheet_name=None)
            return all_sheets
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error occurred while reading Excel file: {e}")
        return None
