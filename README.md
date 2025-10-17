## Travel Sample: AppSync + Couchbase Data API

This demo searches hotels near airports using an AWS AppSync GraphQL API backed by Couchbase Data API, with a Streamlit frontend for visualization. The query uses geospatial calculations to find hotels within a specified distance from an airport. Results include both hotel listings and the airport information (name and location) in a structured GraphQL response.

### Screenshots

- AWS AppSync
  - Environment Variables
    ![AppSync Env Vars Configuration](assets/appsync-env-vars.jpg)

  - Schema / Types
    ![AppSync schema](assets/appsync-schema.jpg)
  
  - Data source
    ![AppSync Data Source](assets/appsync-data-source.jpg)

  - Resolver  
    ![AppSync Resolver](assets/appsync-resolver.jpg)

- Streamlit frontend
  - Home Page
    ![Streamlit home](assets/streamlit-search.jpg)
  
  - Map visualization  
    ![Streamlit map](assets/streamlit-map.jpg)

### What's here
- `src/backend/`
  - `schema.graphql`: Defines the GraphQL schema with:
    - Query: `listHotelsNearAirport(airportName: String!, withinKm: Int!)`
    - Returns `Output` type with `hotels: [Hotel]` and `airport: Airport`
    - `Airport` type includes `name: String` and `location: GeoObject` (lat, lon, accuracy)
    - `Hotel` type includes all hotel details, geo location, and reviews
  - `listHotelsInCity resolver.js`: JavaScript resolver for AppSync HTTP data source
    - Calls Couchbase Data API to query `travel-sample.inventory.hotel` and `travel-sample.inventory.airport`
    - Uses a SQL++ query with Common Table Expression (CTE) for geospatial distance calculation
    - Extracts airport coordinates from query results and combines with airport name from input
    - Returns structured response matching the `Output` schema
    - Credentials read from AppSync environment variables (`cb_username`, `cb_password`)
  - `query.graphql`: Example GraphQL query for testing in the AppSync console
- `src/frontend/`
  - `home.py`: Streamlit main entry point with navigation sidebar and connection settings (GraphQL endpoint, API key)
  - `search_hotels.py`: Interactive search interface
    - Calls AppSync GraphQL API with airport name and distance parameters
    - Displays results on an interactive map using Pydeck
    - Hotels shown as color-coded markers (red to green by rating)
    - Airport shown as orange marker with white outline
    - Hover tooltips show hotel details (name, rating, address, price, etc.) or just airport name
    - Automatically centers and zooms map to show all markers

### Why Data API for this (serverless)
Keeps credentials and query logic securely on the server behind AppSync (as environment variables), avoids client-side secrets and heavy SDK initialization, and fits stateless, scalable Lambda resolvers.

### Quick start
1) Backend (AppSync)
   - Create an HTTP data source pointing to your Couchbase Data API base URL.
   - Import `src/backend/schema.graphql` as your schema.
   - Configure environment variables in AppSync settings:
     - `cb_username`: Your Couchbase username
     - `cb_password`: Your Couchbase password
   - Attach `src/backend/listHotelsInCity resolver.js` as the JavaScript resolver for `Query.listHotelsNearAirport` using the Unit Resolver and Couchbase Data API as the data source.
   - Use `src/backend/query.graphql` in the AppSync console to test (provide an airport name and distance in km).

2) Frontend (Streamlit)
   - Install deps and run:
     ```bash
     cd couchbase-data_api-appsync-demo
     python3 -m pip install -r requirements.txt
     streamlit run src/frontend/home.py
     ```
   - In the app sidebar, set: GraphQL endpoint and API key.
   - Go to "Search Hotels", enter an airport name and distance, and click "Search".

### Notes

**Backend (Resolver)**
- Assumes collections `travel-sample.inventory.hotel` and `travel-sample.inventory.airport` exist
- Uses SQL++ query with CTE to find airport coordinates: `SELECT a.geo.lat, a.geo.lon, a.geo.accuracy FROM airport WHERE a.airportname = $1`
- Calculates distance using Pythagorean theorem approximation (accurate for small distances): `POWER(hotel_lat - airport_lat, 2) + POWER(hotel_lon - airport_lon, 2) <= POWER(distance_km / 111, 2)` where 111 ≈ km per degree of latitude
- Returns airport coordinates from first result row (all rows have same airport location)
- Combines airport location with airport name from input arguments to create `Airport` object
- Cleans hotel objects by removing airport coordinate fields (alat, alon, accuracy)

**Frontend (Streamlit)**
- Extracts airport name and location from the `airport` object in GraphQL response
- Computes hotel ratings by averaging `Overall` scores from reviews array, scaled to 0-10
- Colors hotel markers from red (low rating) to green (high rating)
- Shows airport marker in orange with larger size and white outline for visibility
- Tooltips display full details for hotels, only name for airport
- Map auto-centers on all markers with appropriate zoom level based on geographic spread

