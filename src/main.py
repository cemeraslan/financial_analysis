#!/usr/bin/env python3
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
import argparse
import sys
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import seaborn as sns
print(plt.style.available)  # Look for 'seaborn' or 'seaborn-v0_8'

# Local imports
from src.datafetch import TiingoDataFetcher
from src.database import FinancialDatabase
from src.analysis import FinancialAnalyzer

load_dotenv()

class FinancialAnalysisTool:
    def __init__(self):
        self.db = FinancialDatabase()
        self.fetcher = TiingoDataFetcher()
        
    def get_user_input(self) -> Dict:
        """Handle both CLI and interactive input with improved validation."""
        parser = argparse.ArgumentParser(
            description='Financial Market Analysis Tool',
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        parser.add_argument(
            '-t', '--tickers',
            nargs='+',
            required=True,
            help='Stock tickers (space separated) e.g. -t AAPL MSFT'
        )
        parser.add_argument(
            '-s', '--start_date',
            required=True,
            help='Start date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '-e', '--end_date',
            help='End date in YYYY-MM-DD format (default: today)'
        )
        parser.add_argument(
            '-f', '--freq',
            choices=['daily', 'weekly', 'monthly'],
            default='daily',
            help='Data frequency (default: daily)'
        )
        parser.add_argument(
            '--no-plots',
            action='store_true',
            help='Disable plot generation'
        )
        parser.add_argument(
            '--cache-days',
            type=int,
            default=30,
            help='Days to keep cached data (0=disable, default: 30)'
        )

        # Handle case when no args provided (VS Code debugging)
        if len(sys.argv) == 1 and 'debugpy' in sys.modules:
            print("\nNo arguments detected. Using VS Code debug defaults...")
            return {
                'tickers': ['AAPL', 'MSFT'],
                'start_date': '2020-01-01',
                'end_date': datetime.now().strftime('%Y-%m-%d'),
                'freq': 'daily',
                'no_plots': False,
                'cache_days': 30
            }

        args = parser.parse_args()

        # Validate dates
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else datetime.now()
            
            if start_date > end_date:
                raise ValueError("Start date cannot be after end date")
                
            if start_date < datetime.now() - timedelta(days=365*20):
                print("Warning: Large date range may impact performance")

            return {
                'tickers': [t.upper() for t in args.tickers],
                'start_date': args.start_date,
                'end_date': args.end_date if args.end_date else None,
                'freq': args.freq,
                'no_plots': args.no_plots,
                'cache_days': args.cache_days
            }
            
        except ValueError as e:
            print(f"Date error: {str(e)}")
            sys.exit(1)
        
    def run(self):
        """Main execution flow with enhanced error handling."""
        params = self.get_user_input()
        
        print(f"\n{'='*40}")
        print(f"Running analysis for: {', '.join(params['tickers'])}")
        print(f"Date Range: {params['start_date']} to {params['end_date'] or 'today'}")
        print(f"Frequency: {params['freq']}")
        print(f"Caching: {params['cache_days']} days retention")
        print(f"Plots {'disabled' if params['no_plots'] else 'enabled'}")
        print(f"{'='*40}\n")

        for ticker in params['tickers']:
            try:
                print(f"\n{'='*30}")
                print(f"Processing {ticker}...")
                
                # Check cache first
                df = self._get_data_with_cache(ticker, params)
                
                if df.empty:
                    print(f"No data available for {ticker}")
                    continue
                    
                # Perform analysis
                analyzer = FinancialAnalyzer(df)
                
                if not params['no_plots']:
                    analyzer.plot_prices(
                        title=f"{ticker} Price Analysis",
                        save_path=f"data/{ticker}_prices.png"
                    )
                    analyzer.plot_technical_analysis(
                        save_path=f"data/{ticker}_technical.png"
                    )
                
                self._print_analysis_summary(ticker, analyzer, params)
                
            except Exception as e:
                print(f"Error processing {ticker}: {str(e)}")
                continue

    def _get_data_with_cache(self, ticker: str, params: Dict) -> pd.DataFrame:
        """Smart data fetching with caching."""
        # Try to load from cache first
        if self.db.table_exists(ticker) and params['cache_days'] > 0:
            df = self.db.load_data(
                ticker,
                start_date=params['start_date'],
                end_date=params['end_date']
            )
            
            if not df.empty:
                print(f"Loaded cached data for {ticker}")
                return df
                
        # Fetch fresh data
        print(f"Fetching new data for {ticker}...")
        df = self.fetcher.fetch_data(
            ticker,
            start_date=params['start_date'],
            end_date=params['end_date'],
            freq=params['freq']
        )
        
        if not df.empty:
            self.db.save_data(df, ticker)
            if params['cache_days'] > 0:
                self.db.clean_old_data(ticker, params['cache_days'])
        
        return df

    def _print_analysis_summary(self, ticker: str, analyzer: FinancialAnalyzer, params: Dict):
        """Generate comprehensive output report."""
        returns = analyzer.calculate_returns()
        ma = analyzer.moving_averages()
        bb = analyzer.bollinger_bands()
        current_bb_width = (bb['upper'].iloc[-1] - bb['lower'].iloc[-1])
        
        print(f"\n{ticker} Analysis Summary:")
        print(f"- Latest Price: {analyzer.data['adjClose'].iloc[-1]:.2f}")
        print(f"- 50-Day MA: {ma['ma_50'].iloc[-1]:.2f}")
        print(f"- 200-Day MA: {ma['ma_200'].iloc[-1]:.2f}")
        
        print("\nRecent Volatility:")
        print(f"- Current Bollinger Band Width: {current_bb_width:.2f}")
        print(f"- 30-Day Average True Range: {analyzer.atr(30).iloc[-1]:.2f}")
        
        print("\nPerformance Metrics:")
        print(f"- 1 Month Return: {returns['daily'].iloc[-21:].sum()*100:.2f}%")
        print(f"- YTD Return: {returns['daily'].iloc[-252:].sum()*100:.2f}%")
        
        if hasattr(self.fetcher, 'cost_tracker'):
            cost = self.fetcher.cost_tracker.estimate_cost()
            print(f"\nAPI Usage: {self.fetcher.cost_tracker.calls} calls (Est. cost: ${cost:.4f})")

if __name__ == "__main__":
    try:
        tool = FinancialAnalysisTool()
        tool.run()
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nCritical error: {str(e)}")
        sys.exit(1)