import streamlit as st
import pandas as pd
import sqlite3
import datetime
import altair as alt

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
        spend_by_category = df.groupby("category")["amount"].sum().reset_index()
        chart = alt.Chart(spend_by_category).mark_bar().encode(
            x="category",
            y="amount",
            tooltip=["category", "amount"]
        ).properties(title="Spend by Category")
        st.altair_chart(chart, use_container_width=True)

        st.markdown("---")
        spend_by_supplier = df.groupby("supplier")["amount"].sum().reset_index()
        chart2 = alt.Chart(spend_by_supplier).mark_bar().encode(
            x="supplier",
            y="amount",
            tooltip=["supplier", "amount"]
        ).properties(title="Spend by Supplier")
        st.altair_chart(chart2, use_container_width=True)

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
