import pandas as pd
import numpy as np
import utils


def population_coverage_ratio():

    # Load data
    gdf = pd.read_csv(
        utils.clean_dir("tract_population_covered.csv")
    )

    population_covered = gdf["population_covered"].astype("float").sum()
    population_total = gdf["population"].astype("int").sum()
    coverage_ratio = np.round(population_covered / population_total * 100, 1)

    # Print metrics
    print("\nCoverage Metrics")
    print("-" * 40)
    print(f"Total Population: {population_total}")
    print(f"Covered Population: {int(np.round(population_covered))}")
    print(
        f"Population Coverage Ratio: {coverage_ratio}%\n\n"
    )


if __name__ == "__main__":
    population_coverage_ratio()
