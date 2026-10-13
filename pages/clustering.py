import streamlit as st
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Clustering",
    page_icon="📊",
    layout="wide",
)

render_sidebar()

st.title("Clustering")

# Add your content here
