import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point
import numpy as np
import utils
import json


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
    berkeley_stops = berkeley_stops.drop(columns=["index_right"])

    # Reset index
    berkeley_stops = berkeley_stops.reset_index(drop=True)

    # Export berkeley bus stops
    utils.export_clean(berkeley_stops, "berkeley_stops.geojson")


def coverage():

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
    assert coverage.crs == berkeley_boundary.crs

    # Clip polygon to the Berkeley land boundary
    coverage = gpd.clip(coverage, berkeley_boundary)

    # Export coverage polygon
    utils.export_clean(coverage, "coverage.geojson")


def tract_population_covered():

    # Load data
    ca_block_population = gpd.read_file(
        utils.clean_dir("ca_block_population.geojson")
    )
    berkeley_tracts = gpd.read_file(
        utils.clean_dir("berkeley_tracts.geojson")
    )
    coverage = gpd.read_file(
        utils.clean_dir("coverage.geojson")
    )
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    # Convert datatypes
    ca_block_population["tract"] = ca_block_population["tract"].astype(
        "string")
    berkeley_tracts["tract"] = berkeley_tracts["tract"].astype("string")

    # Filter blocks by Berkeley tracts
    berkeley_block_population = ca_block_population[
        ca_block_population["tract"].isin(berkeley_tracts["tract"])
    ]

    # Assert summed pop equals actual census pop in 2020
    assert berkeley_block_population["population"].sum() == 124321

    # Assert CRS matches
    assert berkeley_block_population.crs == berkeley_boundary.crs

    # Clip non-land blocks with Berkeley land boundary
    berkeley_block_population = gpd.clip(
        berkeley_block_population, berkeley_boundary)

    # Project geometries for area calculations
    berkeley_block_population = berkeley_block_population.to_crs(epsg=3310)
    coverage = coverage.to_crs(epsg=3310).geometry.iloc[0]

    # Area per block
    area_block = berkeley_block_population.geometry.area

    # Intersect each block with coverage polygon
    area_overlap = berkeley_block_population.geometry.intersection(
        coverage).area

    # Per block area coverage
    area_ratio = area_overlap / area_block

    # Block level population coverage
    berkeley_block_population["population_covered"] = berkeley_block_population["population"] * area_ratio

    # Aggregate to tract level population coverage
    tract_population_covered = berkeley_block_population.groupby(
        ["tract"])[["population", "population_covered"]].sum()
    tract_population_covered = tract_population_covered.reset_index()

    # Select Relevant Columns
    tract_population_covered = tract_population_covered[[
        "tract", "population", "population_covered"]]

    tract_population_covered.to_csv(
        utils.clean_dir("tract_population_covered.csv"),
        index=False
    )


def scheduled_arrivals():

    # Maps an hour to a time block
    def time_block(hour):
        if 5 <= hour <= 6:
            return "Early AM (5–6:59)"
        elif 7 <= hour <= 9:
            return "AM Peak (7–9:59)"
        elif 10 <= hour <= 14:
            return "Midday (10–14:59)"
        elif 15 <= hour <= 18:
            return "PM Peak (15–18:59)"
        elif 19 <= hour <= 21:
            return "Evening (19–21:59)"
        elif hour >= 22 or hour == 0:
            return "Late Night (22–0:59)"
        else:
            return "Overnight (1–4:59)"

    # Count hourly scheduled arrivals for a given route and bus stop
    def count_scheduled_arrivals(schedule, route, stop_id, hour):

        # Filter bus stops by route (e.g. "51B northbound, 51B southbound")
        routes = [
            x
            for x in schedule["Routes"]
            if x.get("RouteId") == route
        ]

        count = 0
        for r in routes:

            # Get all trips that start during that hour
            trips = [
                trip
                for trip in r["Trips"]
                if int(trip.get("StartTime")[:2]) == hour
            ]

            for trip in trips:
                arrivals = [
                    arrival
                    for arrival in trip["StopTimes"]
                    if int(arrival.get("StopTime")[11:13]) == hour
                    and arrival.get("StopId") == stop_id
                ]
                count += len(arrivals)

        return count

    # Load data
    berkeley_stops = gpd.read_file(
        utils.clean_dir("berkeley_stops.geojson")
    )
    with open(utils.raw_dir("schedule_2026-01-03.json"), "r") as file:
        data = json.load(file)

    # Convert datatypes
    berkeley_stops["stop_id"] = berkeley_stops["stop_id"].astype("string")
    berkeley_stops["routes"] = berkeley_stops["routes"].astype("string")
    berkeley_stops["tract"] = berkeley_stops["tract"].astype("string")

    # Split routes delimited by " "
    berkeley_stops["routes"] = berkeley_stops["routes"].str.split(" ")

    # Compute of bus arrivals per stop in Berkeley
    rows = []
    for _, stop in berkeley_stops.iterrows():
        stop_id = stop["stop_id"]
        routes = stop["routes"]

        for hour in range(24):
            arrivals = sum([
                count_scheduled_arrivals(
                    data,
                    route,
                    stop_id,
                    hour
                )
                for route in routes
            ])

            rows.append({
                "stop_id": stop_id,
                "arrivals": arrivals,
                "hour": hour
            })

    # Convert to dataframe
    arrivals = pd.DataFrame(rows)

    # Convert to geodataframe
    arrivals = arrivals.merge(berkeley_stops, on="stop_id")

    # Sanity check i.e. there are 24 observations per bus stop
    assert len(arrivals) / 24 == len(berkeley_stops)

    # Select relevant columns
    arrivals = arrivals[["tract", "arrivals", "hour"]]

    # Export hourly bus arrivals
    arrivals.groupby(["hour"])["arrivals"].sum().reset_index().to_csv(
        utils.clean_dir("hour_arrivals.csv"),
        index=False
    )

    # Convert datatype
    arrivals["time_block"] = arrivals["hour"].apply(time_block)
    arrivals["time_block"] = arrivals["time_block"].astype("string")

    # Export time_block bus arrivals
    arrivals.groupby(["time_block"])["arrivals"].sum().reset_index().to_csv(
        utils.clean_dir("time_block_arrivals.csv"),
        index=False
    )

    # Load data
    berkeley_tracts = gpd.read_file(
        utils.clean_dir("berkeley_tracts.geojson")
    )

    # Group arrivals by time block
    tract_time_block_arrivals = (
        arrivals
        .groupby(["tract", "time_block"])["arrivals"]
        .sum()
        .reset_index()
    )

    # Sanity check
    assert len(tract_time_block_arrivals) == len(
        tract_time_block_arrivals["time_block"].unique()) * len(berkeley_tracts)

    # Convert to geodataframe
    tract_time_block_arrivals = berkeley_tracts.merge(
        tract_time_block_arrivals, on="tract")

    # Load Data
    tract_population_covered = pd.read_csv(
        utils.clean_dir("tract_population_covered.csv")
    )

    tract_population_covered["tract"] = tract_population_covered["tract"].astype(
        "string")

    # Convert
    tract_time_block_arrivals = tract_time_block_arrivals.merge(
        tract_population_covered, on="tract")

    tract_time_block_arrivals["arrivals_per_1000_covered"] = tract_time_block_arrivals["arrivals"] / \
        tract_time_block_arrivals["population_covered"] * 1000

    utils.export_clean(tract_time_block_arrivals,
                       "tract_time_block_arrivals.geojson")


if __name__ == "__main__":
    berkeley_tracts()
    berkeley_stops()
    coverage()
    tract_population_covered()
    scheduled_arrivals()
