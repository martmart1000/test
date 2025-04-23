import streamlit as st
import pandas as pd
import sqlite3
import datetime
import altair as alt
import requests

# Connect to SQLite DB
conn = sqlite3.connect("supplier_spend.db")
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
    api_key = "YOUR_GNEWS_API_KEY"  # Replace with your actual API key
    url = f"https://gnews.io/api/v4/search?q={supplier}&lang=en&token={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        news_items = []
        for article in articles[:3]:  # Limit to top 3 articles
            title = article["title"]
            link = article["url"]
            desc = article.get("description", "")
            risk_level, opportunity = ai_tag_insight(desc)
            flag = "Opportunity" if opportunity != "None" else ("Risk" if risk_level in ["High", "Medium"] else "Neutral")
            news_items.append({"title": title, "url": link, "flag": flag})
        return news_items
    except:
        return []

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
    csv = st.file_uploader("Upload CSV", type="csv")
    if csv:
        df = pd.read_csv(csv)
        df.to_sql("spend", conn, if_exists="append", index=False)
        st.success("CSV uploaded and saved to database!")

elif menu == "Dashboard":
    st.subheader("📈 Spend Visualization")
    df = pd.read_sql_query("SELECT * FROM spend", conn)
    if df.empty:
        st.info("No data available.")
    else:
        df["date"] = pd.to_datetime(df["date"])

        # Spend by Category
        spend_by_category = df.groupby("category")["amount"].sum().reset_index()
        chart = alt.Chart(spend_by_category).mark_bar().encode(
            x="category",
            y="amount",
            tooltip=["category", "amount"]
        ).properties(title="Spend by Category")
        st.altair_chart(chart, use_container_width=True)

        # Spend by Supplier
        st.markdown("---")
        spend_by_supplier = df.groupby("supplier")["amount"].sum().reset_index()
        chart2 = alt.Chart(spend_by_supplier).mark_bar().encode(
            x="supplier",
