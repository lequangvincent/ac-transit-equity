import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point
import utils


def berkeley_tracts():

    # Load data
    alameda_tracts = gpd.read_file(utils.clean_dir("alameda_tracts.geojson"))
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    # Assert CRS matches (EPSG:4269)
    assert alameda_tracts.crs == berkeley_boundary.crs

    # Create a representative point for each Alameda tract
    alameda_points = gpd.GeoDataFrame(
        geometry=alameda_tracts.representative_point()
    )

    # Spatially filter representative points within Berkeley boundary
    berkeley_points = gpd.sjoin(
        alameda_points,
        berkeley_boundary,
        how="inner",
        predicate="intersects"
    )

    # Drop right index to sjoin again
    berkeley_points = berkeley_points.drop(columns=["index_right"])

    # Match representative points back to corresponding polygons
    berkeley_tracts = gpd.sjoin(
        alameda_tracts,
        berkeley_points,
        how="inner",
        predicate="intersects"
    )

    # Reset index
    berkeley_tracts = berkeley_tracts.reset_index(drop=True)

    # Select relevant columns
    berkeley_tracts = berkeley_tracts[["tract", "geometry"]]

    # Export Berkeley census tracts
    utils.export_clean(berkeley_tracts, "berkeley_tracts.geojson")


def berkeley_stops():

    # Load data
    ac_stops = gpd.read_file(utils.clean_dir("ac_stops.geojson"))
    berkeley_tracts = gpd.read_file(utils.clean_dir("berkeley_tracts.geojson"))

    # Assert CRS matches (EPSG:4269)
    assert ac_stops.crs == berkeley_tracts.crs

    # Spatial filter AC Transit stops in Berkeley
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


def generate_coverage():

    # Isochrone Parameters
    distance = 500  # 500 meters
    speed = 5  # 5 kph
    time = distance / 1000 / speed * 60  # 6 minutes

    # Create Berkeley OSMnx graph
    G = ox.graph.graph_from_place(
        "Berkeley, California, USA", network_type="walk")

    # Project graph and set edge attributes
    G = ox.projection.project_graph(G)
    nx.set_edge_attributes(G, speed, "speed_kph")
    G = ox.routing.add_edge_travel_times(G)

    # Load Berkeley stops
    berkeley_stops = gpd.read_file(
        utils.clean_dir("berkeley_stops.geojson")
    )

    # Project Berkeley stops from coordiantes to meters
    projected_stops = ox.projection.project_gdf(
        berkeley_stops, to_crs=G.graph["crs"])["geometry"]

    # Snap bus stops to nearest node on graph
    nodes = ox.distance.nearest_nodes(
        G,
        X=projected_stops.x,
        Y=projected_stops.y
    )

    # Generate isochrones from each bus stop node
    isochrones = []
    for node in set(nodes):

        # Create subgraph of reachable nodes within 6 minutes
        subgraph = nx.ego_graph(G, node, radius=time, distance='time')
        reachable_nodes = [
            Point(data['x'], data['y'])
            for _, data
            in subgraph.nodes(data=True)
        ]

        # Create a polygon from all reachable nodes within the subgraph
        if reachable_nodes:
            polygon = gpd.GeoSeries(reachable_nodes).union_all().convex_hull
            isochrones.append(polygon)

    # Turn list of isochrone polygons into a geodataframe
    isochrones = gpd.GeoDataFrame(geometry=isochrones, crs=G.graph["crs"])

    # Set CRS to NAD83 (EPSG:4269)
    isochrones = isochrones.to_crs(berkeley_stops.crs)

    # Merge individual isochrones to a single polygon
    coverage = gpd.GeoDataFrame(
        geometry=[isochrones.union_all()], crs=berkeley_stops.crs)

    # Load Berkeley land boundary
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    # Assert CRS
    assert coverage.crs == berkeley_boundary.crs == 4269

    # Clip polygon to the Berkeley land boundary
    coverage = gpd.clip(coverage, berkeley_boundary)

    # Export coverage polygon
    utils.export_clean(coverage, "coverage.geojson")


def berkeley_block_pop():

    # Load data
    ca_block_population = gpd.read_file(
        utils.clean_dir("ca_block_population.geojson")
    )
    berkeley_tracts = gpd.read_file(
        utils.clean_dir("berkeley_tracts.geojson")
    )

    # Convert datatypes
    ca_block_population = ca_block_population.convert_dtypes()
    berkeley_tracts = berkeley_tracts.convert_dtypes()

    # Assert datatypes
    assert str(ca_block_population["tract"].dtype) == "string"
    assert str(berkeley_tracts["tract"].dtype) == "string"

    # Filter blocks by Berkeley tracts
    berkeley_block_population = ca_block_population[
        ca_block_population["tract"].isin(berkeley_tracts["tract"])
    ]

    # Assert summed pop equals actual census pop in 2020
    assert berkeley_block_population["population"].sum() == 124321

    # Export coverage polygon
    utils.export_clean(berkeley_block_population, "berkeley_block_pop.geojson")


berkeley_tracts()
berkeley_stops()
generate_coverage()
berkeley_block_pop()
