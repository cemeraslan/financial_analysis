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
        
    def plot_prices(self, title='Stock Prices', save_path=None):
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
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
        
    def plot_returns(self, save_path=None):
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
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()

    def rsi(self, window=14):
        """Calculate Relative Strength Index"""
        delta = self.data['adjClose'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def macd(self, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = self.data['adjClose'].ewm(span=fast).mean()
        ema_slow = self.data['adjClose'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        return macd_line, signal_line
# In analysis.py
    def plot_technical_analysis(self, save_path=None):
        """Plot price with Bollinger Bands and volume"""
        try:
            import seaborn as sns
            sns.set_theme(style="whitegrid")
        except:
            plt.style.use('ggplot')
        
        # Initialize figure FIRST
        fig, (ax1, ax2) = plt.subplots(
            2, 1, 
            figsize=(14, 10), 
            gridspec_kw={'height_ratios': [3, 1]}
        )
        
        # Now safe to use ax1 and ax2
        bb = self.bollinger_bands()
        
        # Plot to ax1
        ax1.plot(self.data.index, self.data['adjClose'], 
                label='Price', linewidth=2)
        ax1.plot(bb['upper'], label='Upper Band', 
                linestyle='--', alpha=0.7)
        ax1.plot(bb['middle'], label='Middle Band', alpha=0.7)
        ax1.plot(bb['lower'], label='Lower Band', 
                linestyle='--', alpha=0.7)
        ax1.set_title('Price with Bollinger Bands')
        ax1.legend()
        
        # Plot to ax2
        ax2.bar(self.data.index, self.data['volume'], 
            color='skyblue', alpha=0.7)
        ax2.set_title('Volume')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

#bollinger bands
    def bollinger_bands(self, window=20, num_std=2):
        rolling_mean = self.data['adjClose'].rolling(window).mean()
        rolling_std = self.data['adjClose'].rolling(window).std()
        return {
            'upper': rolling_mean + (rolling_std * num_std),
            'middle': rolling_mean,
            'lower': rolling_mean - (rolling_std * num_std)
}  # Make sure this is properly indented    
    def atr(self, window=14):
        required_columns = {'high', 'low', 'adjClose'}
        if not required_columns.issubset(self.data.columns):
            raise ValueError("Data must contain high, low, and adjClose columns")
        # ... rest of calculation ...

        high = self.data['high']
        low = self.data['low']
        close = self.data['adjClose']
        
        # Calculate True Range components
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        
        # True Range is the greatest of the three values
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Average True Range
        return true_range.rolling(window).mean()