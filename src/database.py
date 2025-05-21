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
    
    # In database.py
    def clean_old_data(self, table_name, keep_days=30):
        """Remove data older than keep_days"""
        if keep_days <= 0:
            return
            
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        query = f"DELETE FROM {table_name} WHERE date < '{cutoff_date}'"
        
        try:
            with self.engine.connect() as conn:
                conn.execute(query)
            print(f"Cleaned data older than {keep_days} days from {table_name}")
        except Exception as e:
            print(f"Error cleaning old data: {str(e)}")
