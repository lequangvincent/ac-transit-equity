import geopandas as gpd
from dotenv import load_dotenv
import utils
import os
import requests
import json
from datetime import date


def ingest_berkeley_boundary():
    url = "https://data.cityofberkeley.info/resource/e3zv-nuhf.geojson"

    try:
        gdf = gpd.read_file(url)

        if gdf.empty:
            raise ValueError()

        gdf.to_file("berkeley_boundary.geojson", driver="GeoJSON")

    except Exception as e:
        raise e


def ingest_schedule():

    # All AC Transit routes in Berkeley
    routes = ['FS', '6', '18', '7', '688', '604', 'E', '51B', '67', '36', '52', '802',
              '27', '605', '800', '12', '88', '72L', 'J', '72', '22', '72M', 'G', 'F', '851', '65']

    routes_param = ",".join(routes)
    api_key = os.getenv("AC_TRANSIT_API_KEY")
    url = f"https://api.actransit.org/transit/route/{routes_param}/schedule?token={api_key}&dayCode=Weekday&hasAllStops=True"

    response = requests.get(url, timeout=10)

    assert response.status_code == 200

    raw = response.json()

    today = date.today().isoformat()
    filename = f"schedule_{today}.json"

    with open(utils.raw_dir(filename), "w") as json_file:
        json.dump(raw, json_file, indent=4)


if __name__ == "__main__":

    # Create directories
    output_dir = "../data/raw"
    os.makedirs(output_dir, exist_ok=True)

    # Load .env file
    load_dotenv(dotenv_path="../../.env")

    # Ingest data
    ingest_schedule()
