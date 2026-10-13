import streamlit as st
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Instructions",
    page_icon="📋",
    layout="wide",
)

render_sidebar()

st.title("Instructions")

# Add your content here
