import streamlit as st
import yfinance as yf
import altair as alt
from backend.service.macd import calculate_macd, calculate_custom_macd, create_macd_chart, create_moving_averages_chart

# Set page config
st.set_page_config(page_title="Stock Analysis Dashboard", page_icon="📈", layout="wide")

# App title and description
st.title("Stock Analysis Dashboard")
st.markdown("Analyze stock price movements with custom MACD indicators")

# Sidebar for controls
st.sidebar.header("Settings")

# Ticker selection
default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "JNJ", "WMT", "PG"]
selected_ticker = st.sidebar.selectbox("Select Stock", default_tickers, index=0)

# Time period selection
time_periods = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "2 Years": "2y",
    "5 Years": "5y",
}
selected_period = st.sidebar.selectbox("Select Time Period", list(time_periods.keys()))
period = time_periods[selected_period]

# MACD parameters
st.sidebar.header("MACD Parameters")

col1, col2 = st.sidebar.columns(2)
with col1:
    fast_ma = st.number_input("Fast MA Period", min_value=5, max_value=50, value=10)
    slow_ma = st.number_input("Slow MA Period", min_value=10, max_value=100, value=30)
with col2:
    longest_ma = st.number_input("Longest MA Period", min_value=20, max_value=200, value=60)
    signal_period = st.number_input("Signal Period", min_value=5, max_value=20, value=9)


# Cache function for data fetching
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_stock_data(ticker, period="1y"):
    """Fetch stock data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            st.error(f"No data found for ticker {ticker}")
            return None
        return df
    except Exception as e:
        st.error(f"Failed to fetch data for {ticker}: {str(e)}")
        return None


# Create price chart
def create_price_chart(df, ticker):
    """Create price chart with moving averages"""
    # Reset index to make Date a column
    df_reset = df.reset_index()

    # Create selection for hover
    nearest = alt.selection_point(nearest=True, on="mouseover", fields=["Date"], empty=False)

    # Create base chart
    base = alt.Chart(df_reset).encode(x=alt.X("Date:T", title="Date"))

    # Price line
    price_line = base.mark_line().encode(
        y=alt.Y("Close:Q", title="Price", scale=alt.Scale(zero=False)), color=alt.value("black")
    )

    # Moving average lines
    ma10_line = base.mark_line(strokeDash=[1, 0]).encode(y=f"MA_{fast_ma}:Q", color=alt.value("blue"))

    ma30_line = base.mark_line(strokeDash=[5, 5]).encode(y=f"MA_{slow_ma}:Q", color=alt.value("green"))

    ma60_line = base.mark_line(strokeDash=[2, 2]).encode(y=f"MA_{longest_ma}:Q", color=alt.value("red"))

    # Add selection and tooltip elements
    selectors = (
        alt.Chart(df_reset)
        .mark_point()
        .encode(
            x="Date:T",
            opacity=alt.value(0),
        )
        .add_params(nearest)
    )

    # Vertical rule
    rule = base.mark_rule(color="gray").encode(x="Date:T").transform_filter(nearest)

    # Create tooltip points
    price_points = (
        price_line.mark_point(color="black", size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    ma10_points = (
        ma10_line.mark_point(color="blue", size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    ma30_points = (
        ma30_line.mark_point(color="green", size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    ma60_points = (
        ma60_line.mark_point(color="red", size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    # Combine all elements
    chart = (
        alt.layer(
            price_line,
            ma10_line,
            ma30_line,
            ma60_line,
            selectors,
            rule,
            price_points,
            ma10_points,
            ma30_points,
            ma60_points,
        )
        .encode(
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Close:Q", title="Price", format=".2f"),
                alt.Tooltip(f"MA_{fast_ma}:Q", title=f"{fast_ma}-day MA", format=".2f"),
                alt.Tooltip(f"MA_{slow_ma}:Q", title=f"{slow_ma}-day MA", format=".2f"),
                alt.Tooltip(f"MA_{longest_ma}:Q", title=f"{longest_ma}-day MA", format=".2f"),
            ]
        )
        .properties(title=f"{ticker} - Price with Moving Averages", width=800, height=400)
    )

    return chart


# Fetch the data
df = get_stock_data(selected_ticker, period)

# Continue only if we have data
if df is not None:
    # Company info
    company_info = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com, Inc.",
        "META": "Meta Platforms, Inc.",
        "TSLA": "Tesla, Inc.",
        "NVDA": "NVIDIA Corporation",
        "JPM": "JPMorgan Chase & Co.",
        "V": "Visa Inc.",
        "JNJ": "Johnson & Johnson",
        "WMT": "Walmart Inc.",
        "PG": "Procter & Gamble Company",
    }

    # Display company name
    st.header(f"{company_info.get(selected_ticker, 'Unknown Company')} ({selected_ticker})")

    # Calculate MACD values
    df_custom_macd = calculate_custom_macd(df, fast_ma, slow_ma, longest_ma, signal_period)
    df_macd = calculate_macd(df)

    # Stats row
    col1, col2, col3, col4 = st.columns(4)

    current_price = df["Close"].iloc[-1]

    # Weekly change
    week_ago_idx = -6 if len(df) >= 6 else 0
    week_ago_price = df["Close"].iloc[week_ago_idx]
    weekly_change = ((current_price - week_ago_price) / week_ago_price) * 100

    # Monthly change
    month_ago_idx = -21 if len(df) >= 21 else 0
    month_ago_price = df["Close"].iloc[month_ago_idx]
    monthly_change = ((current_price - month_ago_price) / month_ago_price) * 100

    # MACD signal
    last_custom_macd = df_custom_macd["macd_10_30"].iloc[-1]
    last_custom_signal = df_custom_macd["signal_10_30"].iloc[-1]
    last_macd = df_macd["macd"].iloc[-1]
    last_signal = df_macd["signal"].iloc[-1]

    if last_macd > last_signal and last_custom_macd > last_custom_signal and last_macd > 0:
        macd_signal = "Bullish"
        signal_color = "green"
    elif last_macd < last_signal and last_custom_macd < last_custom_macd and last_macd < 0:
        macd_signal = "Bearish"
        signal_color = "red"
    else:
        macd_signal = "Neutral"
        signal_color = "orange"

    with col1:
        st.metric("Current Price", f"${current_price:.2f}")

    with col2:
        weekly_delta = f"{weekly_change:.2f}%"
        st.metric("Weekly Change", weekly_delta, delta=weekly_delta)

    with col3:
        monthly_delta = f"{monthly_change:.2f}%"
        st.metric("Monthly Change", monthly_delta, delta=monthly_delta)

    with col4:
        st.markdown(f"**MACD Signal**")
        st.markdown(f"<h3 style='color:{signal_color}'>{macd_signal}</h3>", unsafe_allow_html=True)

    # Tabs for different chart views
    tab1, tab2 = st.tabs(["Price & MACD", "Moving Averages"])

    with tab1:
        # Create and display price chart
        price_chart = create_macd_chart(df_macd)
        st.altair_chart(price_chart, use_container_width=True)

    with tab2:
        ma_chart = create_moving_averages_chart(df_custom_macd)
        st.altair_chart(ma_chart, use_container_width=True)

    # Additional details section
    with st.expander("Trading Volume"):
        # Create volume chart
        volume_data = df.reset_index()
        volume_chart = (
            alt.Chart(volume_data)
            .mark_bar()
            .encode(
                x="Date:T",
                y="Volume:Q",
                color=alt.condition(alt.datum.Close > alt.datum.Open, alt.value("green"), alt.value("red")),
                tooltip=["Date:T", "Volume:Q", "Open:Q", "Close:Q", "High:Q", "Low:Q"],
            )
            .properties(title=f"{selected_ticker} - Trading Volume", width=800, height=300)
        )
        st.altair_chart(volume_chart, use_container_width=True)

    # Raw data
    with st.expander("Raw Data"):
        st.dataframe(df)

    # Download options
    st.download_button(
        label="Download CSV",
        data=df.to_csv().encode("utf-8"),
        file_name=f"{selected_ticker}_stock_data.csv",
        mime="text/csv",
    )
