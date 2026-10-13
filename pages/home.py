import streamlit as st
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Home",
    page_icon="🏠",
    layout="wide",
)

render_sidebar()

st.title("Home")

# Add your content here
