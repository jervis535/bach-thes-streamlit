import streamlit as st
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="My App",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)