import importlib
import streamlit as st


def render_home():
    st.title("Home")
    st.subheader("About this demo")
    st.markdown(
        "This demo showcases how to use **Couchbase Capella Data API** with AWS AppSync. "
        "The app searches hotels near airports using geospatial queries and visualizes results on an interactive map."
    )
    st.markdown(
        "**Why Data API for serverless?**\n\n"
        "The Data API is ideal for serverless architectures because:\n"
        "- **Driverless mode:** No need to deploy SDKs in FaaS environments (AWS Lambda, Azure Functions)\n"
        "- **Lightweight:** Avoids heavy SDK initialization overhead in stateless functions\n"
        "- **Simple integration:** Uses standard HTTP—no SDK version management or dependencies\n"
        "- **Language agnostic:** Works with any platform that can make HTTP requests\n"
        "\nLearn more: [Data API vs. SDKs](https://docs.couchbase.com/cloud/data-api-guide/data-api-sdks.html)"
    )
    
    st.subheader("Architecture")
    st.markdown(
        "- **Frontend:** Streamlit (Python)\n"
        "- **API Layer:** AWS AppSync (GraphQL)\n"
        "- **Backend:** Couchbase Capella via Data API\n"
        "- **Dataset:** Travel-sample bucket"
    )
    
    st.subheader("How to get started")
    st.markdown(
        "**Step 1:** Set up AWS AppSync as per this [tutorial](https://developer.couchbase.com/tutorial-appsync-data-api-streamlit-travel-sample).\n\n"
        "**Step 2:** Enter your AppSync GraphQL API endpoint and API key in the sidebar (found in the Settings section in AWS AppSync console).\n\n"
        "**Step 3:** Click the 'Search Hotels' tab above to experience the full flow—search for hotels near airports and view them on a map."
    )
    
    st.subheader("Resources")
    st.markdown(
        "- [Couchbase Capella Data API Documentation](https://docs.couchbase.com/cloud/data-api-guide/data-api-intro.html)\n"
        "- [AWS AppSync Documentation](https://docs.aws.amazon.com/appsync/)"
    )


def render():
    st.sidebar.header("Connection Settings")
    st.session_state["gql_endpoint"] = st.sidebar.text_input(
        "AppSync GraphQL Endpoint",
        value=st.session_state.get("gql_endpoint", ""),
        placeholder="https://xxxxx.appsync-api.ap-south-1.amazonaws.com/graphql",
    )
    st.session_state["api_key"] = st.sidebar.text_input(
        "AppSync API Key",
        value=st.session_state.get("api_key", ""),
        type="password"
    )

    tab1, tab2 = st.tabs(["Home", "Search Hotels"])
    
    with tab1:
        render_home()
    
    with tab2:
        # Require connection settings for Search Hotels page
        required_keys = [
            "gql_endpoint",
            "api_key",
        ]
        labels = {
            "gql_endpoint": "AppSync GraphQL Endpoint",
            "api_key": "AppSync API Key",
        }
        missing = [labels[k] for k in required_keys if not st.session_state.get(k)]
        if missing:
            st.error(f"Please fill the required connection settings in the sidebar: {', '.join(missing)}")
        else:
            try:
                module = importlib.import_module("search_hotels")
                if hasattr(module, "render"):
                    module.render()
                else:
                    st.error("Selected page is missing a render() function.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Failed to load page: {exc}")


if __name__ == "__main__":
    render()



