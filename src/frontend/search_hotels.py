from typing import Any, Dict, List

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


def get_connection_settings() -> Dict[str, str]:
    return {
        "endpoint": st.session_state.get("gql_endpoint", ""),
        "api_key": st.session_state.get("api_key", ""),
    }


def validate_required(settings: Dict[str, str]) -> List[str]:
    labels = {
        "endpoint": "GraphQL Endpoint",
        "api_key": "GraphQL API Key",
    }
    return [labels[k] for k, v in settings.items() if not v]


def build_query() -> str:
    return (
        "query ListHotelsNearAirport($airportName: String!, $withinKm: Int!) {\n"
        "  listHotelsNearAirport(airportName: $airportName, withinKm: $withinKm) {\n"
        "    hotels {\n"
        "      id\n"
        "      name\n"
        "      address\n"
        "      city\n"
        "      country\n"
        "      phone\n"
        "      price\n"
        "      url\n"
        "      geo { lat lon }\n"
        "      reviews { ratings { Overall } }\n"
        "    }\n"
        "    airport {\n"
        "      name\n"
        "      location {\n"
        "        lat\n"
        "        lon\n"
        "        accuracy\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    )


def build_variables(settings: Dict[str, str], airport_name: str, within_km: int) -> Dict[str, Any]:
    return {
        "airportName": airport_name,
        "withinKm": within_km,
    }


def fetch_hotels(endpoint: str, api_key: str, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"x-api-key": api_key} if api_key else {}
    resp = requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)
    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(str(payload["errors"]))
    result = payload.get("data", {}).get("listHotelsNearAirport", {})
    return {
        "hotels": result.get("hotels", []),
        "airport": result.get("airport")
    }


def compute_rating_from_reviews(hotel: Dict[str, Any]) -> float:
    reviews = hotel.get("reviews") or []
    overall_values: List[float] = []
    for review in reviews:
        ratings = (review or {}).get("ratings") or {}
        overall = ratings.get("Overall")
        if isinstance(overall, (int, float)):
            overall_values.append(float(overall))
    avg_overall = sum(overall_values) / len(overall_values) if overall_values else None
    return (avg_overall * 2.0) if avg_overall is not None else 0.0


def color_from_rating(rating_out_of_10: float) -> List[int]:
    normalized = max(0.0, min(1.0, rating_out_of_10 / 10.0))
    red = int(255 * (1.0 - normalized))
    green = int(200 * normalized + 30 * (1 - normalized))
    blue = 40
    return [red, green, blue, 200]


def hotels_to_points(hotels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for hotel in hotels:
        geo = hotel.get("geo") or {}
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is None or lon is None:
            continue
        rating = compute_rating_from_reviews(hotel)
        color = color_from_rating(rating)
        # Format tooltip content with hotel details
        details = (
            f"<br/><div style='margin-top: 5px;'>"
            f"<b>Rating:</b> {rating:.1f}/10<br/>"
            f"<b>Address:</b> {hotel.get('address', '')}<br/>"
            f"<b>City:</b> {hotel.get('city', '')}<br/>"
            f"<b>Country:</b> {hotel.get('country', '')}<br/>"
            f"<b>Price:</b> {hotel.get('price', '')}<br/>"
            f"<b>Phone:</b> {hotel.get('phone', '')}<br/>"
            f"<b>Website:</b> {hotel.get('url', '')}"
            f"</div>"
        )
        points.append(
            {
                "name": hotel.get("name", ""),
                "details": details,
                "lat": float(lat),
                "lon": float(lon),
                "color": color,
            }
        )
    return points


def get_map_style() -> str:
    token = st.session_state.get("mapbox_token", "")
    if token:
        # If user provides a Mapbox token, use Mapbox light style
        try:
            pdk.settings.mapbox_api_key = token
        except Exception as e:
            st.warning(f"Failed to apply Mapbox token: {e}")
        return "mapbox://styles/mapbox/light-v10"
    # Tokenless Carto basemap
    return "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"


def build_map(df_hotels: pd.DataFrame, airport: Dict[str, Any]) -> pdk.Deck:
    layers = []
    
    # Hotel markers layer with detailed tooltip
    hotel_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_hotels,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius=8,
        radius_units="meters",
        radius_min_pixels=4,
        radius_max_pixels=20,
        pickable=True,
        auto_highlight=True,
    )
    layers.append(hotel_layer)
    
    # Airport marker layer (if airport is available)
    if airport and airport.get("location"):
        airport_location = airport["location"]
        df_airport = pd.DataFrame([{
            "name": airport.get("name", "Airport"),
            "lat": airport_location["lat"],
            "lon": airport_location["lon"],
            "color": [255, 165, 0, 255],  # Orange color for airport
            "details": "",  # No details for airport
        }])
        
        airport_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_airport,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=15,  # Larger radius for airport
            radius_units="meters",
            radius_min_pixels=10,
            radius_max_pixels=40,
            pickable=True,
            auto_highlight=True,
            get_line_color=[255, 255, 255, 255],  # White outline
            line_width_min_pixels=2,
            stroked=True,
        )
        layers.append(airport_layer)
    
    # Calculate bounding box to show all markers (hotels + airport)
    all_lats = list(df_hotels["lat"])
    all_lons = list(df_hotels["lon"])
    
    if airport and airport.get("location"):
        airport_location = airport["location"]
        all_lats.append(float(airport_location["lat"]))
        all_lons.append(float(airport_location["lon"]))
    
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    
    # Calculate zoom level based on bounding box
    lat_range = max(all_lats) - min(all_lats)
    lon_range = max(all_lons) - min(all_lons)
    max_range = max(lat_range, lon_range)
    
    # Estimate zoom level (rough approximation)
    if max_range > 1.0:
        zoom = 8
    elif max_range > 0.5:
        zoom = 9
    elif max_range > 0.2:
        zoom = 10
    elif max_range > 0.1:
        zoom = 11
    else:
        zoom = 12
    
    view_state = pdk.ViewState(
        longitude=center_lon,
        latitude=center_lat,
        zoom=zoom,
        pitch=0,
        bearing=0,
    )
    
    # Tooltip shows name for all, details for hotels only
    tooltip = {
        "html": (
            "<div style='font-family: Arial, sans-serif;'>"
            "<b style='font-size: 14px;'>{name}</b>"
            "{details}"
            "</div>"
        ),
        "style": {"color": "white"},
    }
    
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=get_map_style(),
    )


def render():
    st.title("Search Hotels Near Airport")
    settings = get_connection_settings()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        airport_name = st.text_input("Airport Name", help="Enter the airport name to search near")
    with col2:
        within_km = st.number_input("Distance (km)", min_value=1, max_value=500, value=50, help="Search radius in kilometers")
    
    st.caption("Markers are colored by rating (0–10) derived from reviews.")

    if st.button("Search"):
        missing = validate_required(settings)
        if missing:
            st.error(f"Please fill the required connection settings: {', '.join(missing)}")
            return
        if not airport_name:
            st.error("Please enter an airport name")
            return
        try:
            result = fetch_hotels(
                endpoint=settings["endpoint"],
                api_key=settings["api_key"],
                query=build_query(),
                variables=build_variables(settings, airport_name, within_km),
            )
            hotels = result["hotels"]
            airport = result["airport"]
        except Exception as exc:  # noqa: BLE001
            st.error(f"GraphQL error: {exc}")
            return
        
        if not airport:
            st.error(f"Airport '{airport_name}' not found.")
            return
            
        if not hotels:
            st.warning(f"No hotels found within {within_km}km of {airport_name}.")
            return
            
        points = hotels_to_points(hotels)
        if not points:
            st.warning("No hotel coordinates to plot on the map.")
            return
            
        df = pd.DataFrame(points)
        
        deck = build_map(df, airport)
        st.pydeck_chart(deck)
        
        # Add legend
        st.markdown("""
        **Legend:**
        - 🟠 Orange marker: Airport location
        - 🔴 Red to 🟢 Green markers: Hotels (colored by rating, 0-10)
        """)
        
        with st.expander("Raw response"):
            st.json({"data": {"listHotelsNearAirport": {"hotels": hotels, "airport": airport}}})


if __name__ == "__main__":
    render()



