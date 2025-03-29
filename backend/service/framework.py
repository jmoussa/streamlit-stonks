import pandas as pd
import numpy as np
import altair as alt
import yfinance as yf
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
import io
import requests
import json
import logging
from abc import ABC, abstractmethod
from framework.macd import fetch_charts


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("stock_report")


class StockReportGenerator:
    """
    Generates stock reports with Altair visualizations and buy/sell recommendations
    """

    def __init__(self, stock_df):
        """
        Initialize with a dataframe of stock information

        Parameters:
        stock_df (pd.DataFrame): DataFrame containing stock information with columns:
            - Ticker
            - Index (e.g., "S&P 500", "NASDAQ 100")
            - Current_Price
            - Weekly_Price_Change
            - Weekly_Percentage_Change
            - Monthly_Price_Change
            - Monthly_Percentage_Change
        """
        self.stock_df = stock_df
        self.buy_strategy = "Stocks with negative weekly change (< -$10) but positive monthly change"
        self.sell_strategy = "Stocks with positive weekly change (> $10) but negative monthly change"
        self.report_data = {
            "buy_strategy": self.buy_strategy,
            "sell_strategy": self.sell_strategy,
        }

    def generate_report(self, report_title="Stock Market Report", n_recommendations=15):
        """
        Generate a comprehensive stock report

        Parameters:
        report_title (str): Title of the report
        n_recommendations (int): Number of buy/sell recommendations to include

        Returns:
        dict: Report data including charts and recommendations
        """
        # Create report timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate charts
        top_weekly_gainers_chart = self._create_top_movers_chart("Weekly_Percentage_Change", True, 10)
        top_weekly_losers_chart = self._create_top_movers_chart("Weekly_Percentage_Change", False, 10)
        top_monthly_gainers_chart = self._create_top_movers_chart("Monthly_Percentage_Change", True, 10)
        top_monthly_losers_chart = self._create_top_movers_chart("Monthly_Percentage_Change", False, 10)

        # Create index comparison chart
        index_comparison_chart = self._create_index_comparison_chart()

        # Generate recommendations
        buy_recommendations = self._generate_buy_recommendations(n_recommendations)
        sell_recommendations = self._generate_sell_recommendations(n_recommendations)
        my_stocks = self.stock_df[self.stock_df["Index"] == "My Stocks"]
        my_stock_tickers = my_stocks["Ticker"].tolist()
        my_stock_stat_charts = fetch_charts(my_stock_tickers)

        # Compile report data
        self.report_data = {
            "title": report_title,
            "timestamp": timestamp,
            "charts": {
                "top_weekly_gainers": top_weekly_gainers_chart,
                "top_weekly_losers": top_weekly_losers_chart,
                "top_monthly_gainers": top_monthly_gainers_chart,
                "top_monthly_losers": top_monthly_losers_chart,
                "index_comparison": index_comparison_chart,
                "statistics": my_stock_stat_charts,
            },
            "recommendations": {"buy": buy_recommendations, "sell": sell_recommendations, "my_stocks": my_stocks},
            "summary_stats": self._generate_summary_stats(),
        }

        return self.report_data

    def _create_top_movers_chart(self, metric, is_gain=True, n=10):
        """
        Create a chart of top movers (gainers or losers)

        Parameters:
        metric (str): The column to use for ranking ('Weekly_Percentage_Change' or 'Monthly_Percentage_Change')
        is_gain (bool): If True, show top gainers; if False, show top losers
        n (int): Number of stocks to include

        Returns:
        alt.Chart: Altair chart object
        """
        # Filter and sort data
        direction = -1 if is_gain else 1  # Descending for gainers, ascending for losers
        filtered_df = self.stock_df.dropna(subset=[metric])
        sorted_df = filtered_df.sort_values(by=metric, ascending=(not is_gain)).head(n)

        title = f"Top {n} {'Gainers' if is_gain else 'Losers'} by {metric.replace('_', ' ')}"

        # Create Altair chart
        chart = (
            alt.Chart(sorted_df)
            .mark_bar()
            .encode(
                x=alt.X(f"{metric}:Q", title=metric.replace("_", " ")),
                y=alt.Y("Ticker:N", sort="-x", title="Stock Ticker"),
                color=alt.Color(f"{metric}:Q", scale=alt.Scale(scheme="blueorange")),
                tooltip=[
                    alt.Tooltip("Ticker:N", title="Ticker"),
                    alt.Tooltip("Index:N", title="Index"),
                    alt.Tooltip("Current_Price:Q", title="Current Price", format="$.2f", formatType="number"),
                    alt.Tooltip(f"{metric}:Q", title=metric.replace("_", " "), format=".2f", formatType="number"),
                    alt.Tooltip(
                        "Weekly_Price_Change:Q", title="Weekly Price Change", format="$.2f", formatType="number"
                    ),
                ],
            )
            .properties(title=title, width=900, height=300)
        )

        return chart

    def _create_index_comparison_chart(self):
        """
        Create a chart comparing the performance of S&P 500 vs NASDAQ 100

        Returns:
        alt.Chart: Altair chart object
        """
        # Aggregate data by index
        index_df = (
            self.stock_df.groupby("Index")
            .agg({"Weekly_Percentage_Change": "mean", "Monthly_Percentage_Change": "mean"})
            .reset_index()
        )

        # Reshape data for Altair
        index_df_long = pd.melt(
            index_df,
            id_vars=["Index"],
            value_vars=["Weekly_Percentage_Change", "Monthly_Percentage_Change"],
            var_name="Time Period",
            value_name="Average Percentage Change",
        )

        # Create Altair chart
        chart = (
            alt.Chart(index_df_long)
            .mark_bar()
            .encode(
                x=alt.X("Index:N", title="Market Index"),
                y=alt.Y("Average Percentage Change:Q", title="Avg. Percentage Change"),
                color="Index:N",
                column="Time Period:N",
                tooltip=[
                    alt.Tooltip("Index:N", title="Index"),
                    alt.Tooltip("Average Percentage Change:Q", title="Avg. % Change", format=".2f"),
                ],
            )
            .properties(title="Index Performance Comparison", width=500, height=300)
        )

        return chart

    def _generate_buy_recommendations(self, n=5):
        """
        Generate buy recommendations based on a simple strategy

        Strategy: Stocks with negative weekly change but positive monthly change
        (potential short-term dip in an otherwise upward trend)

        Parameters:
        n (int): Number of recommendations to generate

        Returns:
        list: List of dictionaries with buy recommendations
        """
        # Filter stocks with negative weekly change but positive monthly change
        potential_buys = self.stock_df[
            (self.stock_df["Weekly_Price_Change"] < -10) & (self.stock_df["Monthly_Percentage_Change"] > 0)
        ]

        # Sort by most negative weekly change (best discount)
        potential_buys = potential_buys.sort_values(by="Weekly_Price_Change", ascending=True)

        # Get top n recommendations
        recommendations = []
        for _, row in potential_buys.head(n).iterrows():
            recommendations.append(
                {
                    "ticker": row["Ticker"],
                    "index": row["Index"],
                    "current_price": row["Current_Price"],
                    "weekly_change": row["Weekly_Percentage_Change"],
                    "weekly_price_change": row["Weekly_Price_Change"],
                    "monthly_change": row["Monthly_Percentage_Change"],
                    "monthly_price_change": row["Monthly_Price_Change"],
                    "reason": f"Short-term dip (-{abs(row['Weekly_Percentage_Change'])}%) in longer-term uptrend (+{row['Monthly_Percentage_Change']}%)",
                }
            )

        return recommendations

    def _generate_sell_recommendations(self, n=5):
        """
        Generate sell recommendations based on a simple strategy

        Strategy: Stocks with positive weekly change but negative monthly change
        (potential short-term spike in an otherwise downward trend)

        Parameters:
        n (int): Number of recommendations to generate

        Returns:
        list: List of dictionaries with sell recommendations
        """
        # Filter stocks with positive weekly change but negative monthly change
        potential_sells = self.stock_df[
            (self.stock_df["Weekly_Price_Change"] > 10) & (self.stock_df["Monthly_Percentage_Change"] < 0)
        ]

        # Sort by most positive weekly change (best selling opportunity)
        potential_sells = potential_sells.sort_values(by="Weekly_Percentage_Change", ascending=False)

        # Get top n recommendations
        recommendations = []
        for _, row in potential_sells.head(n).iterrows():
            recommendations.append(
                {
                    "ticker": row["Ticker"],
                    "index": row["Index"],
                    "current_price": row["Current_Price"],
                    "weekly_change": row["Weekly_Percentage_Change"],
                    "weekly_price_change": row["Weekly_Price_Change"],
                    "monthly_change": row["Monthly_Percentage_Change"],
                    "monthly_price_change": row["Monthly_Price_Change"],
                    "reason": f"Short-term spike (+{row['Weekly_Percentage_Change']}%) in longer-term downtrend (-{abs(row['Monthly_Percentage_Change'])}%)",
                }
            )

        return recommendations

    def _generate_summary_stats(self):
        """
        Generate summary statistics for the report

        Returns:
        dict: Dictionary containing summary statistics
        """
        summary = {
            "total_stocks": len(self.stock_df),
            "sp500_count": len(self.stock_df[self.stock_df["Index"] == "S&P 500"]),
            "nasdaq_count": len(self.stock_df[self.stock_df["Index"] == "NASDAQ 100"]),
            "weekly_gainers": len(self.stock_df[self.stock_df["Weekly_Percentage_Change"] > 0]),
            "weekly_losers": len(self.stock_df[self.stock_df["Weekly_Percentage_Change"] < 0]),
            "monthly_gainers": len(self.stock_df[self.stock_df["Monthly_Percentage_Change"] > 0]),
            "monthly_losers": len(self.stock_df[self.stock_df["Monthly_Percentage_Change"] < 0]),
            "avg_weekly_change": self.stock_df["Weekly_Percentage_Change"].mean(),
            "avg_monthly_change": self.stock_df["Monthly_Percentage_Change"].mean(),
            "top_weekly_gainer": self.stock_df.loc[self.stock_df["Weekly_Percentage_Change"].idxmax()]["Ticker"],
            "top_weekly_loser": self.stock_df.loc[self.stock_df["Weekly_Percentage_Change"].idxmin()]["Ticker"],
        }

        return summary

    def save_report_to_html(self, filename="stock_report.html"):
        """
        Save the report to an HTML file

        Parameters:
        filename (str): Name of the HTML file to save
        """
        if not self.report_data:
            raise ValueError("No report data available. Generate a report first.")

        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.report_data['title']}</title>
            <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
            <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
            <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .section {{ margin-bottom: 30px; }}
                .chart {{ height: 400px; width: 100%; padding: 25px; }}
                .recommendations {{ display: flex; }}
                .recommendation-column {{ flex: 1; margin-right: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>{self.report_data['title']}</h1>
            <p>Generated on {self.report_data['timestamp']}</p>
            <!--- make market summary a table
            <div class="section">
                <h2>Market Summary</h2>
                <p>Total stocks: {self.report_data['summary_stats']['total_stocks']}</p>
                <p>S&P 500: {self.report_data['summary_stats']['sp500_count']} stocks</p>
                <p>NASDAQ 100: {self.report_data['summary_stats']['nasdaq_count']} stocks</p>
                <p>Weekly Gainers: {self.report_data['summary_stats']['weekly_gainers']} stocks</p>
                <p>Weekly Losers: {self.report_data['summary_stats']['weekly_losers']} stocks</p>
                <p class='{'positive' if self.report_data['summary_stats']['avg_weekly_change'] > 0 else 'negative'}'>Average Weekly Change: {self.report_data['summary_stats']['avg_weekly_change']}%</p>
                <p class='{'positive' if self.report_data['summary_stats']['avg_monthly_change'] > 0 else 'negative'}'>Average Monthly Change: {self.report_data['summary_stats']['avg_monthly_change']}%</p>
            </div>
            -->
            <div class="section">
                <h2>Market Summary</h2>
                <table>
                    <tr>
                        <th>Category</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Total Stocks</td>
                        <td>{self.report_data['summary_stats']['total_stocks']}</td>
                    </tr>
                    <tr>
                        <td>S&P 500</td>
                        <td>{self.report_data['summary_stats']['sp500_count']}</td>  
                    </tr>
                    <tr>
                        <td>NASDAQ 100</td>
                        <td>{self.report_data['summary_stats']['nasdaq_count']}</td>
                    </tr>
                    <tr>
                        <td>Weekly Gainers</td>
                        <td class="positive">{self.report_data['summary_stats']['weekly_gainers']}</td>
                    </tr>
                    <tr>
                        <td>Weekly Losers</td>
                        <td class="negative">{self.report_data['summary_stats']['weekly_losers']}</td>
                    </tr>
                    <tr>
                        <td>Average Weekly Change</td>
                        <td class='{'positive' if self.report_data['summary_stats']['avg_weekly_change'] > 0 else 'negative'}'>{round(self.report_data['summary_stats']['avg_weekly_change'], 2)}%</td>
                    </tr>
                    <tr>
                        <td>Average Monthly Change</td>
                        <td class='{'positive' if self.report_data['summary_stats']['avg_monthly_change'] > 0 else 'negative'}'>{round(self.report_data['summary_stats']['avg_monthly_change'], 2)}%</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>My Stocks</h2> 
                <ul>
                    {"".join([f"<li><strong>{row['Ticker']}</strong> : ${row['Current_Price']}  |  Weekly Change: <span class='{'positive' if row['Weekly_Percentage_Change'] > 0 else 'negative'}'>{row['Weekly_Percentage_Change']}%</span> | Monthly Change: <span class='{'positive' if row['Monthly_Percentage_Change'] > 0 else 'negative'}'> {row['Monthly_Percentage_Change']}%</span></li>" for _, row in self.stock_df.iterrows() if row['Index'] == "My Stocks"])}
                </ul> 
            <div>
            <div class="section">
                <h2>Index Comparison</h2>
                <div id="index-comparison" class="chart"></div>
            </div>
            
            <div class="section">
                <h2>Top Weekly Gainers</h2>
                <div id="weekly-gainers" class="chart"></div>
            </div>
            
            <div class="section">
                <h2>Top Weekly Losers</h2>
                <div id="weekly-losers" class="chart"></div>
            </div>
            
            <div class="section">
                <h2>Top Monthly Gainers</h2>
                <div id="monthly-gainers" class="chart"></div>
            </div>
            
            <div class="section">
                <h2>Top Monthly Losers</h2>
                <div id="monthly-losers" class="chart"></div>
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                <div class="recommendations">
                    <div class="recommendation-column">
                        <h3>Buy Recommendations</h3>
                        <p>{self.buy_strategy}</p>
                        <table>
                            <tr>
                                <th>Ticker</th>
                                <th>Price</th>
                                <th>Weekly Change</th>
                                <th>Weekly Price Change</th>
                                <th>Monthly Change</th>
                                <th>Monthly Price Change</th>
                                <th>Reason</th>
                            </tr>
                            {"".join([f"<tr><td>{rec['ticker']}</td><td>$ {rec['current_price']}</td><td class='negative'>{rec['weekly_change']}%</td><td class='negative'>$ {rec['weekly_price_change']}</td><td class='positive'>{rec['monthly_change']}%</td><td class='positive'>$ {rec['monthly_price_change']}</td><td>{rec['reason']}</td></tr>" for rec in self.report_data['recommendations']['buy']])}
                        </table>
                    </div>
                    <div class="recommendation-column">
                        <h3>Sell Recommendations</h3>
                        <p>{self.sell_strategy}</p>
                        <table>
                            <tr>
                                <th>Ticker</th>
                                <th>Price</th>
                                <th>Weekly Change</th>
                                <th>Weekly Price Change</th>
                                <th>Monthly Change</th>
                                <th>Monthly Price Change</th>
                                <th>Reason</th>
                            </tr>
                            {"".join([f"<tr><td>{rec['ticker']}</td><td>$ {rec['current_price']}</td><td class='positive'>{rec['weekly_change']}%</td><td class='positive'>$ {rec['weekly_price_change']}</td><td class='negative'>{rec['monthly_change']}%</td><td class='negative'>$ {rec['monthly_price_change']}</td><td>{rec['reason']}</td></tr>" for rec in self.report_data['recommendations']['sell']])}
                        </table>
                    </div>
                </div>
            </div>
        </body>
        <script>
                // Embed Altair charts
                vegaEmbed('#index-comparison', {self.report_data['charts']['index_comparison'].to_json()});
                vegaEmbed('#weekly-gainers', {self.report_data['charts']['top_weekly_gainers'].to_json()});
                vegaEmbed('#weekly-losers', {self.report_data['charts']['top_weekly_losers'].to_json()});
                vegaEmbed('#monthly-gainers', {self.report_data['charts']['top_monthly_gainers'].to_json()});
                vegaEmbed('#monthly-losers', {self.report_data['charts']['top_monthly_losers'].to_json()});
                
        </script>
        </html>
        """

        # Save to HTML file
        with open(filename, "w") as file:
            file.write(html_content)

        return html_content


# Distribution Framework


class ReportDistributor(ABC):
    """
    Abstract base class for report distribution channels
    """

    def __init__(self, config=None):
        self.config = config or {}

    @abstractmethod
    def send_report(self, report_data, report_file=None):
        """
        Send the report through the specific channel

        Parameters:
        report_data (dict): The report data dictionary
        report_file (str): Path to the report HTML file

        Returns:
        bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def format_report(self, report_data):
        """
        Format the report for the specific channel

        Parameters:
        report_data (dict): The report data dictionary

        Returns:
        str: Formatted report content
        """
        pass


class EmailDistributor(ReportDistributor):
    """
    Distributes reports via email
    """

    def __init__(self, config):
        """
        Initialize with email configuration

        Parameters:
        config (dict): Email configuration with keys:
            - smtp_server: SMTP server address
            - smtp_port: SMTP server port
            - smtp_user: SMTP username
            - smtp_password: SMTP password
            - sender_email: Sender email address
            - recipients: List of recipient email addresses
        """
        super().__init__(config)
        required_keys = ["smtp_server", "smtp_port", "smtp_user", "smtp_password", "sender_email", "recipients"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration key: {key}")

    def send_report(self, report_data, report_file=None):
        """
        Send the report via email
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"{report_data['title']} - {report_data['timestamp']}"
            msg["From"] = self.config["sender_email"]
            msg["To"] = ", ".join(self.config["recipients"])

            # Create HTML content
            html_content = self.format_report(report_data)
            msg.attach(MIMEText(html_content, "html"))

            # Attach the full HTML report if available
            if report_file and os.path.exists(report_file):
                with open(report_file, "r") as f:
                    attachment = MIMEText(f.read(), "html")
                    attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(report_file))
                    msg.attach(attachment)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["smtp_user"], self.config["smtp_password"])
                server.send_message(msg)

            logger.info(f"Report sent via email to {len(self.config['recipients'])} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def format_report(self, report_data):
        """
        Format the report for html
        """
        # Create an email-friendly HTML summary
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>{report_data['title']}</h1>
            <p>Generated on {report_data['timestamp']}</p>
            
            <h2>Market Summary</h2>
            <p>Average Weekly Change: <span class="{'positive' if report_data['summary_stats']['avg_weekly_change'] > 0 else 'negative'}">{report_data['summary_stats']['avg_weekly_change']}%</span></p>
            <p>Average Monthly Change: <span class="{'positive' if report_data['summary_stats']['avg_monthly_change'] > 0 else 'negative'}">{report_data['summary_stats']['avg_monthly_change']}%</span></p>
            
            <h2>Top Buy Recommendations</h2>
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Price</th>
                    <th>Weekly Change</th>
                    <th>Monthly Change</th>
                </tr>
                {"".join([f"<tr><td>{rec['ticker']}</td><td>$ {rec['current_price']}</td><td class='negative'>{rec['weekly_change']}%</td><td class='negative'>$ {rec['weekly_price_change']}</td><td class='positive'>{rec['monthly_change']}%</td><td class='positive'>$ {rec['monthly_price_change']}</td></tr>" for rec in report_data['recommendations']['buy'][:3]])}
            </table>
            
            <h2>Top Sell Recommendations</h2>
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Price</th>
                    <th>Weekly Change</th>
                    <th>Monthly Change</th>
                </tr>
                {"".join([f"<tr><td>{rec['ticker']}</td><td>$ {rec['current_price']}</td><td class='positive'>{rec['weekly_change']}%</td><td class='positive'>$ {rec['weekly_price_change']}</td><td class='negative'>{rec['monthly_change']}%</td><td class='negative'>$ {rec['monthly_price_change']}</td></tr>" for rec in report_data['recommendations']['sell'][:3]])}
            </table>
            
            <p>Please see the attached file for the full report with charts.</p>
        </body>
        </html>
        """
        return html


class DiscordDistributor(ReportDistributor):
    """
    Distributes reports via Discord webhooks
    """

    def __init__(self, config):
        """
        Initialize with Discord configuration

        Parameters:
        config (dict): Discord configuration with keys:
            - webhook_url: Discord webhook URL
            - username: Bot username (optional)
            - avatar_url: Bot avatar URL (optional)
        """
        super().__init__(config)
        if "webhook_url" not in self.config:
            raise ValueError("Missing required configuration key: webhook_url")

    def send_report(self, report_data, report_file=None):
        """
        Send the report via Discord webhook
        """
        try:
            # Format message content
            content = self.format_report(report_data)

            # Prepare webhook data
            webhook_data = {
                "content": content,
                "embeds": [
                    {
                        "title": f"{report_data['title']} - {report_data['timestamp']}",
                        "color": 3447003,  # Blue color
                        "fields": [],
                    }
                ],
            }

            # Add username and avatar if provided
            if "username" in self.config:
                webhook_data["username"] = self.config["username"]
            if "avatar_url" in self.config:
                webhook_data["avatar_url"] = self.config["avatar_url"]

            # Add buy recommendations
            buy_recommendations = []
            for i, rec in enumerate(report_data["recommendations"]["buy"][:10]):
                buy_recommendations.append(
                    f"**{rec['ticker']}**: $ {rec['current_price']} | Weekly: {rec['weekly_change']}% | Monthly: {rec['monthly_change']}%"
                )

            # webhook_data["embeds"][0]["fields"].append(
            #     {
            #         "name": "Top Buy Recommendations",
            #         # "value": "\n".join(buy_recommendations) if buy_recommendations else "None available",
            #         "inline": False,
            #     }
            # )

            # Add sell recommendations
            sell_recommendations = []
            for i, rec in enumerate(report_data["recommendations"]["sell"][:10]):
                sell_recommendations.append(
                    f"**{rec['ticker']}**: $ {rec['current_price']} | Weekly: {rec['weekly_change']}% | Monthly: {rec['monthly_change']}%"
                )

            # webhook_data["embeds"][0]["fields"].append(
            #     {
            #         "name": "Top Sell Recommendations",
            #         "value": "\n".join(sell_recommendations) if sell_recommendations else "None available",
            #         "inline": False,
            #     }
            # )

            # Attach HTML file if available
            if report_file and os.path.exists(report_file):
                files = {"file": (os.path.basename(report_file), open(report_file, "rb"))}
                response = requests.post(
                    self.config["webhook_url"], data={"payload_json": json.dumps(webhook_data)}, files=files
                )
            else:
                response = requests.post(self.config["webhook_url"], json=webhook_data)

            if response.status_code in (200, 204):
                logger.info("Report sent via Discord webhook")
                return True
            else:
                logger.error(f"Failed to send to Discord: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send to Discord: {str(e)}")
            return False

    def format_report(self, report_data):
        """
        Format the report for Discord
        """
        content = f"# {report_data['title']}\n"
        # Discord uses Markdown formatting
        content += f"Generated on {report_data['timestamp']}\n\n"
        content += "## Market Summary\n"
        content += "This just in, we're cookin' with gas! 🚀\n"

        weekly_emoji = "📈" if report_data["summary_stats"]["avg_weekly_change"] > 0 else "📉"
        monthly_emoji = "📈" if report_data["summary_stats"]["avg_monthly_change"] > 0 else "📉"
        content += f"{weekly_emoji} Average Weekly Change: {report_data['summary_stats']['avg_weekly_change']:.2f}%\n"
        content += (
            f"{monthly_emoji} Average Monthly Change: {report_data['summary_stats']['avg_monthly_change']:.2f}%\n"
        )

        # My Stocks
        content += "\n"
        content += "## My Stocks\n"
        my_stocks = report_data["recommendations"]["my_stocks"].sort_values(by="Ticker", ascending=False)

        for _, row in my_stocks.iterrows():
            if row["Index"] == "My Stocks":
                emoji = "📈" if row["Weekly_Percentage_Change"] > 0 else "📉"
                content += f"{emoji} - **{row['Ticker']}**: $ {row['Current_Price']}  |  Weekly: {row['Weekly_Percentage_Change']}%  |  Monthly: {row['Monthly_Percentage_Change']}%\n"

        content += "\n"
        # Add buy recommendations
        content += "## Top Buy Recommendations\n"
        for rec in report_data["recommendations"]["buy"][:5]:
            content += f"- **{rec['ticker']}**: $ {rec['current_price']}  |  Weekly: {rec['weekly_change']}%  |  Monthly: {rec['monthly_change']}% |  Reason: {rec['reason']}\n"

        content += "\n"
        # Add sell recommendations
        content += "## Top Sell Recommendations\n"
        for rec in report_data["recommendations"]["sell"][:5]:
            content += f"- **{rec['ticker']}**: $ {rec['current_price']} |  Weekly: {rec['weekly_change']}%  |  Monthly: {rec['monthly_change']}% |  Reason: {rec['reason']}\n"
        content += "\n"

        return content


if __name__ == "__main__":
    # Generate Report from latest stock parquet
    latest_parquet = max(
        [f for f in os.listdir() if f.endswith(".parquet") and ("stocks" in f)],
        key=os.path.getctime,
    )
    print(f"Loading data from {latest_parquet}")
    df = pd.read_parquet(latest_parquet)

    # De-dupe based on Ticker column
    df = df.drop_duplicates(subset=["Ticker"], keep="first")

    # Generate stock report
    report_generator = StockReportGenerator(df)
    report_data_dict = report_generator.generate_report()
    filename = "full_stock_report.html"
    report_html = report_generator.save_report_to_html(filename)

    money_moves = "https://discord.com/api/webhooks/1354536674096320653/wxIbvAbYB6DSDemrR8LjXBFxLDGuX7q7QGGH0fZ7yq4HB5uTg3lUe0TfTbdY6Xb-D3Tr"
    test_channel = "https://discord.com/api/webhooks/1354544888590630952/PwJar1bIfYS6rRcYmQlWeMu2YBFY-Z4xszFqiDFLFrNc_qOdNwgt0E2UpQlon0NJFqSD"
    discord_distributor = DiscordDistributor(
        {
            "webhook_url": test_channel,
            "username": "StonkBot",
            "avatar_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQOoSZbnUKiiXkx-C6kHAAZ-aSbYeu-5dnd4g&s",
        }
    )
    # Send report to Discord with file
    discord_distributor.send_report(report_data_dict, report_file=filename)
