#!/bin/bash

# Create the project directory structure
mkdir -p financial_analysis/data financial_analysis/src

# Create empty __init__.py to make src a Python package
touch financial_analysis/src/__init__.py

# Create the Python module files with basic content
cat > financial_analysis/src/database.py << 'EOL'
import os
import pandas as pd
from sqlalchemy import create_engine, inspect
from sqlalchemy.types import DateTime, Float

class FinancialDatabase:
    def __init__(self, db_path='sqlite:///data/financial_data.db'):
        """Initialize database connection."""
        os.makedirs('data', exist_ok=True)
        self.engine = create_engine(db_path)
        
    def save_data(self, df, table_name, if_exists='append'):
        """
        Save DataFrame to database.
        
        Args:
            df: DataFrame to save
            table_name: Name of the table
            if_exists: What to do if table exists ('fail', 'replace', 'append')
        """
        # Convert index to column if it's a DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            time_column = 'index'
        else:
            time_column = None
        
        # Infer SQL types
        dtype = {}
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                dtype[col] = DateTime
            elif pd.api.types.is_float_dtype(df[col]):
                dtype[col] = Float
        
        df.to_sql(
            table_name,
            self.engine,
            if_exists=if_exists,
            index=False,
            dtype=dtype
        )
        
    def load_data(self, table_name, start_date=None, end_date=None):
        """
        Load data from database with optional date filtering.
        
        Args:
            table_name: Name of the table to load
            start_date: Optional start date filter
            end_date: Optional end date filter
        Returns:
            DataFrame with the data
        """
        query = f"SELECT * FROM {table_name}"
        conditions = []
        
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        df = pd.read_sql(query, self.engine, parse_dates=['date'])
        if 'date' in df.columns:
            df = df.set_index('date')
        return df
    
    def table_exists(self, table_name):
        """Check if a table exists in the database."""
        return inspect(self.engine).has_table(table_name)
EOL

cat > financial_analysis/src/datafetch.py << 'EOL'
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
                df = df.set_index('date')
                df = df.sort_index()
            return df
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return pd.DataFrame()
EOL

cat > financial_analysis/src/analysis.py << 'EOL'
import pandas as pd
import matplotlib.pyplot as plt

class FinancialAnalyzer:
    def __init__(self, data):
        """Initialize with financial data."""
        self.data = data
        
    def calculate_returns(self):
        """Calculate daily and cumulative returns."""
        if 'adjClose' not in self.data.columns:
            raise ValueError("Data must contain 'adjClose' column")
            
        returns = pd.DataFrame(index=self.data.index)
        returns['daily'] = self.data['adjClose'].pct_change()
        returns['cumulative'] = (1 + returns['daily']).cumprod()
        return returns
        
    def moving_averages(self, windows=[20, 50, 200]):
        """Calculate moving averages for given windows."""
        ma = pd.DataFrame(index=self.data.index)
        for window in windows:
            ma[f'ma_{window}'] = self.data['adjClose'].rolling(window=window).mean()
        return ma
        
    def plot_prices(self, title='Stock Prices'):
        """Plot adjusted closing prices."""
        if 'adjClose' not in self.data.columns:
            raise ValueError("Data must contain 'adjClose' column")
            
        plt.figure(figsize=(12, 6))
        plt.plot(self.data.index, self.data['adjClose'], label='Adjusted Close')
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        plt.show()
        
    def plot_returns(self):
        """Plot daily and cumulative returns."""
        returns = self.calculate_returns()
        
        plt.figure(figsize=(12, 6))
        plt.subplot(2, 1, 1)
        plt.plot(returns.index, returns['daily'], label='Daily Returns')
        plt.title('Daily Returns')
        plt.grid(True)
        
        plt.subplot(2, 1, 2)
        plt.plot(returns.index, returns['cumulative'], label='Cumulative Returns')
        plt.title('Cumulative Returns')
        plt.grid(True)
        
        plt.tight_layout()
        plt.show()
EOL

cat > financial_analysis/src/main.py << 'EOL'
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from datafetch import TiingoDataFetcher
from database import FinancialDatabase
from analysis import FinancialAnalyzer
import argparse

load_dotenv()

class FinancialAnalysisTool:
    def __init__(self):
        self.db = FinancialDatabase()
        self.fetcher = TiingoDataFetcher()
        
    def get_user_input(self):
        """Get user input for tickers and date range."""
        parser = argparse.ArgumentParser(description='Financial Market Analysis Tool')
        parser.add_argument('--tickers', nargs='+', required=True, help='List of tickers to analyze')
        parser.add_argument('--start_date', required=True, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end_date', help='End date (YYYY-MM-DD)')
        parser.add_argument('--freq', default='daily', help='Frequency (daily, weekly, monthly)')
        
        args = parser.parse_args()
        
        # Validate dates
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else datetime.now()
            
            if start_date > end_date:
                raise ValueError("Start date cannot be after end date")
                
            if start_date < datetime.now() - timedelta(days=365*20):  # Roughly 20 years
                print("Warning: You're requesting a very large date range which may take time to download.")
                
        except ValueError as e:
            print(f"Invalid date format: {str(e)}")
            exit(1)
            
        return {
            'tickers': [t.upper() for t in args.tickers],
            'start_date': args.start_date,
            'end_date': args.end_date,
            'freq': args.freq
        }
        
    def run(self):
        """Main execution flow."""
        params = self.get_user_input()
        
        for ticker in params['tickers']:
            print(f"\nProcessing {ticker}...")
            
            # Check if data exists in database
            if self.db.table_exists(ticker):
                print(f"Loading existing data for {ticker} from database...")
                df = self.db.load_data(
                    ticker,
                    start_date=params['start_date'],
                    end_date=params['end_date']
                )
                
                # Check if we have all requested data
                if not df.empty:
                    data_start = df.index.min().strftime('%Y-%m-%d')
                    data_end = df.index.max().strftime('%Y-%m-%d')
                    
                    # If database has less data than requested, fetch the missing parts
                    if data_start > params['start_date']:
                        print(f"Fetching additional historical data from {params['start_date']} to {data_start}")
                        new_data = self.fetcher.fetch_data(
                            ticker,
                            start_date=params['start_date'],
                            end_date=data_start,
                            freq=params['freq']
                        )
                        if not new_data.empty:
                            df = pd.concat([new_data, df])
                            self.db.save_data(new_data, ticker)
                            
                    if params['end_date'] and data_end < params['end_date']:
                        print(f"Fetching additional recent data from {data_end} to {params['end_date']}")
                        new_data = self.fetcher.fetch_data(
                            ticker,
                            start_date=data_end,
                            end_date=params['end_date'],
                            freq=params['freq']
                        )
                        if not new_data.empty:
                            df = pd.concat([df, new_data])
                            self.db.save_data(new_data, ticker)
            else:
                print(f"No existing data found for {ticker}. Fetching from Tiingo...")
                df = self.fetcher.fetch_data(
                    ticker,
                    start_date=params['start_date'],
                    end_date=params['end_date'],
                    freq=params['freq']
                )
                if not df.empty:
                    self.db.save_data(df, ticker)
                    
            if df.empty:
                print(f"No data available for {ticker}")
                continue
                
            # Perform analysis
            analyzer = FinancialAnalyzer(df)
            analyzer.plot_prices(title=f"{ticker} Prices")
            
            returns = analyzer.calculate_returns()
            print(f"\nReturn statistics for {ticker}:")
            print(returns['daily'].describe())
            
            analyzer.plot_returns()
            
            # Calculate and display moving averages
            ma = analyzer.moving_averages()
            print(f"\nMoving Averages for {ticker}:")
            print(ma.tail())

if __name__ == "__main__":
    tool = FinancialAnalysisTool()
    tool.run()
EOL

# Create requirements.txt
cat > financial_analysis/requirements.txt << 'EOL'
pandas
numpy
python-dotenv
tiingo
sqlalchemy
matplotlib
EOL

# Create .env file (empty, user should add their API key)
touch financial_analysis/.env

echo "Project structure created successfully!"
echo "Don't forget to:"
echo "1. Add your TIINGO_API_KEY to the .env file"
echo "2. Activate your virtual environment"
echo "3. Run 'pip install -r requirements.txt'"
