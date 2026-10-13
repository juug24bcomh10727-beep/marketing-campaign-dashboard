import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Marketing Campaign Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Digital Marketing Campaign Performance Dashboard")
st.caption(
    "Explore marketing effectiveness, campaign returns, "
    "regional performance and business opportunities."
)

# ---------- LOAD DATA ----------
uploaded_file = st.sidebar.file_uploader(
    "Upload your marketing Excel file",
    type=["xlsx", "xls"]
)

if uploaded_file is None:
    st.info(
        "Upload Marketing_Campaign_Analysis_Dashboard.xlsx "
        "to start exploring the dashboard."
    )
    st.stop()

try:
    excel_file = pd.ExcelFile(uploaded_file)
    sheet = "Raw_Data" if "Raw_Data" in excel_file.sheet_names else excel_file.sheet_names[0]
    df = pd.read_excel(uploaded_file, sheet_name=sheet)
except Exception as e:
    st.error(f"Unable to read the Excel file: {e}")
    st.stop()

required = [
    "Date", "Campaign_ID", "Impressions", "Clicks",
    "Conversions", "Spend", "Revenue"
]
missing = [col for col in required if col not in df.columns]

if missing:
    st.error(f"Required columns are missing: {missing}")
    st.stop()

# ---------- DATA PREPARATION ----------
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

numeric_cols = [
    "Impressions", "Clicks", "Conversions", "Spend", "Revenue"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["Date", "Campaign_ID"] + numeric_cols).copy()

# Add fallback values if optional columns are absent
for col in [
    "Campaign_Name", "Channel", "Region", "Product_Category",
    "Campaign_Type", "Target_Audience"
]:
    if col not in df.columns:
        df[col] = "Unknown"
    else:
        df[col] = df[col].fillna("Unknown").astype(str)

if df.empty:
    st.error("No valid records remain after data preparation.")
    st.stop()

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Dashboard Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date)
].copy()

def multiselect_filter(frame, column, label):
    options = sorted(frame[column].dropna().unique().tolist())
    selected = st.sidebar.multiselect(
        label, options, default=options
    )
    return frame[frame[column].isin(selected)]

for column, label in [
    ("Channel", "Marketing channel"),
    ("Region", "Region"),
    ("Product_Category", "Product category"),
    ("Campaign_Type", "Campaign type"),
    ("Campaign_ID", "Campaign")
]:
    filtered = multiselect_filter(filtered, column, label)

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

# ---------- KPI CALCULATIONS ----------
impressions = filtered["Impressions"].sum()
clicks = filtered["Clicks"].sum()
conversions = filtered["Conversions"].sum()
spend = filtered["Spend"].sum()
revenue = filtered["Revenue"].sum()

ctr = clicks / impressions * 100 if impressions else 0
conversion_rate = conversions / clicks * 100 if clicks else 0
cpc = spend / clicks if clicks else 0
cost_per_conversion = spend / conversions if conversions else 0
roas = revenue / spend if spend else np.nan
advertising_roi = (revenue - spend) / spend * 100 if spend else np.nan

# ---------- KPI CARDS ----------
st.subheader("Key Performance Indicators")

k1, k2, k3 = st.columns(3)
k1.metric("Total Impressions", f"{impressions:,.0f}")
k2.metric("Total Clicks", f"{clicks:,.0f}")
k3.metric("Total Conversions", f"{conversions:,.0f}")

k4, k5, k6 = st.columns(3)
k4.metric("Advertising Spend", f"{spend:,.2f}")
k5.metric("Attributed Revenue", f"{revenue:,.2f}")
k6.metric("ROAS", f"{roas:.2f}x" if pd.notna(roas) else "N/A")

k7, k8, k9 = st.columns(3)
k7.metric("Click-through Rate", f"{ctr:.2f}%")
k8.metric("Conversion Rate", f"{conversion_rate:.2f}%")
k9.metric(
    "Cost per Conversion",
    f"{cost_per_conversion:,.2f}"
    if conversions else "N/A"
)

st.caption(
    "ROAS = attributed revenue ÷ advertising spend. "
    "ROI here considers advertising spend only, not all business costs."
)

# ---------- GROUPED PERFORMANCE DATA ----------
channel = filtered.groupby("Channel", as_index=False).agg(
    Spend=("Spend", "sum"),
    Revenue=("Revenue", "sum"),
    Clicks=("Clicks", "sum"),
    Conversions=("Conversions", "sum"),
    Impressions=("Impressions", "sum")
)

channel["ROAS"] = channel["Revenue"] / channel["Spend"].replace(0, np.nan)
channel["CTR (%)"] = (
    channel["Clicks"] / channel["Impressions"].replace(0, np.nan) * 100
)
channel["Conversion Rate (%)"] = (
    channel["Conversions"] / channel["Clicks"].replace(0, np.nan) * 100
)
channel["Cost per Conversion"] = (
    channel["Spend"] / channel["Conversions"].replace(0, np.nan)
)

campaign = filtered.groupby(
    ["Campaign_ID", "Campaign_Name", "Channel"], as_index=False
).agg(
    Spend=("Spend", "sum"),
    Revenue=("Revenue", "sum"),
    Clicks=("Clicks", "sum"),
    Conversions=("Conversions", "sum"),
    Impressions=("Impressions", "sum")
)

campaign["ROAS"] = campaign["Revenue"] / campaign["Spend"].replace(0, np.nan)
campaign["Cost per Conversion"] = (
    campaign["Spend"] / campaign["Conversions"].replace(0, np.nan)
)

# ---------- BUSINESS VISUALIZATIONS ----------
st.divider()
st.subheader("Channel Performance")

left, right = st.columns(2)

with left:
    fig = px.bar(
        channel.sort_values("Revenue"),
        x="Revenue", y="Channel",
        orientation="h",
        title="Attributed Revenue by Channel",
        labels={"Revenue": "Revenue", "Channel": "Marketing Channel"},
        hover_data=["Spend", "Conversions"]
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    roas_data = channel.dropna(subset=["ROAS"]).sort_values("ROAS")
    fig = px.bar(
        roas_data, x="Channel", y="ROAS",
        title="Return on Advertising Spend by Channel",
        labels={"ROAS": "ROAS (times)", "Channel": "Marketing Channel"},
        hover_data=["Spend", "Revenue"]
    )
    fig.add_hline(y=1, line_dash="dash", annotation_text="ROAS = 1")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly Trends")

monthly = filtered.assign(
    Month=filtered["Date"].dt.to_period("M").dt.to_timestamp()
).groupby("Month", as_index=False).agg(
    Spend=("Spend", "sum"),
    Revenue=("Revenue", "sum"),
    Clicks=("Clicks", "sum"),
    Conversions=("Conversions", "sum")
)

monthly["ROAS"] = monthly["Revenue"] / monthly["Spend"].replace(0, np.nan)

left, right = st.columns(2)

with left:
    monthly_long = monthly.melt(
        id_vars="Month",
        value_vars=["Spend", "Revenue"],
        var_name="Metric",
        value_name="Amount"
    )
    fig = px.line(
        monthly_long, x="Month", y="Amount", color="Metric",
        markers=True, title="Monthly Spend vs Revenue"
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.line(
        monthly, x="Month", y="ROAS", markers=True,
        title="Monthly ROAS",
        labels={"ROAS": "ROAS (times)", "Month": "Month"}
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Campaign Performance")

left, right = st.columns(2)

with left:
    top_revenue = campaign.nlargest(10, "Revenue").sort_values("Revenue")
    fig = px.bar(
        top_revenue, x="Revenue", y="Campaign_Name",
        orientation="h", color="Channel",
        title="Top 10 Campaigns by Revenue",
        labels={"Revenue": "Revenue", "Campaign_Name": "Campaign"}
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    efficient = campaign[
        (campaign["Spend"] > 0) & campaign["ROAS"].notna()
    ].nlargest(10, "ROAS").sort_values("ROAS")

    fig = px.bar(
        efficient, x="ROAS", y="Campaign_Name",
        orientation="h", color="Channel",
        title="Top 10 Campaigns by ROAS",
        labels={"ROAS": "ROAS (times)", "Campaign_Name": "Campaign"}
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- MANAGEMENT ATTENTION ----------
st.subheader("Areas for Management Attention")

low_return = campaign[
    (campaign["Spend"] > 0) & (campaign["ROAS"] < 1)
].sort_values("ROAS")

if low_return.empty:
    st.success(
        "No campaigns with positive spend and ROAS below 1 "
        "were found in the current filter selection."
    )
else:
    st.warning(
        f"{len(low_return)} campaign(s) have ROAS below 1. "
        "Review campaign objectives, attribution and other costs "
        "before making budget decisions."
    )
    st.dataframe(
        low_return[
            ["Campaign_ID", "Campaign_Name", "Channel",
             "Spend", "Revenue", "ROAS", "Conversions"]
        ].round(2),
        use_container_width=True,
        hide_index=True
    )

st.subheader("Detailed Performance Tables")

tab1, tab2, tab3 = st.tabs(
    ["By Channel", "By Campaign", "By Month"]
)

with tab1:
    st.dataframe(
        channel.sort_values("Revenue", ascending=False).round(2),
        use_container_width=True, hide_index=True
    )

with tab2:
    st.dataframe(
        campaign.sort_values("Revenue", ascending=False).round(2),
        use_container_width=True, hide_index=True
    )

with tab3:
    st.dataframe(
        monthly.round(2),
        use_container_width=True, hide_index=True
    )

# ---------- DOWNLOAD FILTERED DATA ----------
st.download_button(
    "Download filtered data as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_marketing_campaign_data.csv",
    mime="text/csv"
)

st.caption(
    "Note: ROAS and conversion metrics are calculated from aggregated "
    "underlying measures. Revenue exceeding advertising spend does not "
    "necessarily imply overall business profitability."
)
