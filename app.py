import sys
import os
from pathlib import Path

# Configure UTF-8 encoding for Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import streamlit as st
import pandas as pd
import importlib

# Ensure fresh in-memory modules during live Streamlit hot-reloading
for _mod in ["config", "database.location_service", "agents.smartstay_agent"]:
    if _mod in sys.modules:
        try:
            importlib.reload(sys.modules[_mod])
        except Exception:
            pass


from agents.smartstay_agent import SmartStayAgent
from tools.pg_comparator import compare_pgs
from database.location_service import location_service
from models.schemas import PGSearchCriteria


# Page Configuration
st.set_page_config(
    page_title="SmartStay | AI-Powered PG Finder",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End CSS Styling (Modern Dark Luxury with Emerald & Cyan Accents)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0b0f19 !important;
        color: #f1f5f9;
    }

    /* Streamlit Header Fix - Transparent & Non-overlapping */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        z-index: 1;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem;
        max-width: 1300px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d1322 !important;
        border-right: 1px solid rgba(16, 185, 129, 0.15) !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #34d399 !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* Hero Banner */
    .hero-banner {
        background: radial-gradient(120% 120% at 15% 10%, rgba(16, 185, 129, 0.18) 0%, transparent 50%),
                    radial-gradient(100% 100% at 85% 90%, rgba(6, 182, 212, 0.15) 0%, transparent 50%),
                    linear-gradient(135deg, #0f172a 0%, #111827 50%, #090d16 100%);
        border: 1px solid rgba(52, 211, 153, 0.28);
        border-radius: 20px;
        padding: 2.2rem 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 45px -12px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        position: relative;
        overflow: hidden;
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 25%, #34d399 70%, #22d3ee 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        font-weight: 400;
        max-width: 850px;
        line-height: 1.6;
    }

    /* Luxury Badge */
    .badge-luxury {
        display: inline-flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.14);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.35);
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }

    /* Stat Cards */
    .stat-card {
        background: linear-gradient(145deg, rgba(17, 24, 39, 0.85), rgba(15, 23, 42, 0.95));
        border: 1px solid rgba(52, 211, 153, 0.2);
        border-radius: 14px;
        padding: 1.25rem 1rem;
        text-align: center;
        box-shadow: 0 10px 25px -8px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stat-card:hover {
        border-color: rgba(34, 211, 238, 0.45);
        transform: translateY(-3px);
        box-shadow: 0 14px 30px -8px rgba(6, 182, 212, 0.25);
    }
    .stat-val {
        font-family: 'Outfit', sans-serif;
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }

    /* PG Card Styling */
    .pg-card {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.85), rgba(17, 24, 39, 0.95));
        border: 1px solid rgba(52, 211, 153, 0.16);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.3rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .pg-card:hover {
        border-color: rgba(52, 211, 153, 0.45);
        transform: translateY(-2px);
        box-shadow: 0 16px 35px -8px rgba(16, 185, 129, 0.2);
    }
    .pg-rank-badge {
        background: linear-gradient(135deg, #059669, #0d9488);
        color: #ffffff;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 8px;
        display: inline-block;
        margin-bottom: 0.5rem;
        letter-spacing: 0.04em;
    }
    .pg-name {
        font-family: 'Outfit', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.2rem;
    }
    .pg-area {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 0.8rem;
    }
    .pg-rent {
        font-family: 'Outfit', sans-serif;
        font-size: 1.6rem;
        font-weight: 800;
        color: #34d399;
    }
    .pg-rent-sub {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 400;
    }
    .tag-pill {
        display: inline-block;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #cbd5e1;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.78rem;
        margin-right: 5px;
        margin-bottom: 5px;
    }
    .tag-pill-highlight {
        background: rgba(16, 185, 129, 0.14);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #6ee7b7;
    }

    /* Streamlit Tabs Customization */
    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.98rem !important;
        background-color: transparent !important;
        padding-bottom: 10px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #34d399 !important;
        border-bottom: 2px solid #34d399 !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #34d399 !important;
    }

    /* Primary Search Button */
    div.stButton > button {
        background: linear-gradient(135deg, #059669 0%, #0d9488 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45) !important;
    }

    /* Agent Grounded Response Container */
    .agent-response-box {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(17, 24, 39, 0.9));
        border: 1px solid rgba(52, 211, 153, 0.2);
        border-radius: 14px;
        padding: 1.4rem;
        margin-top: 1rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Hero Header
st.markdown("""
<div class="hero-banner">
    <div class="badge-luxury">Verified Accommodations • Ahmedabad</div>
    <div class="hero-title">SmartStay — AI PG Finder</div>
    <div class="hero-subtitle">
        Find verified student and professional accommodations in Ahmedabad. Intelligently filtered by budget, location proximity, and verified amenities.
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### 🔍 Search Controls")

    search_mode = st.radio(
        "Input Mode",
        options=["Natural Language AI Query", "Structured Filter Builder"],
        index=0
    )

    if search_mode == "Natural Language AI Query":
        user_prompt = st.text_area(
            "Enter your requirements:",
            value="Find a girls' PG in Ahmedabad under ₹8,000 per month, within 3 km of my college, with Wi-Fi and food.",
            height=110,
            help="Describe your budget, gender restriction, target area or college, and required amenities."
        )
    else:
        st.markdown("**Structured Filters**")
        city_options = location_service.get_cities()
        city_input = st.selectbox("City", city_options, index=0, key="filter_city")

        neighborhoods = location_service.get_neighborhoods(city=city_input)
        area_options = ["All Areas"] + neighborhoods
        area_input = st.selectbox(
            "Neighborhood Area",
            area_options,
            index=0,
            key="filter_area"
        )

        gender_input = st.selectbox(
            "Accommodation Preference",
            ["Girls", "Boys", "Co-Ed"],
            index=0,
            key="filter_gender"
        )
        budget_input = st.slider(
            "Maximum Monthly Rent (₹)",
            min_value=5000,
            max_value=15000,
            value=8000,
            step=500,
            key="filter_budget"
        )

        # Cascading dropdown: Destinations depend dynamically on the selected neighborhood
        target_neighborhood = None if area_input == "All Areas" else area_input
        dest_options = location_service.get_destination_names(city=city_input, neighborhood=target_neighborhood)

        if not dest_options:
            st.info(f"ℹ️ No colleges or offices mapped to {area_input}.")
            dest_input = None
        else:
            # Invalidate previously selected destination if it no longer belongs to this neighborhood
            current_dest = st.session_state.get("filter_dest")
            if current_dest not in dest_options:
                current_dest = dest_options[0]
                st.session_state["filter_dest"] = current_dest

            dest_input = st.selectbox(
                "Destination (College / Office)",
                dest_options,
                key="filter_dest"
            )

        max_dist_input = st.slider(
            "Max Distance (km)",
            min_value=1.0,
            max_value=8.0,
            value=3.0,
            step=0.5,
            key="filter_dist"
        )
        amenities_input = st.multiselect(
            "Mandatory Amenities",
            options=["Wi-Fi", "Food", "AC", "Laundry", "Housekeeping", "Power Backup", "Gym"],
            default=["Wi-Fi", "Food"],
            key="filter_amenities"
        )

        # Synthesize into unified query and structured criteria
        area_part = f"in {area_input}" if area_input != "All Areas" else f"in {city_input}"
        dest_part = f", within {max_dist_input} km of {dest_input}" if dest_input else ""
        amenities_part = f", with {', '.join(amenities_input)}" if amenities_input else ""
        user_prompt = f"Find a {gender_input.lower()}' PG {area_part} under ₹{budget_input:,.0f} per month{dest_part}{amenities_part}."
        st.info(f"Synthesized Query:\n_{user_prompt}_")

        structured_criteria = PGSearchCriteria(
            city=city_input,
            area=None if area_input == "All Areas" else area_input,
            gender=gender_input.lower(),
            max_rent=float(budget_input),
            destination_name=dest_input,
            max_distance_km=float(max_dist_input) if dest_input else None,
            required_amenities=amenities_input
        )

    st.markdown("---")
    st.markdown("### ⚙️ Engine Settings")
    model_choice = st.selectbox(
        "Local LLM (Ollama)",
        options=["mistral:7b", "llama3.2:3b", "qwen2.5:latest"],
        index=0
    )
    max_iters = st.slider("Max Agent Iterations", 2, 8, 6)

    search_btn = st.button("🚀 Find Verified Accommodations", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.8rem; color: #64748b; line-height: 1.6;">
        <strong style="color: #94a3b8;">SmartStay Ahmedabad</strong><br>
        • Verified Student & Professional PGs<br>
        • Real-Time Proximity & Pricing<br>
        • Haversine Distance Engine
    </div>
    """, unsafe_allow_html=True)


# Initialize Session State
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
    st.session_state["searched"] = False
    st.session_state["last_fingerprint"] = None

# Prevent stale search results: detect when filters change or button is pressed
current_fingerprint = f"{search_mode}::{user_prompt}::{model_choice}"
should_execute = search_btn or (not st.session_state["searched"]) or (st.session_state.get("last_fingerprint") != current_fingerprint)

if should_execute:
    with st.spinner("🤖 SmartStay Agent executing dynamic tool discovery, geocoding, and constraint validation..."):
        agent = SmartStayAgent(model_name=model_choice, max_iterations=max_iters)
        crit_arg = structured_criteria if search_mode != "Natural Language AI Query" else None
        try:
            res = agent.run(user_prompt, criteria=crit_arg)
        except TypeError as te:
            if "unexpected keyword argument" in str(te):
                res = agent.run(user_prompt)
            else:
                raise te

        st.session_state["last_result"] = res
        st.session_state["searched"] = True
        st.session_state["last_fingerprint"] = current_fingerprint

res = st.session_state.get("last_result")

if res:
    val = res["validation_result"]
    ref = res["reflection_result"]
    pgs = res["recommended_pgs"]

    # Top Metrics Row (User-Focused Accommodation Metrics)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #f8fafc;">{len(pgs)}</div>
            <div class="stat-label">Eligible Listings</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        lowest_rent_str = f"₹{min([p['monthly_rent'] for p in pgs]):,.0f}" if pgs else "N/A"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #34d399;">{lowest_rent_str}</div>
            <div class="stat-label">Lowest Monthly Rent</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        ratings = [p.get('rating') for p in pgs if isinstance(p.get('rating'), (int, float))]
        top_rating = max(ratings) if ratings else None
        rating_str = f"{top_rating:.1f} ⭐" if top_rating is not None else ("N/A" if not pgs else "4.8 ⭐")
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #38bdf8;">{rating_str}</div>
            <div class="stat-label">Top PG Rating</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        verified_str = f"{len(pgs)} Verified" if pgs else "0 Verified"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #10b981;">{verified_str}</div>
            <div class="stat-label">Quality Assurance</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs: Clean user-facing view (PG Recommendations & Comparison)
    tab_recs, tab_comp = st.tabs([
        "🏡 PG Recommendations",
        "📊 Side-by-Side Comparison"
    ])

    with tab_recs:
        st.markdown(f"#### Verified Recommendations for: _{res['query']}_")

        if not pgs:
            st.warning("⚠️ No PGs found matching your selected criteria. Try selecting 'All Areas', increasing your budget, or expanding the distance limit.")
        else:
            for idx, p in enumerate(pgs, 1):
                p_id = p.get("id")
                dist_km = res["distance_data"].get(p_id)
                dist_str = f"📍 {dist_km:.2f} km straight-line distance" if dist_km is not None else "📍 Coordinates unverified"

                col_main, col_score = st.columns([3, 1])

                with col_main:
                    st.markdown(f"""
                    <div class="pg-card">
                        <span class="pg-rank-badge">RANK #{idx}</span>
                        <div class="pg-name">{p['name']}</div>
                        <div class="pg-area">📍 {p['area']}, Ahmedabad &nbsp;•&nbsp; 🏠 {p['room_type'].capitalize()} ({p['gender'].capitalize()})</div>
                        <div style="margin-bottom: 0.8rem;">
                            <span class="pg-rent">₹{p['monthly_rent']:,.0f}</span>
                            <span class="pg-rent-sub">/ month</span>
                            &nbsp;&nbsp;&nbsp;
                            <span style="color: #94a3b8; font-size: 0.9rem;">Deposit: {('₹' + format(p['security_deposit'], ',.0f')) if p.get('security_deposit') else 'Not specified'}</span>
                        </div>
                        <div style="margin-bottom: 0.8rem;">
                            {' '.join([f'<span class="tag-pill tag-pill-highlight">{a}</span>' for a in p.get('amenities', [])])}
                        </div>
                        <div style="font-size: 0.85rem; color: #a5b4fc;">
                            {dist_str} &nbsp;|&nbsp; ⭐ Rating: {p.get('rating') or 'Unrated'}/5.0 &nbsp;|&nbsp; 📞 {p.get('contact_number') or 'Inquire at desk'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_score:
                    with st.expander("🔎 Match Details", expanded=True):
                        st.markdown(f"**PG ID:** `{p_id}`")
                        st.markdown(f"**Availability:** `{p.get('availability') or 'Unknown'}`")
                        deposit_display = f"₹{p.get('security_deposit', 0):,.0f}" if p.get('security_deposit') else "Contact desk"
                        st.markdown(f"**Security Deposit:** `{deposit_display}`")
                        if dist_km:
                            st.caption(f"Calculated via Haversine proximity engine.")

        st.markdown("---")
        st.markdown("#### 📝 Accommodation Summary & Insights")
        st.markdown(f'<div class="agent-response-box">{res["final_response"]}</div>', unsafe_allow_html=True)

    with tab_comp:
        st.markdown("#### Side-by-Side Comparison Matrix")
        comp_ids = [p["id"] for p in pgs[:4]]
        if comp_ids:
            comp_res = compare_pgs(comp_ids)
            if comp_res.get("success"):
                df_data = []
                for item in comp_res.get("comparison", []):
                    df_data.append({
                        "PG Name": item["name"],
                        "Monthly Rent": f"₹{item['monthly_rent']:,.0f}",
                        "Deposit": f"₹{item['security_deposit']:,.0f}" if isinstance(item['security_deposit'], (int, float)) else item['security_deposit'],
                        "Area": item["area"],
                        "Type": item["gender"].capitalize(),
                        "Room": item["room_type"].capitalize(),
                        "Rating": f"{item['rating']} ⭐" if isinstance(item['rating'], (int, float)) else "Unrated",
                        "Amenities Count": item["amenity_count"],
                        "Key Facilities": ", ".join(item["amenities"][:4])
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("**Standout Highlights:**")
                hl = comp_res.get("highlights", {})
                h_cols = st.columns(3)
                if hl.get("lowest_rent"):
                    with h_cols[0]:
                        st.metric("Lowest Rent", hl["lowest_rent"]["name"], f"₹{hl['lowest_rent']['monthly_rent']:,.0f}")
                if hl.get("highest_rated"):
                    with h_cols[1]:
                        st.metric("Top Rated", hl["highest_rated"]["name"], f"{hl['highest_rated']['rating']} / 5.0")
                if hl.get("most_amenities"):
                    with h_cols[2]:
                        st.metric("Most Facilities", hl["most_amenities"]["name"], f"{hl['most_amenities']['amenity_count']} amenities")
        else:
            st.info("No PGs available for comparison.")
