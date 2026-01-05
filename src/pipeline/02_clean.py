import geopandas as gpd
import pandas as pd
import utils


# North American CRS (project to this for spatial joins)
na_crs = 4269


def clean_ca_tracts():

    # Load data
    gdf = gpd.read_file(
        utils.raw_dir("2024_06_tract.zip")
    )

    # Rename columns
    gdf = gdf.rename(columns={
        "COUNTYFP": "county",
        "TRACTCE": "tract"
    })

    # Drop missing values
    gdf = gdf.dropna(subset=["county", "tract", "geometry"])

    # Assert data not empty
    assert not gdf.empty

    # Convert datatypes
    gdf[["county", "tract"]] = gdf[["county", "tract"]].astype("string")

    # Filter for Alameda county rows
    gdf = gdf[gdf["county"] == "001"]

    # Assert no duplicate tracts
    assert len(gdf["tract"].unique()) == len(gdf)

    # Select relevant columns
    gdf = gdf[["tract", "geometry"]]

    # Reset index
    gdf = gdf.reset_index(drop=True)

    # Assert valid geometries
    assert gdf.is_valid.all()

    # Assert CRS by default is Census NAD83 (EPSG:4269)
    assert gdf.crs is not None
    assert gdf.crs.to_epsg() == na_crs

    # Export cleaned
    utils.export_clean(gdf, "alameda_tracts.geojson")


def clean_berkeley_boundary():

    # Load data
    gdf = gpd.read_file(utils.raw_dir("Land_Boundary_20251109.geojson"))

    # Assert data not empty
    assert not gdf.empty

    # Select relevant column
    gdf = gdf[["geometry"]]

    # Assert valid geometry
    assert gdf.is_valid.all()

    # Set CRS to NAD83 (EPSG:4269)
    if gdf.crs is None:
        gdf = gdf.set_crs(na_crs)
    else:
        gdf = gdf.to_crs(na_crs)

    # Export cleaned
    utils.export_clean(gdf, "berkeley_boundary.geojson")


def clean_ac_stops():

    # Load data
    gdf = gpd.read_file(
        utils.raw_dir("UniqueStops_Fall25.zip")
    )

    # Rename columns
    gdf = gdf.rename(columns={
        "stp_511_id": "stop_id",
        "route": "routes"
    })

    # Select relevant columns
    gdf = gdf[["stop_id", "routes", "geometry"]]

    # Drop missing values
    gdf = gdf.dropna()

    # Assert data not empty
    assert not gdf.empty

    # Convert datatypes
    gdf[["stop_id", "routes"]] = gdf[["stop_id", "routes"]].astype("string")

    # Assert that each stop is unique
    assert len(gdf["stop_id"].unique()) == len(gdf)

    # Assert valid geometry
    assert gdf.is_valid.all()

    # Set CRS to NAD83 (EPSG:4269)
    if gdf.crs is None:
        gdf = gdf.set_crs(na_crs)
    else:
        gdf = gdf.to_crs(na_crs)

    # Export cleaned
    utils.export_clean(gdf, "ac_stops.geojson")


def clean_ca_block_population():

    # Load data
    gdf = gpd.read_file(
        utils.raw_dir("tl_2020_06_tabblock20.zip")
    )

    # Rename columns
    gdf = gdf.rename(columns={
        "TRACTCE20": "tract",
        "POP20": "population",
    })

    # Select relevant columns
    gdf = gdf[["tract", "population", "geometry"]]

    # Convert datatypes
    gdf["tract"] = gdf["tract"].astype("string")
    gdf["population"] = gdf["population"].astype("int")

    # Assert no missing population
    assert gdf["population"].isna().sum() == 0

    # Assert summed pop equals actual census pop in 2020
    assert gdf["population"].sum() == 39538223

    # Assert valid geometry
    assert gdf.is_valid.all()

    # Assert CRS by default is Census NAD83 (EPSG:4269)
    assert gdf.crs is not None
    assert gdf.crs.to_epsg() == na_crs

    # Export cleaned
    utils.export_clean(gdf, "ca_block_population.geojson")


def clean_vehicle_ownership():

    # Load data
    df = pd.read_csv(
        utils.raw_dir("vehicle_ownership_2026-01-04.csv")
    )

    # Rename columns
    df = df.rename(columns={
        "B08201_001E": "households",
        "B08201_002E": "zero_vehicle_households"
    })

    # Convert datatypes
    df[["households", "zero_vehicle_households"]] = df[[
        "households", "zero_vehicle_households"]].astype("int")

    # Select relevant columns
    df = df[["tract", "households", "zero_vehicle_households"]]

    # Export cleaned
    df.to_csv(
        utils.clean_dir("vehicle_ownership.csv"),
        index=False
    )


def clean_college_population():

    # Load data
    df = pd.read_csv(
        utils.raw_dir("college_population_2026-01-04.csv")
    )

    # Rename columns
    df = df.rename(columns={
        "B14001_008E": "undergrad_pop",
        "B14001_009E": "grad_pop"
    })

    # Convert datatypes
    df = df.astype({"undergrad_pop": "int", "grad_pop": "int"})

    # Select relevant columns
    df = df[["tract", "undergrad_pop", "grad_pop"]]

    # Export cleaned
    df.to_csv(
        utils.clean_dir("college_population.csv"),
        index=False
    )


if __name__ == "__main__":
    # Clean ingested data
    # clean_ca_tracts()
    # clean_berkeley_boundary()
    # clean_ac_stops()
    # clean_ca_block_population()
    # clean_vehicle_ownership()
    clean_college_population()
