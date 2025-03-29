import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt
from datetime import datetime, timedelta


def get_stock_data(ticker, period="1y"):
    """
    Fetch stock data using yfinance

    Parameters:
    ticker (str): Stock ticker symbol
    period (str): Period to fetch data for (default: 1 year)

    Returns:
    pd.DataFrame: DataFrame with stock data
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    return df


def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate MACD and signal line

    Parameters:
    df (pd.DataFrame): DataFrame with stock data
    fast_period (int): Fast EMA period
    slow_period (int): Slow EMA period
    signal_period (int): Signal line period

    Returns:
    pd.DataFrame: DataFrame with MACD data
    """
    # Make a copy of the dataframe to avoid modifying the original
    df_macd = df.copy()

    # Calculate fast and slow EMAs
    df_macd["ema_fast"] = df_macd["Close"].ewm(span=fast_period, adjust=False).mean()
    df_macd["ema_slow"] = df_macd["Close"].ewm(span=slow_period, adjust=False).mean()

    # Calculate MACD line
    df_macd["macd"] = df_macd["ema_fast"] - df_macd["ema_slow"]

    # Calculate signal line
    df_macd["signal"] = df_macd["macd"].ewm(span=signal_period, adjust=False).mean()

    # Calculate histogram
    df_macd["histogram"] = df_macd["macd"] - df_macd["signal"]

    return df_macd


def calculate_custom_macd(df, fast_ma=10, slow_ma=30, longest_ma=60, signal_period=9):
    """
    Calculate custom MACD using specified moving averages

    Parameters:
    df (pd.DataFrame): DataFrame with stock data
    fast_ma (int): Fast moving average period
    slow_ma (int): Slow moving average period
    longest_ma (int): Longest moving average period
    signal_period (int): Signal line period

    Returns:
    pd.DataFrame: DataFrame with custom MACD data
    """
    # Make a copy of the dataframe to avoid modifying the original
    df_custom = df.copy()

    # Calculate moving averages (using SMA for clarity)
    df_custom[f"MA_{fast_ma}"] = df_custom["Close"].rolling(window=fast_ma).mean()
    df_custom[f"MA_{slow_ma}"] = df_custom["Close"].rolling(window=slow_ma).mean()
    df_custom[f"MA_{longest_ma}"] = df_custom["Close"].rolling(window=longest_ma).mean()

    # Calculate custom MACD lines
    df_custom["macd_10_30"] = df_custom[f"MA_{fast_ma}"] - df_custom[f"MA_{slow_ma}"]
    df_custom["macd_30_60"] = df_custom[f"MA_{slow_ma}"] - df_custom[f"MA_{longest_ma}"]
    df_custom["macd_10_60"] = df_custom[f"MA_{fast_ma}"] - df_custom[f"MA_{longest_ma}"]

    # Calculate signal lines
    df_custom["signal_10_30"] = df_custom["macd_10_30"].rolling(window=signal_period).mean()
    df_custom["signal_30_60"] = df_custom["macd_30_60"].rolling(window=signal_period).mean()
    df_custom["signal_10_60"] = df_custom["macd_10_60"].rolling(window=signal_period).mean()

    return df_custom


def create_macd_chart(df):
    """
    Create an Altair chart with MACD including enhanced tooltips and vertical rule on hover

    Parameters:
    df (pd.DataFrame): DataFrame with MACD data

    Returns:
    alt.Chart: Altair chart with MACD visualization
    """
    # Reset index to make Date a column
    df_reset = df.reset_index()

    # Create selection for hover
    nearest = alt.selection_point(nearest=True, on="mouseover", fields=["Date"], empty=False)

    # Create legend selection
    # selection = alt.selection_point(fields=["Ticker"], bind="legend")

    # Base chart for price
    base = alt.Chart(df_reset).encode(x=alt.X("Date:T", title="Date"))

    # Price line
    price_line = base.mark_line().encode(
        y=alt.Y("Close:Q", title="Price", scale=alt.Scale(zero=False)), color=alt.value("black")
    )

    # Transparent selectors across the chart
    selectors = (
        alt.Chart(df_reset)
        .mark_point()
        .encode(
            x="Date:T",
            opacity=alt.value(0),
            # opacity=alt.when(selection).then(alt.value(1)).otherwise(alt.value(0.2)),
        )
        .add_params(nearest)
        # .add_params(selection)
    )

    # Vertical rule that follows mouse
    rule = base.mark_rule(color="gray").encode(x="Date:T").transform_filter(nearest)

    # Points on the price line that appear on hover
    price_points = (
        price_line.mark_point(color="green", size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    # Price tooltip
    price_tooltip = (
        base.mark_text(align="left", dx=5, dy=-5, fontSize=12)
        .encode(x="Date:T", y="Close:Q", text=alt.condition(nearest, alt.Text("Close:Q", format=".2f"), alt.value("")))
        .transform_filter(nearest)
    )

    # Complete price chart with all layers
    price_chart = (
        alt.layer(price_line, selectors, rule, price_points, price_tooltip)
        .encode(
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Close:Q", title="Price", format=".2f"),
                alt.Tooltip("Volume:Q", title="Volume", format=","),
            ]
        )
        .properties(title="Stock Price", width=800, height=300)
    )

    # MACD base chart
    macd_base = alt.Chart(df_reset).encode(x=alt.X("Date:T", title="Date"))

    # MACD line
    macd_line = macd_base.mark_line().encode(y=alt.Y("macd:Q", title="MACD"), color=alt.value("blue"))

    # Signal line
    signal_line = macd_base.mark_line().encode(y="signal:Q", color=alt.value("red"))

    # Histogram
    histogram = macd_base.mark_bar().encode(
        y="histogram:Q", color=alt.condition(alt.datum.histogram > 0, alt.value("green"), alt.value("red"))
    )

    # MACD selectors
    macd_selectors = macd_base.mark_point().encode(x="Date:T", opacity=alt.value(0)).add_params(nearest)

    # MACD rule
    macd_rule = macd_base.mark_rule(color="gray").encode(x="Date:T").transform_filter(nearest)

    # Points on the MACD line
    macd_points = (
        macd_line.mark_point(size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    # Points on the signal line
    signal_points = (
        signal_line.mark_point(size=50)
        .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
        .transform_filter(nearest)
    )

    # MACD tooltip
    macd_tooltip = (
        macd_base.mark_text(align="left", dx=5, dy=-5, fontSize=12)
        .encode(x="Date:T", y="macd:Q", text=alt.condition(nearest, alt.Text("macd:Q", format=".2f"), alt.value("")))
        .transform_filter(nearest)
    )

    # Complete MACD chart with all layers
    macd_plot = (
        alt.layer(
            macd_line, signal_line, histogram, macd_selectors, macd_rule, macd_points, signal_points, macd_tooltip
        )
        .encode(
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("macd:Q", title="MACD", format=".2f"),
                alt.Tooltip("signal:Q", title="Signal", format=".2f"),
                alt.Tooltip("histogram:Q", title="Histogram", format=".2f"),
            ]
        )
        .properties(title="MACD", width=800, height=200)
    )

    # Combine price and MACD charts
    final_chart = alt.vconcat(price_chart, macd_plot).resolve_scale(y="independent")

    return final_chart


def create_moving_averages_chart(df):
    """
    Create an Altair chart with custom MACD using 10, 30, and 60 day moving averages
    with enhanced tooltips and vertical rule on hover

    Parameters:
    df (pd.DataFrame): DataFrame with custom MACD data

    Returns:
    alt.Chart: Altair chart with custom MACD visualization
    """
    # Reset index to make Date a column
    df_reset = df.reset_index()

    # Create selection for hover
    nearest = alt.selection_point(nearest=True, on="mouseover", fields=["Date"], empty=False)

    # Create base chart for price and MAs
    base = alt.Chart(df_reset).encode(x=alt.X("Date:T", title="Date"))

    # Price chart lines
    price_line = base.mark_line().encode(
        y=alt.Y("Close:Q", title="Price", scale=alt.Scale(zero=False)), color=alt.value("black")
    )

    ma10_line = base.mark_line(strokeDash=[1, 0]).encode(y="MA_10:Q", color=alt.value("blue"))

    ma30_line = base.mark_line(strokeDash=[5, 5]).encode(y="MA_30:Q", color=alt.value("green"))

    ma60_line = base.mark_line(strokeDash=[2, 2]).encode(y="MA_60:Q", color=alt.value("red"))

    # Transparent selectors across the chart (for triggering tooltips)
    selectors = (
        alt.Chart(df_reset)
        .mark_point()
        .encode(
            x="Date:T",
            opacity=alt.value(0),
        )
        .add_params(nearest)
    )

    # Vertical rule that follows mouse
    rule = base.mark_rule(color="gray").encode(x="Date:T").transform_filter(nearest)

    # Points on the line that appear on hover
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

    # Create price tooltips
    price_tooltip = (
        alt.Chart(df_reset)
        .mark_text(align="left", dx=5, dy=-5, fontSize=12)
        .encode(x="Date:T", y="Close:Q", text=alt.condition(nearest, alt.Text("Close:Q", format=".2f"), alt.value("")))
        .transform_filter(nearest)
    )

    # Combine price chart layers
    price_chart = (
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
            price_tooltip,
        )
        .properties(title="Stock Price with 10, 30, and 60-day Moving Averages", width=800, height=300)
        .encode(
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Close:Q", title="Price", format=".2f"),
                alt.Tooltip("MA_10:Q", title="10-day MA", format=".2f"),
                alt.Tooltip("MA_30:Q", title="30-day MA", format=".2f"),
                alt.Tooltip("MA_60:Q", title="60-day MA", format=".2f"),
            ]
        )
    )

    # Function to create MACD chart with enhanced tooltips
    # def create_macd_layer(macd_field, signal_field, color, title, height=150):
    #     # Base chart
    #     macd_base = alt.Chart(df_reset).encode(x=alt.X("Date:T", title="Date"))

    #     # MACD line
    #     macd_line = macd_base.mark_line().encode(y=alt.Y(f"{macd_field}:Q", title=title), color=alt.value(color))

    #     # Signal line
    #     signal_line = macd_base.mark_line().encode(y=f"{signal_field}:Q", color=alt.value("red"))

    #     # Add selection
    #     macd_selectors = (
    #         macd_base.mark_point()
    #         .encode(
    #             x="Date:T",
    #             opacity=alt.value(0),
    #         )
    #         .add_params(nearest)
    #     )

    #     # Add vertical rule
    #     macd_rule = macd_base.mark_rule(color="gray").encode(x="Date:T").transform_filter(nearest)

    #     # Points on the MACD line
    #     macd_points = (
    #         macd_line.mark_point(size=50)
    #         .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    #         .transform_filter(nearest)
    #     )

    #     # Points on the signal line
    #     signal_points = (
    #         signal_line.mark_point(size=50)
    #         .encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    #         .transform_filter(nearest)
    #     )

    #     # Tooltips for MACD
    #     macd_tooltip = (
    #         macd_base.mark_text(align="left", dx=5, dy=-5, fontSize=12)
    #         .encode(
    #             x="Date:T",
    #             y=f"{macd_field}:Q",
    #             text=alt.condition(nearest, alt.Text(f"{macd_field}:Q", format=".2f"), alt.value("")),
    #         )
    #         .transform_filter(nearest)
    #     )

    #     # Combine layers
    #     macd_plot = (
    #         alt.layer(macd_line, signal_line, macd_selectors, macd_rule, macd_points, signal_points, macd_tooltip)
    #         .properties(title=title, width=800, height=height)
    #         .encode(
    #             tooltip=[
    #                 alt.Tooltip("Date:T", title="Date"),
    #                 alt.Tooltip(f"{macd_field}:Q", title="MACD", format=".2f"),
    #                 alt.Tooltip(f"{signal_field}:Q", title="Signal", format=".2f"),
    #             ]
    #         )
    #     )

    #     return macd_plot

    # Create all MACD charts with enhanced tooltips
    # macd_10_30_plot = create_macd_layer("macd_10_30", "signal_10_30", "blue", "MACD (10-day MA - 30-day MA)")

    # macd_30_60_plot = create_macd_layer("macd_30_60", "signal_30_60", "green", "MACD (30-day MA - 60-day MA)")

    # macd_10_60_plot = create_macd_layer("macd_10_60", "signal_10_60", "purple", "MACD (10-day MA - 60-day MA)")

    # Combine all charts
    final_chart = price_chart

    return final_chart


def fetch_charts(tickers: list = []) -> list:
    # Get data for a ticker (e.g., Apple)
    charts = []
    for ticker in tickers:
        ticker = "SPY"
        df = get_stock_data(ticker, period="1y")

        # Calculate standard MACD
        df_macd = calculate_macd(df)

        # Calculate custom MACD with 10, 30, 60 day MAs
        df_custom = calculate_custom_macd(df, fast_ma=10, slow_ma=30, longest_ma=60)

        # Create and display charts
        standard_macd_chart = create_macd_chart(df_macd)
        moving_average_chart = create_moving_averages_chart(df_custom)
        charts.append(
            {"ticker": ticker, "standard_macd_chart": standard_macd_chart, "moving_average_chart": moving_average_chart}
        )
        # Save charts to HTML files
        # standard_macd_chart.save(f"{ticker}_standard_macd.html")
        # moving_average_chart.save(f"{ticker}_custom_macd.html")

    return charts


if __name__ == "__main__":
    fetch_charts()
