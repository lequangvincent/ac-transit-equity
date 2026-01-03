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
