
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium

# Load data
st.title("🏠 Chicago Shared Housing Eligibility Checker")

@st.cache_data
def load_data():
    rrz_df = pd.read_csv("House_Share_Restricted_Residential_Zone_Precincts_20250629.csv")
    pbl_df = pd.read_csv("House_Share_Prohibited_Buildings_List_20250629.csv")
    precincts_df = pd.read_csv("Boundaries_-_Ward_Precincts__2023-__20250629.csv")
    precincts_df["geometry"] = precincts_df["the_geom"].apply(wkt_loads)
    precincts_gdf = gpd.GeoDataFrame(precincts_df, geometry="geometry", crs="EPSG:4326")
    return rrz_df, pbl_df, precincts_gdf

rrz_df, pbl_df, precincts_gdf = load_data()

# Create RRZ polygon set
rrz_pairs = set(zip(rrz_df["Ward"], rrz_df["Precinct"]))
rrz_gdf = precincts_gdf[precincts_gdf.apply(lambda row: (row["Ward"], row["Precinct"]) in rrz_pairs, axis=1)]

# Prepare prohibited buildings and small buildings sets
pbl_addresses = set(
    f"{str(row['Address Number']).strip()} {str(row['Street Direction']).strip()} {str(row['Street Name']).strip()} {str(row['Street Type']).strip()}".strip()
    for _, row in pbl_df.iterrows()
)

small_buildings_df = pbl_df[pbl_df["Number of Units"] <= 4]
small_building_addresses = set(
    f"{str(row['Address Number']).strip()} {str(row['Street Direction']).strip()} {str(row['Street Name']).strip()} {str(row['Street Type']).strip()}".strip()
    for _, row in small_buildings_df.iterrows()
)

# Search Box
address = st.text_input("Enter a Chicago address:", "")

# Checker logic
if address:
    geolocator = Nominatim(user_agent="shared_housing_checker_web")
    location = geolocator.geocode(address, timeout=10)
    if not location:
        st.error(f"❌ Address '{address}' could not be geocoded.")
    else:
        point = Point(location.longitude, location.latitude)
        in_rrz = any(row["geometry"].contains(point) for _, row in rrz_gdf.iterrows())
        in_pbl = any(addr.lower() in address.lower() for addr in pbl_addresses)
        in_small = any(addr.lower() in address.lower() for addr in small_building_addresses)

        if in_rrz:
            st.error("❌ Address is in a Restricted Residential Zone.")
        elif in_pbl:
            st.error("❌ Address matches a Prohibited Building.")
        elif in_small:
            st.error("❌ Address is ineligible due to building size (4 or fewer units).")
        else:
            st.success("✅ Address is eligible for shared housing registration.")

# Load map
st.subheader("🗺️ Map of Restricted Zones and Prohibited Buildings")
with open("Chicago_Shared_Housing_Updated_Map.html", "r") as f:
    map_html = f.read()

st.components.v1.html(map_html, height=700, scrolling=True)
