import pandas as pd

# import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import warnings
from loguru import logger

# Suppress warnings
warnings.filterwarnings("ignore")


def get_sp500_tickers():
    """
    Scrape S&P 500 tickers from Wikipedia
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": "constituents"})

    tickers = []
    for row in table.findAll("tr"):
        if len(row.findAll("td")) == 0:
            continue
        ticker = row.findAll("td")[0].text.strip()
        tickers.append(ticker)

    return tickers


def get_nasdaq100_tickers():
    """
    Scrape NASDAQ 100 tickers from Wikipedia
    """
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "wikitable sortable"})

    tickers = []
    for row in table.findAll("tr")[1:]:
        ticker = row.findAll("td")[1].text.strip()
        tickers.append(ticker)

    return tickers


def get_stock_data(tickers, index_name):
    """
    Get stock data for the given tickers using yfinance
    """
    # Set up dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Get 90 days of data to calculate monthly movements

    # Empty lists to store results
    results = []

    # Counter for rate limiting
    count = 0

    for ticker in tickers:
        try:
            # Add delay every 50 requests to avoid hitting rate limits
            if count % 50 == 0 and count > 0:
                print(f"Processed {count} stocks. Pausing for 3 seconds...")
                time.sleep(3)

            # Get stock data
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if not hist.empty:
                # Calculate current price
                current_price = hist["Close"].iloc[-1]

                # Calculate weekly price and percentage change
                week_ago_price = hist["Close"].iloc[-6] if len(hist) >= 6 else hist["Close"].iloc[0]
                weekly_price_change = current_price - week_ago_price
                weekly_percentage_change = (weekly_price_change / week_ago_price) * 100

                # Calculate monthly price and percentage change
                month_ago_index = -22 if len(hist) >= 22 else 0
                month_ago_price = hist["Close"].iloc[month_ago_index]
                monthly_price_change = current_price - month_ago_price
                monthly_percentage_change = (monthly_price_change / month_ago_price) * 100

                # Append results
                results.append(
                    {
                        "Ticker": ticker,
                        "Index": index_name,
                        "Current_Price": round(current_price, 2),
                        "Weekly_Price_Change": round(weekly_price_change, 2),
                        "Weekly_Percentage_Change": round(weekly_percentage_change, 2),
                        "Monthly_Price_Change": round(monthly_price_change, 2),
                        "Monthly_Percentage_Change": round(monthly_percentage_change, 2),
                    }
                )

                count += 1

            else:
                print(f"No data available for {ticker}")

        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    return pd.DataFrame(results)


def main(my_stocks=["GOOG", "ABBV", "LMT", "EUAD", "PLTR"]):
    """
    Main function to scrape stock data and create dataframe
    """
    # check for parquets published within the last 24 hours
    # if found, load the parquets and return the dataframes
    # if not found, scrape the data and save the parquets
    # return the dataframes
    import os

    files = [f for f in os.listdir() if f.endswith(".parquet") and ("stocks" in f or "actionables" in f)]
    files_present = False if len(files) == 0 else True
    if files_present:
        year = files[0].split("_")[-2]
        time = files[0].split("_")[-1].split(".")[0]
        ts = year + "_" + time
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    combined_data = pd.DataFrame()
    actionable_file = pd.DataFrame()
    # check for files within the last hour
    if files_present and (datetime.now() - datetime.strptime(ts, "%Y%m%d_%H%M")).seconds < 3600:
        logger.info(f"Found parquet file created within the last hour: {files[0]}")
        timestamp = ts
        try:
            combined_data = pd.read_parquet(files[0])
        except:
            combined_data = pd.DataFrame()
            logger.info("No stock file found, fetching")
        try:
            filename = files[0].replace("stocks", "actionables")
            actionable_file = pd.read_parquet(filename)
        except:
            actionable_file = pd.DataFrame()
            logger.info("No actionable file found, fetching")
    elif combined_data.empty:
        print("Scraping S&P 500 tickers...")
        sp500_tickers = get_sp500_tickers()
        print(f"Found {len(sp500_tickers)} S&P 500 tickers")

        print("Scraping NASDAQ 100 tickers...")
        nasdaq100_tickers = get_nasdaq100_tickers()
        print(f"Found {len(nasdaq100_tickers)} NASDAQ 100 tickers")

        # Remove duplicates (stocks that are in both indices)
        nasdaq100_unique = [ticker for ticker in nasdaq100_tickers if ticker not in sp500_tickers]

        print("Getting S&P 500 stock data...")
        sp500_data = get_stock_data(sp500_tickers, "S&P 500")

        print("Getting NASDAQ 100 stock data...")
        nasdaq100_data = get_stock_data(nasdaq100_unique, "NASDAQ 100")

        print("Getting stock data for my stocks...")
        my_stock_data = get_stock_data(my_stocks, "My Stocks")

        # Combine data
        combined_data = pd.concat([sp500_data, nasdaq100_data], ignore_index=True)
        # dedupe
        combined_data = combined_data.drop_duplicates(subset=["Ticker"], keep="first")
        combined_data = combined_data[combined_data["Ticker"].isin(my_stocks) == False]
        combined_data = pd.concat([combined_data, my_stock_data], ignore_index=True)

        # Sort by ticker
        combined_data = combined_data.sort_values("Ticker")

        print(f"Total stocks processed: {len(combined_data)}")

        combined_data.to_parquet(f"stocks_{timestamp}.parquet", index=False)
        print(f"Data saved to stocks_{timestamp}.paruet")

    if actionable_file.empty:
        # Filter actionable data (stocks that have moved (up or down) more than $10 or 5% in the last week)
        actionable_file = combined_data[
            (
                ((combined_data["Weekly_Price_Change"] > 10) | (combined_data["Weekly_Price_Change"]) < -10)
                | ((combined_data["Weekly_Percentage_Change"] > 5) | (combined_data["Weekly_Percentage_Change"] < -5))
            )  # monthly changes are still positive
            & (combined_data["Monthly_Price_Change"] > 1)
        ]
        if not actionable_file.empty:
            actionable_file.to_parquet(f"actionables_{timestamp}.parquet", index=False)
            print(f"Data saved to actionables_{timestamp}.parquet")

    return combined_data, actionable_file


if __name__ == "__main__":
    docstr = """
--------------------------------------------------------------------------------------------------
    Tool to scrape stock data and identify actionable stocks 
--------------------------------------------------------------------------------------------------
Buy/Sell Strategy:
    - Buy: Stocks that have moved down more than $10 in the last week
        & are still positive in the last month
    - Sell: Stocks that have moved up more than $10 in the last week
        & are still positive in the last month
        
--------------------------------------------------------------------------------------------------
    """
    print(docstr)
    my_stocks = ["SPX", "SPY", "VIX", "ABBV", "LMT", "EUAD", "PLTR", "CVNA", "KMX"]
    print(f"Fetching data for your stocks: {my_stocks}")
    print("---------------------------------------------------------------------------------------------------")
    df, actionable_df = main(my_stocks)
    actionable_df = actionable_df.sort_values(by=["Weekly_Price_Change"], ascending=False)
    sell_list = actionable_df[actionable_df["Weekly_Price_Change"] > 10]
    buy_list = actionable_df[actionable_df["Weekly_Price_Change"] < -10]
    # Write to parquets
    # logger.info("----------------- BUY LIST -----------------------")
    # print(buy_list.head(20))
    # logger.info("----------------- SELL LIST -----------------------")
    # print(sell_list.head(20))
    # buy_list.to_parquet("buy_list.parquet", index=False)
    # sell_list.to_parquet("sell_list.parquet", index=False)

    # Get stock data for my stocks
    # my_buy_list = buy_list[buy_list["Ticker"].isin(my_stocks)]
    # my_sell_list = sell_list[sell_list["Ticker"].isin(my_stocks)]
    # logger.info("----------------- MY BUY LIST -----------------------")
    # print(my_buy_list.head(20))
    # logger.info("----------------- MY SELL LIST -----------------------")
    # print(my_sell_list.head(20))
