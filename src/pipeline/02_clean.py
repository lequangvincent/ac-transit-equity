import geopandas as gpd
import utils
import os

raw_dir = "../../data/raw"
clean_dir = "../../data/clean"


def clean_ca_tracts():
    # Load data
    gdf = gpd.read_file(
        os.path.join(raw_dir, "2024_06_tract.zip")
    )

    # Drop NaN, None, <NA>
    gdf = gdf.dropna()

    # Convert dtypes
    gdf = gdf.convert_dtypes()

    # Assert dtypes
    assert str(gdf["COUNTYFP"].dtype) == "string"
    assert str(gdf["TRACTCE"].dtype) == "string"
    assert str(gdf["geometry"].dtype) == "geometry"

    # Assert TRACTCE (primary key) has no duplicates
    assert len(gdf["TRACTCE"].unique()) == len(gdf)

    # Filter Alameda tracts
    gdf = gdf[gdf["COUNTYFP"] == "001"]

    # Select relevant columns
    gdf = gdf[["TRACTCE", "geometry"]]

    # Rename TRACTCE column
    gdf = gdf.rename(columns={"TRACTCE": "tract"})

    # Reset index
    gdf = gdf.reset_index(drop=True)

    # Export to GeoJSON
    gdf.to_file(
        os.path.join(clean_dir, "alameda_tracts.geojson"),
        driver="GeoJSON",
        index=False
    )


def clean_berkeley_boundary():
    # Load data
    gdf = gpd.read_file(utils.raw_dir("Land_Boundary_20251109.geojson"))

    # Reproject CRS to
    gdf = gdf.to_crs(epsg=4269)

    # Export to GeoJSON
    gdf.to_file(
        utils.clean_dir("berkeley_boundary.geojson"),
        driver="GeoJSON",
        index=False
    )


def clean_ac_stops():
    # Load data
    gdf = gpd.read_file(
        utils.raw_dir("UniqueStops_Fall25.zip")
    )

    # Select relevant columns
    gdf = gdf[["stp_511_id", "route", "geometry"]]

    # Rename columns
    gdf = gdf.rename(columns={
        "stp_511_id": "stop_id",
        "route": "routes"
    })

    # Drop missing data
    gdf = gdf.dropna()

    # Assert that each stop is unique
    assert len(gdf["stop_id"].unique()) == len(gdf)

    # Convert datatypes
    gdf[["stop_id", "routes"]] = gdf[["stop_id", "routes"]].astype("string")

    # Assert dtypes
    assert str(gdf["stop_id"].dtype) == "string"
    assert str(gdf["routes"].dtype) == "string"
    assert str(gdf["geometry"].dtype) == "geometry"

    # Convert routes string to list of routes
    gdf["routes"] = gdf["routes"].str.split(" ")

    # Export cleaned
    utils.export_clean(gdf, "ac_stops.geojson")

clean_ac_stops()
