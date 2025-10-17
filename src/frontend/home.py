import importlib
import streamlit as st


PAGES = {
    "Home": "home",
    "Search Hotels": "search_hotels",
}


def render_home():
    st.title("Home")
    st.subheader("About this demo")
    st.markdown(
        "This Streamlit app calls an AWS AppSync GraphQL API that uses Couchbase Data API behind the scenes to search hotels by city and visualize results on a map."
    )
    st.markdown(
        "**Why dataAPI for serverless?** It keeps credentials and query logic secure on the server behind AppSync, avoids heavy SDK initialization overhead, and perfectly fits stateless, scalable Lambda functions."
    )
    st.subheader("What this demo showcases and how to proceed")
    st.markdown(
        "- Enter your AppSync GraphQL endpoint and API key in the sidebar (plus Couchbase creds).\n"
        "- Go to 'Search Hotels' to run a city filter; resolvers invoke dataAPI to query Couchbase.\n"
        "- View results in a list and on a map; try different cities.\n"
        "- Extend this starter by adding mutations or subscriptions in your AppSync schema."
    )


def render():
    st.sidebar.header("Navigation")
    page_name = st.sidebar.selectbox("Go to", list(PAGES.keys()))

    st.sidebar.header("Connection Settings")
    st.session_state["gql_endpoint"] = st.sidebar.text_input(
        "GraphQL Endpoint",
        value=st.session_state.get("gql_endpoint", ""),
    )
    st.session_state["api_key"] = st.sidebar.text_input(
        "GraphQL API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
    )

    module_name = PAGES[page_name]
    if module_name == "home":
        render_home()
        return
    # Require connection settings for non-Home pages
    required_keys = [
        "gql_endpoint",
        "api_key",
    ]
    labels = {
        "gql_endpoint": "GraphQL Endpoint",
        "api_key": "GraphQL API Key",
    }
    missing = [labels[k] for k in required_keys if not st.session_state.get(k)]
    if missing:
        st.error(f"Please fill the required connection settings: {', '.join(missing)}")
        return
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "render"):
            module.render()
        else:
            st.error("Selected page is missing a render() function.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load page: {exc}")


if __name__ == "__main__":
    render()


