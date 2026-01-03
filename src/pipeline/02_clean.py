import geopandas as gpd
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
    gdf = gdf.convert_dtypes()

    # Assert datatypes
    assert str(gdf["county"].dtype) == "string"
    assert str(gdf["tract"].dtype) == "string"
    assert str(gdf["geometry"].dtype) == "geometry"

    # Filter for Alameda county rows
    gdf = gdf[gdf["county"] == "001"]

    # Assert no duplicates
    assert len(gdf["tract"].unique()) == len(gdf)

    # Select relevant columns
    gdf = gdf[["tract", "geometry"]]

    # Reset index
    gdf = gdf.reset_index(drop=True)

    # Assert CRS by default is Census NAD83 (EPSG:4269)
    assert gdf.crs is not None
    assert gdf.crs.to_epsg() == na_crs

    # Assert valid geometries
    assert gdf.is_valid.all()

    # Export to GeoJSON
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

    # Export to GeoJSON
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

    # Assert datatypes
    assert str(gdf["stop_id"].dtype) == "string"
    assert str(gdf["routes"].dtype) == "string"
    assert str(gdf["geometry"].dtype) == "geometry"

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


clean_ca_tracts()
clean_berkeley_boundary()
clean_ac_stops()
