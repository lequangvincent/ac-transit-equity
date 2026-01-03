import geopandas as gpd
import os


def raw_dir(filename):
    return os.path.join("../../data/raw", filename)


def clean_dir(filename):
    return os.path.join("../../data/clean", filename)

def export_clean(gdf, filename):
    # Assert input is a geodataframe

    assert isinstance(gdf, gpd.GeoDataFrame)

    gdf.to_file(
        clean_dir(filename),
        driver="GeoJSON",
        index=False
    )
