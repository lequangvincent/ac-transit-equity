from shapely.geometry import Point
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import utils
import json


def berkeley_tracts():

    # Load Alameda tracts and Berkeley land boundary
    alameda_tracts = gpd.read_file(utils.clean_dir("alameda_tracts.geojson"))
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

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

    # Drop right index column to sjoin again
    berkeley_points = berkeley_points.drop(columns=["index_right"])

    # Map representative points back to polygons
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

    # Load AC Transit stops and Berkeley tracts
    ac_stops = gpd.read_file(utils.clean_dir("ac_stops.geojson"))
    berkeley_tracts = gpd.read_file(utils.clean_dir("berkeley_tracts.geojson"))

    # Spatially filter AC Transit stops in Berkeley
    berkeley_stops = gpd.sjoin(
        ac_stops,
        berkeley_tracts,
        how="inner",
        predicate="intersects"
    )

    # Drop right index column
    berkeley_stops = berkeley_stops.drop(columns=["index_right"])

    # Reset index
    berkeley_stops = berkeley_stops.reset_index(drop=True)

    # Export berkeley bus stops
    utils.export_clean(berkeley_stops, "berkeley_stops.geojson")


def coverage():

    # Set isochrone parameters
    distance = 500  # meters
    speed = 5  # kph
    time = distance / 1000 / speed * 60  # minutes

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

    # Project stops to meters
    projected_stops = ox.projection.project_gdf(
        berkeley_stops, to_crs=G.graph["crs"])["geometry"]

    # Snap stops to nearest node on graph
    nodes = ox.distance.nearest_nodes(
        G,
        X=projected_stops.x,
        Y=projected_stops.y
    )

    # Generate isochrones for each node
    isochrones = []
    for node in set(nodes):

        # Create subgraph of reachable nodes
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

    # Turn list of isochrones into a geodataframe
    isochrones = gpd.GeoDataFrame(geometry=isochrones, crs=G.graph["crs"])

    # Project CRS
    isochrones = isochrones.to_crs(berkeley_stops.crs)

    # Merge isochrones into a single polygon
    coverage = gpd.GeoDataFrame(
        geometry=[isochrones.union_all()], crs=berkeley_stops.crs)

    # Load Berkeley land boundary
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    # Clip coverage polygon to the Berkeley land boundary
    coverage = gpd.clip(coverage, berkeley_boundary)

    # Export coverage polygon
    utils.export_clean(coverage, "coverage.geojson")


def tract_population_covered():

    # Load CA block population and Berkeley tracts
    ca_block_population = gpd.read_file(
        utils.clean_dir("ca_block_population.geojson")
    )
    berkeley_tracts = gpd.read_file(
        utils.clean_dir("berkeley_tracts.geojson")
    )

    # Convert datatypes
    ca_block_population["tract"] = ca_block_population["tract"].astype(
        "string")
    berkeley_tracts["tract"] = berkeley_tracts["tract"].astype("string")

    # Filter CA blocks by Berkeley tracts
    berkeley_block_population = ca_block_population[
        ca_block_population["tract"].isin(berkeley_tracts["tract"])
    ]

    # Assert summed popualation equals official Census population in 2020
    assert berkeley_block_population["population"].sum() == 124321

    # Load coverage polygon and Berkeley land boundary
    coverage = gpd.read_file(
        utils.clean_dir("coverage.geojson")
    )
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    # Clip non-land blocks with boundary
    berkeley_block_population = gpd.clip(
        berkeley_block_population, berkeley_boundary)

    # Project CRS for area calculations
    berkeley_block_population = berkeley_block_population.to_crs(epsg=3310)
    coverage = coverage.to_crs(epsg=3310).geometry.iloc[0]

    # Compute area per block
    area_block = berkeley_block_population.geometry.area

    # Intersect each block with coverage polygon
    area_overlap = berkeley_block_population.geometry.intersection(
        coverage).area

    # Compute area coverage ratio
    area_ratio = area_overlap / area_block

    # Compute area-weighted estimate of population covered
    berkeley_block_population["population_covered"] = berkeley_block_population["population"] * area_ratio

    # Aggregate to tract level population coverage
    tract_population_covered = berkeley_block_population.groupby(
        ["tract"])[["population", "population_covered"]].sum().reset_index()

    # Select relevant columns
    tract_population_covered = tract_population_covered[[
        "tract", "population", "population_covered"]]

    # Export population covered in per tract
    tract_population_covered.to_csv(
        utils.clean_dir("tract_population_covered.csv"),
        index=False
    )


def scheduled_arrivals():

    # Helper: Map an hour to a time block
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

    time_block_duration = {
        "Early AM (5–6:59)": 2,
        "AM Peak (7–9:59)": 3,
        "Midday (10–14:59)": 5,
        "PM Peak (15–18:59)": 4,
        "Evening (19–21:59)": 3,
        "Late Night (22–0:59)": 3,
        "Overnight (1–4:59)": 4,
    }

    # Helper: Count hourly scheduled arrivals for a given route and bus stop
    def count_scheduled_arrivals(schedule, route, stop_id, hour):

        # Filter a stop by its route (e.g. route=51b then [51B northbound, 51B southbound])
        routes = [
            x
            for x in schedule["Routes"]
            if x.get("RouteId") == route
        ]

        count = 0
        for r in routes:

            # Scheduled bus departures within the hour
            trips = [
                trip
                for trip in r["Trips"]
                if int(trip.get("StartTime")[:2]) == hour
            ]

            # Count the times a bus reaches that stop
            for trip in trips:
                arrivals = [
                    arrival
                    for arrival in trip["StopTimes"]
                    if int(arrival.get("StopTime")[11:13]) == hour
                    and arrival.get("StopId") == stop_id
                ]
                count += len(arrivals)

        return count

    # Load Berkeley stops and weekday bus schedule
    berkeley_stops = gpd.read_file(
        utils.clean_dir("berkeley_stops.geojson")
    )
    with open(utils.raw_dir("schedule_2026-01-03.json"), "r") as file:
        data = json.load(file)

    # Convert datatypes
    berkeley_stops[["stop_id", "routes", "tract"]] = berkeley_stops[[
        "stop_id", "routes", "tract"]].astype("string")

    # Split routes delimited by " "
    berkeley_stops["routes"] = berkeley_stops["routes"].str.split(" ")

    # Compute of bus arrivals per stop in Berkeley
    observations = []
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

            observations.append({
                "stop_id": stop_id,
                "hour": hour,
                "arrivals": arrivals
            })

    # Convert observations to dataframe
    arrivals = pd.DataFrame(observations)

    # Merge on stop_id to get tracts
    arrivals = arrivals.merge(berkeley_stops, on="stop_id")

    # Sanity check i.e. there are 24 observations per bus stop
    assert len(arrivals) / 24 == len(berkeley_stops)

    # Export bus arrivals by hour
    arrivals.groupby(["hour"])["arrivals"].sum().reset_index().to_csv(
        utils.clean_dir("hourly_arrivals.csv"),
        index=False
    )

    # Map hour to time block
    arrivals["time_block"] = arrivals["hour"].apply(
        time_block).astype("string")

    temp = arrivals.copy()

    # Export bus arrivals by time block
    temp = temp.groupby(["time_block"])["arrivals"].sum().reset_index()

    temp["time_block_duration"] = temp["time_block"].map(
        time_block_duration)
    temp["average_arrivals"] = temp["arrivals"] / \
        temp["time_block_duration"]
    temp["average_arrivals"].drop(
        columns=["time_block_duration"])

    temp.to_csv(
        utils.clean_dir("time_block_arrivals.csv"),
        index=False
    )

    # Sum arrivals by tract and time block
    arrivals["tract"] = arrivals["tract"].astype("string")
    tract_time_block_arrivals = (
        arrivals
        .groupby(["tract", "time_block"])["arrivals"]
        .sum()
        .reset_index()
    )

    # Load Berkeley tracts
    berkeley_tracts = gpd.read_file(
        utils.clean_dir("berkeley_tracts.geojson")
    )

    # Convert datatype
    berkeley_tracts["tract"] = berkeley_tracts["tract"].astype("string")

    # Sanity check
    assert len(tract_time_block_arrivals) == len(
        tract_time_block_arrivals["time_block"].unique()) * len(berkeley_tracts)

    # Merge on tract to get geometry
    tract_time_block_arrivals = berkeley_tracts.merge(
        tract_time_block_arrivals, on="tract")

    # Load the population covered per tract
    tract_population_covered = pd.read_csv(
        utils.clean_dir("tract_population_covered.csv")
    )

    tract_time_block_arrivals["time_block_duration"] = tract_time_block_arrivals["time_block"].map(
        time_block_duration)
    tract_time_block_arrivals["average_arrivals"] = tract_time_block_arrivals["arrivals"] / \
        tract_time_block_arrivals["time_block_duration"]
    tract_time_block_arrivals["average_arrivals"].drop(
        columns=["time_block_duration"])

    # Convert datatype
    tract_population_covered["tract"] = tract_population_covered["tract"].astype(
        "string")

    # Merge on tract to get population and population covered
    tract_time_block_arrivals = tract_time_block_arrivals.merge(
        tract_population_covered, on="tract")

    # Compute bus arrivals per 1000 per tract per time block
    tract_time_block_arrivals["average_arrivals_per_1000_covered"] = tract_time_block_arrivals["average_arrivals"] / \
        tract_time_block_arrivals["population_covered"] * 1000

    # Export tract-level arrivals per 1,000 covered residents by time block
    utils.export_clean(tract_time_block_arrivals,
                       "tract_time_block_arrivals.geojson")


def tract_midday_arrivals():

    # Load bus arrivals per tract by time block
    tract_time_block_arrivals = gpd.read_file(
        utils.clean_dir("tract_time_block_arrivals.geojson")
    )

    # Convert data types
    tract_time_block_arrivals[["time_block", "tract"]] = tract_time_block_arrivals[["time_block", "tract"]].astype(
        "string")
    tract_time_block_arrivals["arrivals_per_1000_covered"] = tract_time_block_arrivals["arrivals_per_1000_covered"].astype(
        "float")

    # Filter for Midday arrivals
    tract_midday_arrivals = tract_time_block_arrivals[
        tract_time_block_arrivals["time_block"] == "Midday (10–14:59)"]

    tract_midday_arrivals = tract_midday_arrivals.drop(
        columns=["time_block"])

    # Compute population coverage ratio
    tract_midday_arrivals["coverage_ratio"] = tract_midday_arrivals["population_covered"] / \
        tract_midday_arrivals["population"] * 100

    # Remove outliers within this time block
    Q1 = tract_midday_arrivals["arrivals_per_1000_covered"].quantile(0.25)
    Q3 = tract_midday_arrivals["arrivals_per_1000_covered"].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    outliers = tract_midday_arrivals[(tract_midday_arrivals["arrivals_per_1000_covered"] < lower_bound) |
                                     (tract_midday_arrivals["arrivals_per_1000_covered"] > upper_bound)]

    print(outliers)

    filtered = tract_midday_arrivals[tract_midday_arrivals["tract"] != "982100"].reset_index(
        drop=True)

    # Bottom 25% or top 75% arrivals per 1000 covered
    q25 = filtered["arrivals_per_1000_covered"].quantile(0.25)
    filtered["arrivals_covered_percentile"] = (
        filtered["arrivals_per_1000_covered"]
        .le(q25)
        .map({True: "Bottom 25%", False: "Top 75%"})
    )

    # Sort by arrivals_per_1000_covered
    filtered = filtered.sort_values(
        "arrivals_per_1000_covered", ascending=False).reset_index(drop=True)

    # Load vehicle ownership data
    vehicle_ownership = pd.read_csv(
        utils.clean_dir("vehicle_ownership.csv")
    )

    # Convert data types
    vehicle_ownership["zero_vehicle_households"] = vehicle_ownership["zero_vehicle_households"].astype(
        "float")
    vehicle_ownership["households"] = vehicle_ownership["households"].astype(
        "int")
    vehicle_ownership["tract"] = vehicle_ownership["tract"].astype("string")

    # Compute % zero vehicle households
    vehicle_ownership["%_no_vehicle_households"] = vehicle_ownership["zero_vehicle_households"] / \
        vehicle_ownership["households"] * 100

    # Merge vechile ownership with filtered
    filtered = filtered.merge(
        vehicle_ownership, on="tract")

    # Bottom 25% or top 75% of % zero vehicle households
    q75 = filtered["%_no_vehicle_households"].quantile(
        0.75)
    filtered["no_vehicle_percentile"] = (
        filtered["%_no_vehicle_households"]
        .le(q75)
        .map({False: "Bottom 25%", True: "Top 75%"})
    )

    # See who is bottom 25% in arrivals and bottom 25% in no vehicle households
    bottom = filtered[(filtered["arrivals_covered_percentile"] == "Bottom 25%") & (
        filtered["no_vehicle_percentile"] == "Bottom 25%")]

    print(bottom)

    # Load college population
    college_population = pd.read_csv(
        utils.clean_dir("college_population.csv")
    )

    # Convert data types
    college_population["undergrad_pop"] = college_population["undergrad_pop"].astype(
        "int")
    college_population["grad_pop"] = college_population["grad_pop"].astype(
        "int")
    college_population["tract"] = college_population["tract"].astype("string")

    # Merge college population
    filtered = filtered.merge(
        college_population, on="tract")

    # Compute ratio of student population in a tract
    filtered["student_pop_ratio"] = (
        filtered["grad_pop"] + filtered["undergrad_pop"]) / filtered["population"] * 100

    # Select relevant columns
    filtered = filtered[[
        "tract",
        "population",
        "student_pop_ratio",
        "population_covered",
        "coverage_ratio",
        "arrivals",
        "arrivals_per_1000_covered",
        "arrivals_covered_percentile",
        "%_no_vehicle_households",
        "no_vehicle_percentile",
        "geometry"
    ]]

    # Tracts with a student_pop_ratio over 50 is considered dominant
    students = filtered[filtered["student_pop_ratio"]
                        > 50].reset_index(drop=True)
    non_students = filtered[filtered["student_pop_ratio"]
                            <= 50].reset_index(drop=True)

    # Recompute percentiles for non_students
    q25 = non_students["arrivals_per_1000_covered"].quantile(0.25)
    non_students["arrivals_covered_percentile"] = (
        non_students["arrivals_per_1000_covered"]
        .le(q25)
        .map({True: "Bottom 25%", False: "Top 75%"})
    )

    # Recompute percentiles for non_student dataset
    q75 = non_students["%_no_vehicle_households"].quantile(
        0.75)
    non_students["no_vehicle_percentile"] = (
        non_students["%_no_vehicle_households"]
        .le(q75)
        .map({False: "Bottom 25%", True: "Top 75%"})
    )

    utils.export_clean(students.drop(columns=[
                       "arrivals_covered_percentile", "no_vehicle_percentile"]), "midday_students.geojson")

    utils.export_clean(non_students, "midday_non_students.geojson")


def tract_peak_arrivals():

    # Load vehicle ownership data
    vehicle_ownership = pd.read_csv(
        utils.clean_dir("vehicle_ownership.csv")
    )

    # Convert data types
    vehicle_ownership["zero_vehicle_households"] = vehicle_ownership["zero_vehicle_households"].astype(
        "float")
    vehicle_ownership["households"] = vehicle_ownership["households"].astype(
        "int")
    vehicle_ownership["tract"] = vehicle_ownership["tract"].astype("string")

    # Compute % zero vehicle households
    vehicle_ownership["%_no_vehicle_households"] = vehicle_ownership["zero_vehicle_households"] / \
        vehicle_ownership["households"] * 100

    # Load tract_block_time arrivals
    tract_time_block_arrivals = gpd.read_file(
        utils.clean_dir("tract_time_block_arrivals.geojson")
    )

    # Convert data types
    tract_time_block_arrivals[["tract", "time_block"]] = tract_time_block_arrivals[[
        "tract", "time_block"]].astype("string")
    tract_time_block_arrivals["average_arrivals"] = tract_time_block_arrivals["average_arrivals"].astype(
        "float")

    # # Filter for AM & PM peaks
    tract_time_block_arrivals = tract_time_block_arrivals[(tract_time_block_arrivals["time_block"] == "AM Peak (7–9:59)") | (
        tract_time_block_arrivals["time_block"] == "PM Peak (15–18:59)")]

    # Groupby tract + time block and sum on the average_arrivals
    peak_time_block_arrivals = tract_time_block_arrivals.groupby(
        ["tract", "time_block"])[["average_arrivals"]].sum().reset_index()

    # Merge zero vehicle households
    peak_time_block_arrivals = peak_time_block_arrivals.merge(
        vehicle_ownership, on="tract")

    # Load berkeley tracts for geometry
    berkeley_tracts = gpd.read_file(
        utils.clean_dir("berkeley_tracts.geojson")
    )

    # Convert datatypes
    berkeley_tracts["tract"] = berkeley_tracts["tract"].astype("string")

    # Merge geometry
    peak_time_block_arrivals = berkeley_tracts.merge(
        peak_time_block_arrivals, on="tract")

    # Load tract population
    tract_population_covered = pd.read_csv(
        utils.clean_dir("tract_population_covered.csv")
    )

    # Convert datatypes
    tract_population_covered["tract"] = tract_population_covered["tract"].astype(
        "string")
    tract_population_covered["population_covered"] = tract_population_covered["population_covered"].astype(
        "float")

    # Merge peak time block arrivals with population covered
    peak_time_block_arrivals = peak_time_block_arrivals.merge(
        tract_population_covered, on="tract")

    # Normalize average arrivals
    peak_time_block_arrivals["average_arrivals_normalized"] = peak_time_block_arrivals["average_arrivals"] / \
        peak_time_block_arrivals["population_covered"] * 1000

    # Export
    utils.export_clean(peak_time_block_arrivals,
                       "peak_time_block_arrivals.geojson")


def main():
    berkeley_tracts()
    berkeley_stops()
    coverage()
    tract_population_covered()
    scheduled_arrivals()
    # tract_midday_arrivals()
    tract_peak_arrivals()


if __name__ == "__main__":
    main()
