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


def build_variables(airport_name: str, within_km: int) -> Dict[str, Any]:
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
    overall_values = [
        float(review.get("ratings", {}).get("Overall"))
        for review in reviews
        if review and review.get("ratings", {}).get("Overall") is not None
    ]
    if not overall_values:
        return 0.0
    return (sum(overall_values) / len(overall_values)) * 2.0


def color_from_rating(rating_out_of_10: float) -> List[int]:
    normalized = max(0.0, min(1.0, rating_out_of_10 / 10.0))
    red = int(255 * (1.0 - normalized))
    green = int(200 * normalized + 30 * (1 - normalized))
    blue = 40
    return [red, green, blue, 200]


def hotels_to_points(hotels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points = []
    for hotel in hotels:
        geo = hotel.get("geo") or {}
        if not geo.get("lat") or not geo.get("lon"):
            continue
        
        rating = compute_rating_from_reviews(hotel)
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
        
        points.append({
            "name": hotel.get("name", ""),
            "details": details,
            "lat": float(geo["lat"]),
            "lon": float(geo["lon"]),
            "color": color_from_rating(rating),
        })
    return points


def get_map_style() -> str:
    return "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"


def build_map(df_hotels: pd.DataFrame, airport: Dict[str, Any]) -> pdk.Deck:
    layers = [
        pdk.Layer(
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
    ]
    
    # Add airport marker if available
    if airport and airport.get("location"):
        df_airport = pd.DataFrame([{
            "name": airport.get("name", "Airport"),
            "lat": airport["location"]["lat"],
            "lon": airport["location"]["lon"],
            "color": [255, 165, 0, 255],
            "details": "",
        }])
        
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=df_airport,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=15,
            radius_units="meters",
            radius_min_pixels=10,
            radius_max_pixels=40,
            pickable=True,
            auto_highlight=True,
            get_line_color=[255, 255, 255, 255],
            line_width_min_pixels=2,
            stroked=True,
        ))
    
    # Center map on airport location or first hotel
    if airport and airport.get("location"):
        center_lat = airport["location"]["lat"]
        center_lon = airport["location"]["lon"]
    else:
        center_lat = df_hotels["lat"].iloc[0]
        center_lon = df_hotels["lon"].iloc[0]
    
    view_state = pdk.ViewState(
        longitude=center_lon,
        latitude=center_lat,
        zoom=1,
    )
    
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
        airport_name = st.text_input("Airport Name")
    with col2:
        within_km = st.number_input("Distance (km)", min_value=1, max_value=500, value=50)
    
    st.caption("Markers are colored by rating (0–10) derived from reviews.")

    if st.button("Search"):
        if missing := validate_required(settings):
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
                variables=build_variables(airport_name, within_km),
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



