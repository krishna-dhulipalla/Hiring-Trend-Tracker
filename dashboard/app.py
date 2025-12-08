import streamlit as st
from components import apply_custom_css

st.set_page_config(
    page_title="Hiring Trend Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()

st.title("Hiring Trend Tracker 📈")

st.markdown("""
### Welcome

This dashboard tracks hiring trends across tech companies.

**Navigate using the sidebar to:**
- **Market Overview**: See who is hiring the most.
- **Company Detail**: Deep dive into a specific company.
- **Diff Viewer**: See exactly what changed on a given day.
- **Role Explorer**: Search for open roles across all companies.

*Note: This tool runs locally and reads from your SQLite database and JSON snapshots.*
""")

# Optional: Auto-redirect to Overview if preferred, but a welcome page is nice documentation.
# st.switch_page("pages/01_Overview.py")
