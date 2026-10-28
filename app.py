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
from agents.smartstay_agent import SmartStayAgent
from tools.pg_comparator import compare_pgs

# Page Configuration
st.set_page_config(
    page_title="SmartStay | AI-Powered PG Finder",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }

    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.95) 0%, rgba(15, 23, 42, 0.95) 50%, rgba(49, 46, 129, 0.9) 100%);
        border: 1px solid rgba(129, 140, 248, 0.25);
        border-radius: 20px;
        padding: 2.2rem 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 30%, #818cf8 70%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 400;
        max-width: 850px;
        line-height: 1.5;
    }

    /* Badges */
    .badge-mcp {
        display: inline-flex;
        align-items: center;
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        border: 1px solid rgba(129, 140, 248, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }

    /* Stat Card */
    .stat-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 8px 20px -6px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(8px);
    }
    .stat-val {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.2rem;
    }
    .stat-label {
        font-size: 0.82rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* PG Card Styling */
    .pg-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.3rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .pg-card:hover {
        border-color: rgba(129, 140, 248, 0.4);
        transform: translateY(-2px);
    }
    .pg-rank-badge {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: #ffffff;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 8px;
        display: inline-block;
        margin-bottom: 0.5rem;
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
        color: #38bdf8;
    }
    .pg-rent-sub {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 400;
    }
    .tag-pill {
        display: inline-block;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #cbd5e1;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.78rem;
        margin-right: 5px;
        margin-bottom: 5px;
    }
    .tag-pill-highlight {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #6ee7b7;
    }
    .score-meter {
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(129, 140, 248, 0.3);
        border-radius: 12px;
        padding: 8px 12px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .score-meter strong {
        font-size: 1.2rem;
        color: #818cf8;
    }

    /* Verification Box */
    .verify-box {
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Hero Header
st.markdown("""
<div class="hero-banner">
    <div class="badge-mcp">Model Context Protocol (MCP) Multi-Server Agent</div>
    <div class="hero-title">SmartStay — AI PG Finder</div>
    <div class="hero-subtitle">
        Find verified student and professional accommodations in Ahmedabad. Driven by dynamic tool selection across SmartStay PG & Location MCP servers, grounded with deterministic constraint verification and one-shot reflection.
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
        city_input = st.selectbox("City", ["Ahmedabad"], index=0)
        area_input = st.selectbox(
            "Neighborhood Area",
            ["All Areas", "Navrangpura", "Vastrapur", "Bodakdev", "Satellite", "Paldi"]
        )
        gender_input = st.selectbox(
            "Accommodation Preference",
            ["Girls", "Boys", "Co-Ed"],
            index=0
        )
        budget_input = st.slider(
            "Maximum Monthly Rent (₹)",
            min_value=5000,
            max_value=15000,
            value=8000,
            step=500
        )
        dest_input = st.selectbox(
            "Destination (College / Office)",
            [
                "LD College of Engineering, Ahmedabad",
                "Gujarat University, Ahmedabad",
                "IIM Ahmedabad (Vastrapur)",
                "Nirma University, Ahmedabad",
                "CEPT University, Ahmedabad",
                "St. Xavier's College, Ahmedabad"
            ]
        )
        max_dist_input = st.slider(
            "Max Distance (km)",
            min_value=1.0,
            max_value=8.0,
            value=3.0,
            step=0.5
        )
        amenities_input = st.multiselect(
            "Mandatory Amenities",
            options=["Wi-Fi", "Food", "AC", "Laundry", "Housekeeping", "Power Backup", "Gym"],
            default=["Wi-Fi", "Food"]
        )

        # Synthesize into unified query for the agent
        area_part = f"in {area_input}" if area_input != "All Areas" else "in Ahmedabad"
        amenities_part = f"with {', '.join(amenities_input)}" if amenities_input else ""
        user_prompt = f"Find a {gender_input.lower()}' PG {area_part} under ₹{budget_input:,.0f} per month, within {max_dist_input} km of {dest_input}, {amenities_part}."
        st.info(f"Synthesized Query:\n_{user_prompt}_")

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
    <div style="font-size: 0.8rem; color: #64748b;">
        <strong>Architecture:</strong><br>
        • SmartStay FastMCP Server (stdio)<br>
        • Pre-built Location MCP Server<br>
        • ReAct Agentic Loop & Reflection<br>
        • Level 2 Capstone Project
    </div>
    """, unsafe_allow_html=True)


# Initialize Session State
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
    st.session_state["searched"] = False

# Execution on button click or default initial load
if search_btn or not st.session_state["searched"]:
    with st.spinner("🤖 SmartStay Agent executing dynamic tool discovery, geocoding, and constraint validation..."):
        agent = SmartStayAgent(model_name=model_choice, max_iterations=max_iters)
        res = agent.run(user_prompt)
        st.session_state["last_result"] = res
        st.session_state["searched"] = True

res = st.session_state.get("last_result")

if res:
    val = res["validation_result"]
    ref = res["reflection_result"]
    pgs = res["recommended_pgs"]

    # Top Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">{len(pgs)}</div>
            <div class="stat-label">Eligible Listings</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        lowest_rent = min([p['monthly_rent'] for p in pgs]) if pgs else 0
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">₹{lowest_rent:,.0f}</div>
            <div class="stat-label">Lowest Monthly Rent</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        status_text = "PASSED" if val.get("is_valid") else "FLAGGED"
        status_color = "#34d399" if val.get("is_valid") else "#f87171"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: {status_color};">{status_text}</div>
            <div class="stat-label">Deterministic Check</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        obs_count = len(res.get("observations", []))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">{obs_count}</div>
            <div class="stat-label">MCP Observations</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab_recs, tab_trace, tab_val, tab_comp = st.tabs([
        "🏡 PG Recommendations",
        "⚡ Agentic Loop & MCP Trace",
        "🛡️ Reflection & Validation Audit",
        "📊 Side-by-Side Comparison"
    ])

    with tab_recs:
        st.markdown(f"#### Verified Recommendations for: _{res['query']}_")

        if not pgs:
            st.warning("⚠️ No accommodations found satisfying all criteria. Consider increasing budget or expanding proximity.")
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
                    with st.expander("🔎 Match Analysis", expanded=True):
                        st.markdown(f"**PG ID:** `{p_id}`")
                        st.markdown(f"**Availability:** `{p.get('availability') or 'Unknown'}`")
                        st.markdown(f"**Data Source:** `{p.get('data_source')}`")
                        if dist_km:
                            st.caption(f"Calculated using Haversine formula from destination coordinates.")

        st.markdown("---")
        st.markdown("#### 📝 Agent's Final Grounded Response")
        st.markdown(res["final_response"])

    with tab_trace:
        st.markdown("#### Dynamic MCP Tool Discovery")
        st.caption("Discovered and registered from connected SmartStay and Location MCP servers:")
        tool_cols = st.columns(2)
        discovered = res.get("discovered_tools", [])
        for i, t in enumerate(discovered):
            with tool_cols[i % 2]:
                st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 10px; margin-bottom: 8px;">
                    <strong style="color: #818cf8;">{t['name']}</strong> &nbsp;<span style="font-size: 0.75rem; background: #334155; padding: 2px 6px; border-radius: 4px;">{t['server']}</span>
                    <div style="font-size: 0.82rem; color: #94a3b8; margin-top: 4px;">{t['description']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>#### Tool Calling Observations", unsafe_allow_html=True)
        observations = res.get("observations", [])
        for idx, obs in enumerate(observations, 1):
            with st.expander(f"Step {idx}: Executed tool '{obs.get('tool')}'", expanded=False):
                st.json(obs.get("result"))

    with tab_val:
        st.markdown("#### Deterministic Constraint Verification")
        st.caption("Zero-hallucination verification against active SQLite/JSON database:")

        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.markdown('<div class="verify-box">', unsafe_allow_html=True)
            st.markdown("**Verified Facts [PASS]**")
            for item in val.get("verified_items", []):
                st.markdown(f"- ✅ {item}")
            st.markdown('</div>', unsafe_allow_html=True)

        with v_col2:
            if val.get("warnings") or val.get("errors"):
                st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                st.markdown("**Warnings & Guardrails**")
                for w in val.get("warnings", []):
                    st.markdown(f"- ⚠️ {w}")
                for e in val.get("errors", []):
                    st.markdown(f"- ❌ {e}")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("All budget, gender, amenity, and grounding criteria passed with 0 warnings.")

        st.markdown("#### One-Shot Reflection Audit")
        ref_status = "Correction Applied" if ref.get("needs_correction") else "Verified Without Correction"
        st.info(f"**Reflection Status:** {ref_status}\n\n**Auditor Critique:** {ref.get('critique')}")

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
