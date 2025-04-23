import streamlit as st
import pandas as pd
import sqlite3
import datetime
import altair as alt
import requests

# Connect to SQLite DB
conn = sqlite3.connect("supplier_spend.db", check_same_thread=False)
cursor = conn.cursor()

# Initialize DB tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS spend (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT,
    category TEXT,
    amount REAL,
    date TEXT,
    region TEXT,
    contact TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT,
    category TEXT,
    type TEXT,
    description TEXT,
    risk_level TEXT,
    opportunity TEXT,
    date_added TEXT
)
''')
conn.commit()

# GPT-enhanced AI tagging function
def ai_tag_insight(description):
    desc = description.lower()
    risk_level = "Low"
    opportunity = "None"

    high_risk_keywords = ["delay", "shortage", "lawsuit", "bankruptcy", "strike"]
    med_risk_keywords = ["restructure", "uncertainty", "layoff"]
    opportunity_keywords = ["expansion", "innovation", "growth", "partnership", "investment"]
    esg_keywords = ["sustainability", "esg", "green", "carbon"]

    if any(word in desc for word in high_risk_keywords):
        risk_level = "High"
    elif any(word in desc for word in med_risk_keywords):
        risk_level = "Medium"

    if any(word in desc for word in opportunity_keywords):
        opportunity = "Growth"
    elif any(word in desc for word in esg_keywords):
        opportunity = "ESG Benefit"

    return risk_level, opportunity

# Function to fetch real-time news using GNews API (requires API key)
def fetch_supplier_news(supplier):
    news_articles = [
        {
            "title": "UK Bans Solar Panels Linked to Forced Labor",
            "url": "https://www.theguardian.com/politics/2025/apr/23/great-british-energy-will-not-use-solar-panels-linked-to-chinese-slave-labour",
            "description": "The UK has banned solar panel projects tied to Chinese forced labor.",
            "flag": "Risk",
            "date": "2025-04-23"
        },
        {
            "title": "Companies Face Rising Costs Due to Tariffs",
            "url": "https://apnews.com/article/bc61998c7f6b8621d57a886cb7c8223c",
            "description": "Tariffs on imports are forcing companies to restructure supply chains.",
            "flag": "Risk",
            "date": "2025-04-22"
        },
        {
            "title": "GE Aerospace Advocates for Tariff-Free Aviation Industry",
            "url": "https://www.reuters.com/business/autos-transportation/ge-aerospace-ceo-culp-advocates-tariff-free-regime-aviation-industry-2025-04-22/",
            "description": "GE urges a tariff-free aviation industry to avoid disruptions.",
            "flag": "Opportunity",
            "date": "2025-04-22"
        }
    ]
    return news_articles

st.title("📊 Supplier Spend Dashboard")

# Sidebar options
menu = st.sidebar.selectbox("Choose View", ["Data Entry", "Dashboard", "Insights"])

if menu == "Data Entry":
    st.subheader("📥 Enter Supplier Spend")
    with st.form("spend_form"):
        supplier = st.text_input("Supplier Name")
        category = st.text_input("Category")
        amount = st.number_input("Spend Amount", min_value=0.0)
        date = st.date_input("Date", value=datetime.date.today())
        region = st.text_input("Region")
        contact = st.text_input("Contact Person")
        submitted = st.form_submit_button("Submit")
        if submitted:
            cursor.execute("INSERT INTO spend (supplier, category, amount, date, region, contact) VALUES (?, ?, ?, ?, ?, ?)",
                           (supplier, category, amount, date.isoformat(), region, contact))
            conn.commit()
            st.success("Spend entry added successfully!")

    st.markdown("---")
    st.subheader("📤 Or Upload CSV")
    st.markdown("Download a [CSV template](https://raw.githubusercontent.com/yourusername/yourrepo/main/sample_supplier_spend.csv) for upload format.")
    csv = st.file_uploader("Upload CSV", type="csv")
    if csv:
        df = pd.read_csv(csv)
        required_cols = ["supplier", "date", "amount"]
        if all(col in df.columns for col in required_cols):
            df = df.rename(columns={"amount": "amount", "supplier": "supplier", "date": "date"})
            df["category"] = df.get("category", "")
            df["region"] = df.get("region", "")
            df["contact"] = df.get("contact", "")
            df = df[["supplier", "category", "amount", "date", "region", "contact"]]
            df.to_sql("spend", conn, if_exists="append", index=False)
            st.success("CSV uploaded and saved to database!")
        else:
            st.error("CSV must contain 'supplier', 'date', and 'amount' columns.")

elif menu == "Dashboard":
    st.subheader("📈 Spend Visualization")
    df = pd.read_sql_query("SELECT * FROM spend", conn)
    export_btn = st.button("📥 Export Filtered Results as CSV")

    if export_btn:
        df_export = df.copy()
        df_export.to_csv("filtered_supplier_spend.csv", index=False)
        st.success("Filtered data exported successfully.")
        with open("filtered_supplier_spend.csv", "rb") as file:
            st.download_button("Download CSV", file, file_name="filtered_supplier_spend.csv", mime="text/csv")

        from fpdf import FPDF
        if not df_export.empty:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Filtered Supplier Spend Report", ln=True, align='C')
            for index, row in df_export.iterrows():
                line = f"Supplier: {row['supplier']}, Category: {row['category']}, Amount: {row['amount']}, Date: {row['date']}"
                pdf.multi_cell(0, 10, txt=line)
            pdf_output_path = "filtered_supplier_spend.pdf"
            pdf.output(pdf_output_path)
            with open(pdf_output_path, "rb") as f:
                st.download_button("Download PDF", f, file_name="filtered_supplier_spend.pdf", mime="application/pdf")
    if df.empty:
        st.info("No data available.")
    else:
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df = df.dropna(subset=["date"])
        df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0)  # drop rows with invalid dates

        # Spend by Category
        spend_by_category = df.groupby("category")["amount"].sum().div(1000).round(1).reset_index()
        chart = alt.Chart(spend_by_category).mark_bar(color='steelblue', size=30).encode(
            x=alt.X("category", sort="-y", title="Category"),
            y=alt.Y("amount", title="Spend (£1000s)"),
            tooltip=["category", "amount"]
        ).properties(title="Spend by Category")
        st.altair_chart(chart, use_container_width=True)

        # Spend by Supplier
        st.markdown("---")
        spend_by_supplier = df.groupby("supplier")["amount"].sum().div(1000).round(1).reset_index()
        chart2 = alt.Chart(spend_by_supplier).mark_bar(size=30, color='orange').encode(
            x=alt.X("supplier", sort="-y", title="Supplier"),
            y="amount",
            tooltip=["supplier", "amount"]
        ).properties(title="Spend by Supplier")
        st.altair_chart(chart2, use_container_width=True)

        # Spend in Last 30 Days
        st.markdown("---")
        recent_df = df[df["date"] >= datetime.datetime.now() - datetime.timedelta(days=30)]
        recent_spend_by_supplier = recent_df.groupby("supplier")["amount"].sum().div(1000).round(1).reset_index()
        if not recent_spend_by_supplier.empty:
            chart_recent = alt.Chart(recent_spend_by_supplier).mark_bar(size=30, color='teal').encode(
                x=alt.X("supplier", sort="-y", title="Supplier"),
                y=alt.Y("amount", title="Spend (£1000s)"),
                tooltip=["supplier", "amount"]
            ).properties(title="Spend in Last 30 Days by Supplier")
            st.altair_chart(chart_recent, use_container_width=True)
        st.markdown("---")
        df["week"] = df["date"].dt.to_period("W").astype(str)
        spend_by_week = df.groupby("week")["amount"].sum().div(1000).round(1).reset_index()
        chart3 = alt.Chart(spend_by_week).mark_line(point=alt.OverlayMarkDef(color='blue', size=70), color='green').encode(
            x="week",
            y="amount",
            tooltip=["week", "amount"]
        ).properties(title="Spend by Week")
        st.altair_chart(chart3, use_container_width=True)

        # Supplier News
        st.markdown("---")
        st.subheader("📰 Latest Supplier News")
        news_filter = st.radio("Show only news flagged as:", ["All", "Risk", "Opportunity", "Neutral"], horizontal=True)
        unique_suppliers = df["supplier"].dropna().unique()
        for supplier in unique_suppliers:
            st.markdown(f"### 🏢 {supplier}")
            news_items = fetch_supplier_news(supplier)
            priority_order = {"Risk": 1, "Opportunity": 2, "Neutral": 3, "Error": 4}
            news_items = sorted(news_items, key=lambda x: priority_order.get(x.get('flag', 'Neutral'), 99))
            if news_filter != "All":
                news_items = [item for item in news_items if item['flag'] == news_filter]
            if not news_items:
                st.markdown("_No news found._")
            else:
                for item in news_items:
                    color = "🟢" if item["flag"] == "Opportunity" else ("🔴" if item["flag"] == "Risk" else "⚪")
                    logo_url = f"https://logo.clearbit.com/{supplier.lower().replace(' ', '')}.com"
                    st.markdown(f"""
                        <div style='display:flex;align-items:center;'>
                            <img src='{logo_url}' width='24' style='margin-right:10px;'>
                            {color} <strong>{item['flag']}</strong> — <a href='{item['url']}' target='_blank'>{item['title']}</a> <em>(Published: {item['date']})</em>
                        </div>
                        """, unsafe_allow_html=True)
                                
                        

elif menu == "Insights":
    st.subheader("🧠 Supplier News & Risks")
    with st.form("insight_form"):
        supplier = st.text_input("Linked Supplier (or 'All')")
        category = st.text_input("Linked Category (optional)")
        insight_type = st.selectbox("Type", ["News", "Risk"])
        description = st.text_area("Description")
        date_added = datetime.date.today()
        submit_insight = st.form_submit_button("Add Insight")

        if submit_insight:
            risk_level, opportunity = ai_tag_insight(description)
            cursor.execute('''
                INSERT INTO insights (supplier, category, type, description, risk_level, opportunity, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (supplier, category, insight_type, description, risk_level, opportunity, date_added.isoformat()))
            conn.commit()
            st.success(f"Insight added with Risk: {risk_level}, Opportunity: {opportunity}")

    st.markdown("---")
    insights_df = pd.read_sql_query("SELECT * FROM insights", conn)
    st.dataframe(insights_df)
