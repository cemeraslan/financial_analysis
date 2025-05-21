from tiingo import TiingoClient
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class TiingoDataFetcher:
    def __init__(self):
        """Initialize Tiingo client with API key from .env."""
        api_key = os.getenv('TIINGO_API_KEY')
        if not api_key:
            raise ValueError("TIINGO_API_KEY not found in .env file")
            
        self.config = {
            'api_key': api_key,
            'session': True
        }
        self.client = TiingoClient(self.config)
        
    def fetch_data(self, ticker, start_date, end_date=None, freq='daily'):
        """
        Fetch historical data from Tiingo.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date as string (YYYY-MM-DD) or datetime
            end_date: End date as string (YYYY-MM-DD) or datetime (default: today)
            freq: Frequency of data ('daily', 'weekly', 'monthly')
        Returns:
            DataFrame with historical data
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        try:
            historical_prices = self.client.get_ticker_price(
                ticker,
                fmt='json',
                startDate=start_date,
                endDate=end_date,
                frequency=freq
            )
            df = pd.DataFrame(historical_prices)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                # Remove timezone information and ensure consistency
                df['date'] = df['date'].dt.tz_localize(None)
                df = df.set_index('date')
                df = df.sort_index()
            return df
        except Exception as e:
            if "API limit reached" in str(e):
                print("Tiingo API limit reached - try again later or upgrade your plan")
            elif "Invalid token" in str(e):
                print("Invalid API token - check your .env file")
            else:
                print(f"Error fetching data for {ticker}: {str(e)}")
            return pd.DataFrame()
