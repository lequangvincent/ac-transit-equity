import geopandas as gpd
import numpy as np
import utils


def coverage_ratio():

    # Load data
    blocks = gpd.read_file(
        utils.clean_dir("berkeley_block_pop.geojson")
    )
    coverage_poly = gpd.read_file(
        utils.clean_dir("coverage.geojson")
    )
    berkeley_boundary = gpd.read_file(
        utils.clean_dir("berkeley_boundary.geojson")
    )

    # Assert CRS matches (EPSG:4269)
    assert coverage_poly.crs == berkeley_boundary.crs == 4269

    # Clip non-land blocks with Berkeley land boundary
    blocks = gpd.clip(blocks, berkeley_boundary)

    # Project geometries for area calculations
    blocks = blocks.to_crs(epsg=3310)
    coverage_poly = coverage_poly.to_crs(epsg=3310).geometry.iloc[0]

    # Area per block
    area_block = blocks.geometry.area

    # Intersect each block with coverage polygon
    area_overlap = blocks.geometry.intersection(coverage_poly).area

    # Per block area coverage
    area_ratio = area_overlap / area_block

    # Per block population coverage
    blocks["population_covered"] = blocks["population"] * area_ratio

    # City-wide population coverage ratio
    total_covered = blocks["population_covered"].sum()
    total_population = blocks["population"].sum()
    coverage_ratio = total_covered / total_population

    # Print metrics
    print("\nCoverage Metrics")
    print("-" * 40)
    print(f"Covered Population: {int(total_covered)}")
    print(f"Total Population: {total_population}")
    print(
        f"Population Coverage Ratio: {np.round(coverage_ratio * 100, 1)}%\n\n"
    )


coverage_ratio()
