import streamlit as st
import time
import io
import sys
import os
import tempfile

st.set_page_config(
    page_title="Autonomous Procurement Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
        color: #e6edf3;
    }

    .hero-header {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem;
    }

    .hero-header h1 {
        font-size: 2.6rem;
        font-weight: 700;
        background: linear-gradient(90deg, #58a6ff, #79c0ff, #a5d6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
    }

    .hero-header p {
        color: #8b949e;
        font-size: 1rem;
        font-weight: 400;
    }

    .card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .badge-success {
        background: rgba(35, 134, 54, 0.2);
        border: 1px solid rgba(35, 134, 54, 0.5);
        color: #3fb950;
    }

    .badge-warning {
        background: rgba(210, 153, 34, 0.2);
        border: 1px solid rgba(210, 153, 34, 0.5);
        color: #d29922;
    }

    .badge-error {
        background: rgba(218, 54, 51, 0.2);
        border: 1px solid rgba(218, 54, 51, 0.5);
        color: #f85149;
    }

    .product-card {
        background: rgba(13, 17, 23, 0.6);
        border: 1px solid rgba(48, 54, 61, 0.6);
        border-left: 3px solid #58a6ff;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.8rem;
        transition: border-color 0.2s ease;
    }

    .product-card:hover {
        border-left-color: #79c0ff;
    }

    .product-card h4 {
        color: #e6edf3;
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.5rem;
    }

    .product-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.5rem;
    }

    .meta-chip {
        background: rgba(88, 166, 255, 0.1);
        border: 1px solid rgba(88, 166, 255, 0.25);
        border-radius: 6px;
        padding: 0.15rem 0.55rem;
        font-size: 0.75rem;
        color: #58a6ff;
    }

    .ai-answer-box {
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.08), rgba(121, 192, 255, 0.04));
        border: 1px solid rgba(88, 166, 255, 0.3);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-top: 1rem;
    }

    .ai-answer-box h5 {
        color: #79c0ff;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0 0 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: rgba(13, 17, 23, 0.8) !important;
        border: 1px solid rgba(48, 54, 61, 0.8) !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
    }

    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
        border: none !important;
        color: white !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #388bfd, #58a6ff) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(88, 166, 255, 0.3) !important;
    }

    .stButton > button[kind="secondary"] {
        background: rgba(22, 27, 34, 0.8) !important;
        border: 1px solid rgba(48, 54, 61, 0.8) !important;
        color: #e6edf3 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: rgba(13, 17, 23, 0.6);
        border-radius: 10px;
        padding: 0.3rem;
        gap: 0.2rem;
        border: 1px solid rgba(48, 54, 61, 0.6);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        color: #8b949e !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.5rem !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(88, 166, 255, 0.15) !important;
        color: #58a6ff !important;
    }

    .stMetric {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid rgba(48, 54, 61, 0.6);
        border-radius: 10px;
        padding: 1rem;
    }

    .stMetric [data-testid="metric-container"] > div:first-child {
        color: #8b949e !important;
        font-size: 0.8rem !important;
    }

    .stMetric [data-testid="metric-container"] > div:nth-child(2) {
        color: #e6edf3 !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    .divider {
        border: none;
        border-top: 1px solid rgba(48, 54, 61, 0.8);
        margin: 1.5rem 0;
    }

    .section-label {
        color: #8b949e;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.8rem;
    }

    code {
        background: rgba(88, 166, 255, 0.1) !important;
        color: #79c0ff !important;
        border-radius: 4px !important;
        padding: 0.1rem 0.4rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-header">
        <h1>🤖 Autonomous Procurement Agent</h1>
        <p>Scrape IndiaMART product data · Build a vector database · Query with natural language</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_scraper, tab_query = st.tabs(["🕷️  Data Scraper", "🧠  Query Engine"])


with tab_scraper:
    st.markdown('<div class="section-label">Scraper Configuration</div>', unsafe_allow_html=True)

    col_url, col_count = st.columns([3, 1])
    with col_url:
        category_url = st.text_input(
            "IndiaMART Category URL",
            placeholder="https://dir.indiamart.com/impcat/pipe-fittings.html",
            label_visibility="collapsed",
        )
    with col_count:
        product_count = st.number_input(
            "Products",
            min_value=1,
            max_value=50,
            value=5,
            help="Number of products to scrape",
        )

    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        start_scraping = st.button(
            "🚀 Start Scraping",
            type="primary",
            use_container_width=True,
            disabled=not category_url,
        )
    with col_hint:
        if not category_url:
            st.caption("Paste an IndiaMART category URL above to begin")

    if start_scraping:
        if "indiamart.com" not in category_url:
            st.error("Please enter a valid IndiaMART category URL.")
        else:
            from scraper import scrape_category_and_products

            progress_bar = st.progress(0, text="Initialising browser…")
            log_placeholder = st.empty()
            log_lines = []

            old_stdout = sys.stdout
            sys.stdout = captured = io.StringIO()

            with st.status("Scraping in progress…", expanded=True) as status:
                try:
                    scraped_data, zip_path, gdrive_id = scrape_category_and_products(
                        category_url,
                        products_per_category=product_count,
                        headless=True,
                    )
                    sys.stdout = old_stdout
                    terminal_output = captured.getvalue()

                    if scraped_data:
                        status.update(
                            label=f"✅ Done — {len(scraped_data)} products scraped",
                            state="complete",
                        )
                        progress_bar.progress(1.0, text="Complete")
                    else:
                        status.update(label="⚠️ No products scraped", state="error")
                        progress_bar.empty()

                except Exception as e:
                    sys.stdout = old_stdout
                    terminal_output = captured.getvalue() + f"\n\nError: {e}"
                    status.update(label=f"❌ Error: {e}", state="error")
                    scraped_data = []
                    zip_path = None
                    gdrive_id = None

            if scraped_data:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">Results</div>', unsafe_allow_html=True)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Products Scraped", len(scraped_data))
                m2.metric(
                    "Success Rate",
                    f"{(len(scraped_data) / product_count) * 100:.0f}%",
                )
                m3.metric("Google Drive", "✅ Uploaded" if gdrive_id else "—")
                m4.metric("Local ZIP", "✅ Saved" if zip_path else "—")

                if gdrive_id:
                    st.markdown(
                        f'<span class="status-badge badge-success">📁 Saved to Google Drive › scraped_files</span>',
                        unsafe_allow_html=True,
                    )
                    st.link_button(
                        "Open in Google Drive",
                        f"https://drive.google.com/file/d/{gdrive_id}",
                    )

                if zip_path:
                    st.info(f"Saved locally at `{zip_path}` (GDrive upload failed or not configured)")

                with st.expander("📄 View Scraped Data", expanded=False):
                    for i, product in enumerate(scraped_data, 1):
                        with st.container():
                            col_name, col_price = st.columns([3, 1])
                            with col_name:
                                st.markdown(
                                    f"**{i}. {product.get('product_name', 'Unknown')}**"
                                )
                                st.caption(
                                    f"🏭 {product.get('supplier_name', 'N/A')}  ·  "
                                    f"📍 {product.get('supplier_location', 'N/A')}"
                                )
                            with col_price:
                                price = product.get("price", "N/A")
                                unit = product.get("price_unit", "")
                                st.markdown(f"**₹ {price}** {unit}")

                            if st.toggle(f"Details", key=f"toggle_{i}"):
                                st.json(product)
                            st.markdown("---")

            if "terminal_output" in dir() and terminal_output:
                with st.expander("🖥️ Scraper Log", expanded=False):
                    st.code(terminal_output, language=None)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Setup Guide</div>', unsafe_allow_html=True)

    with st.expander("First-time setup instructions", expanded=False):
        st.markdown(
            """
        **1. Install dependencies**
        ```bash
        pip install -r requirement.txt
        ```

        **2. Configure Google Drive API**
        - Go to [Google Cloud Console](https://console.cloud.google.com/)
        - Create a project → Enable **Google Drive API**
        - Create OAuth 2.0 credentials → download `credentials.json`
        - Place `credentials.json` in the project folder

        **3. Run the scraper**
        ```bash
        streamlit run app.py
        ```
        On first run, a browser window will open to complete Google OAuth.
        After authentication, `token.json` is saved automatically for future runs.

        **Output format in Google Drive**
        ```
        scraped_files/
        └── indiamart_<category>_<timestamp>.zip
            ├── product1_supplier1_abc123.json
            └── product2_supplier2_def456.json
        ```
        """
        )


with tab_query:
    from rag_system import (
        get_database_stats,
        build_database_from_zip,
        query_products,
        clear_database,
        ollama_available,
    )

    stats = get_database_stats()
    ollama_ok = ollama_available()

    st.markdown('<div class="section-label">System Status</div>', unsafe_allow_html=True)

    stat_col1, stat_col2, stat_col3 = st.columns(3)

    with stat_col1:
        db_badge = "badge-success" if stats["count"] > 0 else "badge-warning"
        db_text = f"{stats['count']} products" if stats["count"] > 0 else "Empty"
        st.markdown(
            f'<span class="status-badge {db_badge}">🗄️ Vector DB: {db_text}</span>',
            unsafe_allow_html=True,
        )
    with stat_col2:
        ollama_badge = "badge-success" if ollama_ok else "badge-warning"
        ollama_text = "Connected" if ollama_ok else "Offline"
        st.markdown(
            f'<span class="status-badge {ollama_badge}">🤖 Ollama: {ollama_text}</span>',
            unsafe_allow_html=True,
        )
    with stat_col3:
        if stats["count"] > 0:
            if st.button("🗑️ Clear Database", type="secondary"):
                if clear_database():
                    st.success("Database cleared.")
                    st.rerun()

    if not ollama_ok:
        st.info(
            "Ollama is not running. Semantic search will still work, but AI-generated "
            "summaries will be disabled. Start Ollama with: `ollama serve`"
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Build Vector Database</div>', unsafe_allow_html=True)

    build_col1, build_col2 = st.columns([1, 1])

    with build_col1:
        uploaded_zip = st.file_uploader(
            "Upload a scraped ZIP file",
            type=["zip"],
            help="Upload a ZIP file downloaded from the Scraper tab",
            label_visibility="collapsed",
        )
        if uploaded_zip:
            if st.button("📦 Build from Uploaded ZIP", type="primary", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                    tmp.write(uploaded_zip.getbuffer())
                    tmp_path = tmp.name

                progress_bar = st.progress(0, text="Building database…")
                status_text = st.empty()

                def ui_progress(current, total, filename, skipped=False):
                    pct = current / total if total > 0 else 1.0
                    label = "skipped" if skipped else "indexed"
                    progress_bar.progress(pct, text=f"[{current}/{total}] {filename[:40]} — {label}")

                result = build_database_from_zip(tmp_path, progress_callback=ui_progress)
                os.unlink(tmp_path)

                if result["success"]:
                    progress_bar.progress(1.0, text="Done")
                    st.success(
                        f"✅ Indexed **{result['indexed']}** products  ·  "
                        f"{result['skipped']} duplicates skipped  ·  "
                        f"**{result['total_in_db']}** total in database"
                    )
                    st.rerun()
                else:
                    progress_bar.empty()
                    st.error(f"Failed to build database: {result.get('error')}")

    with build_col2:
        st.markdown("**Load from Google Drive**")
        st.caption("Downloads the most recent scraped ZIP from your Google Drive")
        if st.button("☁️ Load Latest from Google Drive", use_container_width=True):
            try:
                from gdrive_utils import get_latest_zip_from_gdrive

                with st.spinner("Connecting to Google Drive…"):
                    zip_path, zip_name = get_latest_zip_from_gdrive()

                if zip_path:
                    st.info(f"Downloaded: `{zip_name}`")
                    progress_bar = st.progress(0, text="Building database…")

                    def gdrive_progress(current, total, filename, skipped=False):
                        pct = current / total if total > 0 else 1.0
                        progress_bar.progress(
                            pct, text=f"[{current}/{total}] {filename[:40]}"
                        )

                    result = build_database_from_zip(
                        zip_path, progress_callback=gdrive_progress
                    )
                    if result["success"]:
                        progress_bar.progress(1.0, text="Done")
                        st.success(
                            f"✅ Indexed **{result['indexed']}** products — "
                            f"Total: **{result['total_in_db']}**"
                        )
                        st.rerun()
                    else:
                        st.error(f"Failed: {result.get('error')}")
                else:
                    st.warning("No ZIP files found in Google Drive › scraped_files")
            except FileNotFoundError:
                st.error("credentials.json not found. Set up Google Drive first.")
            except Exception as e:
                st.error(f"Google Drive error: {e}")

    if stats["count"] > 0:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Natural Language Query</div>', unsafe_allow_html=True)

        query_col, btn_col = st.columns([4, 1])
        with query_col:
            query_text = st.text_input(
                "Ask anything about the products",
                placeholder="e.g. Find stainless steel fittings under ₹500 from Mumbai",
                label_visibility="collapsed",
                key="query_input",
            )
        with btn_col:
            num_results = st.selectbox("Results", [3, 5, 10], index=1, label_visibility="collapsed")

        example_queries = [
            "Stainless steel pipe fittings",
            "Suppliers with TrustSEAL verified",
            "Products under ₹1000",
            "Elbow fittings from Gujarat",
        ]
        ex_cols = st.columns(len(example_queries))
        for col, eq in zip(ex_cols, example_queries):
            if col.button(f"💬 {eq}", use_container_width=True, key=f"eq_{eq}"):
                st.session_state["query_input"] = eq
                st.rerun()

        search_btn = st.button(
            "🔍 Search",
            type="primary",
            disabled=not query_text,
            use_container_width=False,
        )

        if search_btn and query_text:
            with st.spinner("Searching…"):
                result = query_products(query_text, n_results=num_results)

            if "error" in result:
                st.error(result["error"])
            else:
                if result.get("filters_extracted"):
                    filters_str = "  ·  ".join(
                        [f"{k}: {v}" for k, v in result["filters_extracted"].items()]
                    )
                    st.markdown(
                        f'<span class="status-badge badge-warning">🔧 Filters: {filters_str}</span>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<br><b>{len(result['results'])} results</b> from "
                    f"{result['total_in_db']} indexed products",
                    unsafe_allow_html=True,
                )

                for r in result["results"]:
                    meta = r["metadata"]
                    product_name = meta.get("product_name", "Unknown Product")
                    price = meta.get("price", "")
                    price_unit = meta.get("price_unit", "")
                    supplier = meta.get("supplier_name", "")
                    location = meta.get("supplier_location", "")
                    category = meta.get("category", "")
                    rating = meta.get("supplier_rating", "")
                    trustseal = meta.get("trustseal_verified", "")
                    url = meta.get("url", "")
                    similarity_pct = int(r["similarity"] * 100)

                    chips = []
                    if price and price not in ["Not found", "N/A", ""]:
                        chips.append(f"₹ {price} {price_unit}".strip())
                    if location and location != "Not found":
                        chips.append(f"📍 {location}")
                    if category:
                        chips.append(f"🏷️ {category}")
                    if rating and rating != "Not found":
                        chips.append(f"⭐ {rating}")
                    if trustseal not in ["Not found", "Not verified", ""]:
                        chips.append("✅ TrustSEAL")

                    chips_html = "".join(
                        [f'<span class="meta-chip">{c}</span>' for c in chips]
                    )
                    supplier_line = (
                        f'<span style="color:#8b949e;font-size:0.85rem;">'
                        f"🏭 {supplier}"
                        f"</span>"
                        if supplier and supplier != "Not found"
                        else ""
                    )
                    url_line = (
                        f'<a href="{url}" target="_blank" '
                        f'style="color:#58a6ff;font-size:0.8rem;text-decoration:none;">'
                        f"View on IndiaMART →</a>"
                        if url
                        else ""
                    )

                    st.markdown(
                        f"""
                        <div class="product-card">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                                <h4>{product_name}</h4>
                                <span style="color:#8b949e;font-size:0.78rem;background:rgba(88,166,255,0.08);
                                    border:1px solid rgba(88,166,255,0.2);border-radius:20px;
                                    padding:0.1rem 0.5rem;">
                                    {similarity_pct}% match
                                </span>
                            </div>
                            {supplier_line}
                            <div class="product-meta">{chips_html}</div>
                            <div style="margin-top:0.6rem;">{url_line}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if result.get("llm_answer"):
                    st.markdown(
                        f"""
                        <div class="ai-answer-box">
                            <h5>🤖 AI Summary</h5>
                            <p style="color:#e6edf3;line-height:1.6;margin:0;">
                                {result['llm_answer'].replace(chr(10), '<br>')}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
    else:
        st.info(
            "📭 The vector database is empty. Upload a scraped ZIP file above to build it, "
            "then you can query the product data here."
        )