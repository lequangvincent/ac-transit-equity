from dotenv import load_dotenv
from datetime import date
from census import Census
from us import states
import geopandas as gpd
import pandas as pd
import requests
import utils
import json
import os

# For stamping the current date to each dataset
today = date.today().isoformat()


def ingest_berkeley_boundary():
    url = "https://data.cityofberkeley.info/resource/e3zv-nuhf.geojson"

    try:
        gdf = gpd.read_file(url)

        if gdf.empty:
            raise ValueError()

        gdf.to_file("berkeley_boundary.geojson", driver="GeoJSON")

    except Exception as e:
        raise e


def ingest_schedule():

    # AC Transit routes in Berkeley from output of transformation / exploration
    routes = ['FS', '6', '18', '7', '688', '604', 'E', '51B', '67', '36', '52', '802',
              '27', '605', '800', '12', '88', '72L', 'J', '72', '22', '72M', 'G', 'F', '851', '65']

    routes_param = ",".join(routes)
    api_key = os.getenv("AC_TRANSIT_API_KEY")
    url = f"https://api.actransit.org/transit/route/{routes_param}/schedule?token={api_key}&dayCode=Weekday&hasAllStops=True"

    response = requests.get(url, timeout=10)

    assert response.status_code == 200

    raw = response.json()

    with open(utils.raw_dir(f"schedule_{today}.json"), "w") as json_file:
        json.dump(raw, json_file, indent=4)


def ingest_vehicle_ownership():
    api_key = os.getenv("CENSUS_API_KEY")
    c = Census(api_key)

    # Berkeley tracts from output of transformation / exploration
    berkeley_tracts = ['982100', '422902', '422901', '421100', '421400', '421700',
                       '421800', '421900', '423700', '423800', '423901', '424001',
                       '422500', '422700', '423000', '423100', '424002', '423300',
                       '423400', '423500', '423602', '422000', '421200', '422800',
                       '421300', '423200', '423902', '421500', '421600', '423601',
                       '422100', '422200', '422300', '422400']

    df = pd.DataFrame(
        c.acs5.state_county_tract(
            fields=[
                "B08201_001E",  # total households
                "B08201_002E",  # zero-vehicle households
            ],
            state_fips="06",
            county_fips="001",
            tract=",".join(berkeley_tracts),
            year=2020
        )
    )

    df.to_csv(utils.raw_dir(f"vehicle_ownership_{today}.csv"))


def ingest_college_population():
    api_key = os.getenv("CENSUS_API_KEY")
    c = Census(api_key)

    # Berkeley tracts from output of transformation / exploration
    berkeley_tracts = ['982100', '422902', '422901', '421100', '421400', '421700',
                       '421800', '421900', '423700', '423800', '423901', '424001',
                       '422500', '422700', '423000', '423100', '424002', '423300',
                       '423400', '423500', '423602', '422000', '421200', '422800',
                       '421300', '423200', '423902', '421500', '421600', '423601',
                       '422100', '422200', '422300', '422400']

    df = pd.DataFrame(
        c.acs5.state_county_tract(
            fields=[
                "B14001_008E",  # population enrolled in college (undergrad)
                "B14001_009E"  # population enrolled in college (grad)
            ],
            state_fips="06",
            county_fips="001",
            tract=",".join(berkeley_tracts),
            year=2020
        )
    )

    df.to_csv(utils.raw_dir(f"college_population_{today}.csv"))


if __name__ == "__main__":

    # Create directories
    output_dir = "../data/raw"
    os.makedirs(output_dir, exist_ok=True)

    # Load .env file
    load_dotenv(dotenv_path="../../.env")

    # Ingest data
    # ingest_schedule()
    # ingest_vehicle_ownership()
    ingest_college_population()
