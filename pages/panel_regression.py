import streamlit as st
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Panel Regression",
    page_icon="📈",
    layout="wide",
)

render_sidebar()

st.title("Panel Regression")

# Add your content here
