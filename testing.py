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

# Simulated AI tagging function
def ai_tag_insight(description):
    desc = description.lower()
    risk_level = "Low"
    opportunity = "None"
    if any(word in desc for word in ["delay", "shortage", "lawsuit"]):
        risk_level = "High"
    elif any(word in desc for word in ["restructure", "uncertainty"]):
        risk_level = "Medium"

    if any(word in desc for word in ["expansion", "innovation", "growth"]):
        opportunity = "Growth"
    elif "sustainability" in desc:
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
            # Tag with flags
            if any(word in desc.lower() for word in ["growth", "partnership", "launch"]):
                flag = "Opportunity"
            elif any(word in desc.lower() for word in ["disruption", "layoff", "risk"]):
                flag = "Risk"
            else:
                flag = "Neutral"
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
