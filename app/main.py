import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Retail Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# PROFESSIONAL UI STYLE
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F4F7FB;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .hero {
        background: #14213D;
        padding: 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 24px;
    }

    .hero h1 {
        color: white;
        font-size: 30px;
        margin-bottom: 8px;
    }

    .hero p {
        color: #CBD5E1;
        font-size: 15px;
        margin-bottom: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

PAGES = {
    "Executive Overview":
        "Sales, revenue and business performance.",

    "Sales Analytics":
        "Product, category and store performance.",

    "Inventory Intelligence":
        "Stock monitoring and reorder decisions.",

    "Customer Intelligence":
        "Customer segmentation and retention.",

    "Demand Forecasting":
        "Demand prediction and model evaluation."
}


with st.sidebar:

    st.title("📊 Retail Intelligence")

    st.caption("Business Analytics Platform")

    st.divider()

    selected_page = st.radio(
        "Navigation",
        list(PAGES.keys())
    )

    st.divider()

    st.caption(
        "Portfolio project using synthetic retail data."
    )


# --------------------------------------------------
# MAIN CONTENT
# --------------------------------------------------

st.markdown(
    f"""
    <div class="hero">
        <h1>{selected_page}</h1>
        <p>{PAGES[selected_page]}</p>
    </div>
    """,
    unsafe_allow_html=True
)


st.info(
    "Application interface initialized. "
    "Live PostgreSQL data integration "
    "will be added in the next development step."
)


col1, col2, col3 = st.columns(3)


with col1:
    st.subheader("Data Engineering")
    st.write(
        "Python ETL and PostgreSQL data warehouse."
    )


with col2:
    st.subheader("Business Intelligence")
    st.write(
        "Sales, inventory and customer analytics."
    )


with col3:
    st.subheader("Machine Learning")
    st.write(
        "Demand forecasting and RFM segmentation."
    )


st.divider()

st.caption(
    "Retail Intelligence Platform | "
    "Synthetic Dataset | Portfolio Project"
)