import geopandas as gpd
import os


def ingest_berkeley_boundary():
    url = "https://data.cityofberkeley.info/resource/e3zv-nuhf.geojson"

    try:
        gdf = gpd.read_file(url)

        if gdf.empty:
            raise ValueError()

        gdf.to_file("berkeley_boundary.geojson", driver="GeoJSON")

    except Exception as e:
        raise e

output_dir = "../data/raw"

os.makedirs(output_dir, exist_ok=True)