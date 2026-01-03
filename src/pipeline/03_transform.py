import geopandas as gpd
import utils


def berkeley_tracts():
    ca_tracts = gpd.read_file(utils.clean_dir("ca_tracts.geojson"))
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    assert ca_tracts.crs == berkeley_boundary.crs

    
    


berkeley_tracts()
