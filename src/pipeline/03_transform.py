import geopandas as gpd
import utils


def berkeley_tracts():
    alameda_tracts = gpd.read_file(utils.clean_dir("alameda_tracts.geojson"))
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    assert alameda_tracts.crs == berkeley_boundary.crs

    # Filter representative points within berkeley_boundary
    alameda_points = gpd.GeoDataFrame(
        geometry=alameda_tracts.representative_point()
    )
    berkeley_points = gpd.sjoin(
        alameda_points,
        berkeley_boundary,
        how="inner",
        predicate="intersects"
    )

    berkeley_points = berkeley_points.drop(columns=["index_right"])

    # Use filtered representative points to filter alameda_tracts
    berkeley_tracts = gpd.sjoin(
        alameda_tracts,
        berkeley_points,
        how="inner",
        predicate="intersects"
    )

    berkeley_tracts = berkeley_tracts.reset_index(drop=True)
    berkeley_tracts = berkeley_tracts[["tract", "geometry"]]

    # Export berkeley_tracts
    utils.export_clean(berkeley_tracts, "berkeley_tracts.geojson")


def berkeley_stops():
    # Load data
    ac_stops = gpd.read_file(utils.clean_dir("ac_stops.geojson"))
    berkeley_tracts = gpd.read_file(utils.clean_dir("berkeley_tracts.geojson"))

    assert ac_stops.crs == berkeley_tracts.crs

    # Spatial join to filter for berkeley bus stops
    berkeley_stops = gpd.sjoin(
        ac_stops,
        berkeley_tracts,
        how="inner",
        predicate="intersects"
    )

    # Drop index right column
    berkeley_stops = berkeley_stops.drop("index_right", axis=1)

    # Reset index
    berkeley_stops = berkeley_stops.reset_index(drop=True)

    # Export berkeley bus stops
    utils.export_clean(berkeley_stops, "berkeley_stops.geojson")


