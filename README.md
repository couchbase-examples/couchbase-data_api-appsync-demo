## Travel Sample: AppSync + Couchbase Data API (src)

This demo searches hotels by city using an AWS AppSync GraphQL API backed by Couchbase Data API, with a Streamlit frontend for visualization.

### Screenshots

- AWS AppSync
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
  - `schema.graphql`: Defines `listHotelsInCity(city: String!)` and types.
  - `listHotelsInCity resolver.js`: JavaScript resolver for an AppSync HTTP data source calling Couchbase Data API; queries `travel-sample.inventory.hotel`. Credentials are read from AppSync environment variables.
  - `query.graphql`: Example query you can paste into the AppSync console.
- `src/frontend/`
  - `search_hotels.py`: Streamlit app to call AppSync and plot hotels on a map.

### Why Data API for this (serverless)
Keeps credentials and query logic securely on the server behind AppSync (as environment variables), avoids client-side secrets and heavy SDK initialization, and fits stateless, scalable Lambda resolvers.

### Quick start
1) Backend (AppSync)
   - Create an HTTP data source pointing to your Couchbase Data API base URL.
   - Import `src/backend/schema.graphql` as your schema.
   - Configure environment variables in AppSync settings:
     - `cb_username`: Your Couchbase username
     - `cb_password`: Your Couchbase password
   - Attach `src/backend/listHotelsInCity resolver.js` as the JavaScript resolver for `Query.listHotelsInCity` using the Unit Resolver and Couchbase Data API as the data source.
   - Use `src/backend/query.graphql` in the AppSync console to test (provide a city name).

2) Frontend (Streamlit)
   - Install deps and run:
     ```bash
     cd couchbase-data_api-appsync-demo
     python3 -m pip install -r requirements.txt
     streamlit run src/frontend/home.py
     ```
   - In the app sidebar, set: GraphQL endpoint and API key.
   - Go to "Search Hotels", enter a city, and click "Search".

### Notes
- Resolver assumes collection `travel-sample.inventory.hotel` exists.
- The frontend colors markers by computed rating and shows results on a map and in a table.

