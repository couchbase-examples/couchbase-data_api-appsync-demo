from typing import Any, Dict, List

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


def get_connection_settings() -> Dict[str, str]:
    return {
        "endpoint": st.session_state.get("gql_endpoint", ""),
        "api_key": st.session_state.get("api_key", ""),
        "username": st.session_state.get("username", ""),
        "password": st.session_state.get("password", ""),
    }


def validate_required(settings: Dict[str, str]) -> List[str]:
    labels = {
        "endpoint": "GraphQL Endpoint",
        "api_key": "GraphQL API Key",
        "username": "Couchbase Username",
        "password": "Couchbase Password",
    }
    return [labels[k] for k, v in settings.items() if not v]


def build_query() -> str:
    return (
        "query ListHotelsInCity($auth: CouchbaseAuth!, $city: String!) {\n"
        "  listHotelsInCity(auth: $auth, city: $city) {\n"
        "    id\n"
        "    name\n"
        "    address\n"
        "    city\n"
        "    country\n"
        "    phone\n"
        "    price\n"
        "    url\n"
        "    geo { lat lon }\n"
        "    reviews { ratings { Overall } }\n"
        "  }\n"
        "}"
    )


def build_variables(settings: Dict[str, str], city: str) -> Dict[str, Any]:
    return {
        "auth": {
            "cb_username": settings["username"],
            "cb_password": settings["password"],
        },
        "city": city,
    }


def fetch_hotels(endpoint: str, api_key: str, query: str, variables: Dict[str, Any]) -> List[Dict[str, Any]]:
    headers = {"x-api-key": api_key} if api_key else {}
    resp = requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)
    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(str(payload["errors"]))
    return payload.get("data", {}).get("listHotelsInCity", [])


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
        # Scale radius by rating (in meters). Higher rating -> larger dot.
        points.append(
            {
                "name": hotel.get("name", ""),
                "rating": rating,
                "rating_display": f"{rating:.1f}/10",
                "address": hotel.get("address", ""),
                "city": hotel.get("city", ""),
                "country": hotel.get("country", ""),
                "price": hotel.get("price", ""),
                "phone": hotel.get("phone", ""),
                "url": hotel.get("url", ""),
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


def build_map(df: pd.DataFrame) -> pdk.Deck:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius=8,
        radius_units="meters",
        radius_min_pixels=4,
        radius_max_pixels=20,
        pickable=True,
        auto_highlight=True,
    )
    center_lon = float(df["lon"].mean())
    center_lat = float(df["lat"].mean())
    view_state = pdk.ViewState(
        longitude=center_lon,
        latitude=center_lat,
        zoom=11,
        pitch=0,
        bearing=0,
    )
    tooltip = {
        "html": (
            "<div>"
            "<b>{name}</b><br/>"
            "Rating: {rating_display}<br/>"
            "{address}<br/>{city}, {country}<br/>"
            "Price: {price}<br/>"
            "Phone: {phone}<br/>"
            "{url}"
            "</div>"
        ),
        "style": {"color": "white"},
    }
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=get_map_style(),
    )


def render():
    st.title("Search Hotels by City")
    settings = get_connection_settings()
    city = st.text_input("City", help="Enter the city to search hotels in")
    st.caption("Markers are colored by rating (0–10) derived from reviews.")

    if st.button("Search"):
        missing = validate_required(settings)
        if missing:
            st.error(f"Please fill the required connection settings: {', '.join(missing)}")
            return
        try:
            hotels = fetch_hotels(
                endpoint=settings["endpoint"],
                api_key=settings["api_key"],
                query=build_query(),
                variables=build_variables(settings, city),
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"GraphQL error: {exc}")
            return
        if not hotels:
            st.warning("No hotels found for this city.")
            return
        points = hotels_to_points(hotels)
        if not points:
            st.warning("No hotel coordinates to plot on the map.")
            return
        df = pd.DataFrame(points)
        deck = build_map(df)
        st.pydeck_chart(deck)
        with st.expander("Raw response"):
            st.json({"data": {"listHotelsInCity": hotels}})


if __name__ == "__main__":
    render()



