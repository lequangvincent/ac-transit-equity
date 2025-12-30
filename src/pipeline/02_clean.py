import geopandas as gpd


def clean_ca_tracts():
    # Load data
    df = gpd.read_file("../../data/raw/2024_06_tract.zip")

    # Select relevant columns
    df = df[["COUNTYFP", "TRACTCE", "geometry"]]

    # Drop NaN, None, <NA>
    df = df.dropna()

    # Convert dtypes
    df = df.convert_dtypes()

    # Assert dtypes
    assert str(df["COUNTYFP"].dtype) == "string"
    assert str(df["TRACTCE"].dtype) == "string"
    assert str(df["geometry"].dtype) == "geometry"

    # Filter Alameda tracts
    df = df[df["COUNTYFP"] == "001"]


clean_ca_tracts()
