import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def BollingerBands(df: pd.DataFrame, window: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """
    Calculate Bollinger Bands for a given DataFrame using the "typical" price, which is the average of the high, low, and close prices.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame containing 'Close' prices.
        window (int): The number of periods to use for the moving average.
        std_dev (int): The number of standard deviations to use for the bands.
        
    Returns:
        pd.DataFrame: A DataFrame with Bollinger Bands added.
    """
    # Calculate the typical price
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    # Calculate the moving average
    df['SMA'] = df['Typical_Price'].rolling(window=window).mean()
    
    # Calculate the standard deviation
    df['STD'] = df['Typical_Price'].rolling(window=window).std()
    
    # Calculate the upper and lower Bollinger Bands
    df['BB_Upper'] = df['SMA'] + (std_dev * df['STD'])
    df['BB_Lower'] = df['SMA'] - (std_dev * df['STD'])
    
    # Calculate the Bollinger Band width
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
    
    return df



def PlotBollingerBands(df, title="Bollinger Bands Analysis", 
                       width=1200, height=700, 
                       show_stats=True, 
                       show_volume=False):
    """
    Plot Bollinger Bands with candlesticks for financial data.
    
    Parameters:
        df (pd.DataFrame): DataFrame with OHLCV data and BB columns
        title (str): Chart title
        width (int): Chart width in pixels
        height (int): Chart height in pixels
        show_stats (bool): Whether to print statistics
        show_volume (bool): Whether to show volume subplot
    
    Returns:
        plotly.graph_objects.Figure: The plotly figure object
    """
    
    # Create subplots if volume is requested
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(title, 'Volume'),
            row_width=[0.2, 0.7]
        )
    else:
        fig = go.Figure()
    
    # Add candlesticks
    candlestick = go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price',
        increasing_line_color='#00ff00',
        decreasing_line_color='#ff0000',
        increasing_fillcolor='#00ff00',
        decreasing_fillcolor='#ff0000'
    )
    
    if show_volume:
        fig.add_trace(candlestick, row=1, col=1)
    else:
        fig.add_trace(candlestick)
    
    # Add the SMA (middle line)
    sma_trace = go.Scatter(
        x=df.index,
        y=df['SMA'],
        mode='lines',
        name='SMA (20)',
        line=dict(color='#FFA500', width=2),
        opacity=0.8
    )
    
    if show_volume:
        fig.add_trace(sma_trace, row=1, col=1)
    else:
        fig.add_trace(sma_trace)
    
    # Add the upper Bollinger Band
    upper_bb = go.Scatter(
        x=df.index,
        y=df['BB_Upper'],
        mode='lines',
        name='Upper BB',
        line=dict(color='#FF6B6B', width=1, dash='dash'),
        opacity=0.7
    )
    
    if show_volume:
        fig.add_trace(upper_bb, row=1, col=1)
    else:
        fig.add_trace(upper_bb)
    
    # Add the lower Bollinger Band
    lower_bb = go.Scatter(
        x=df.index,
        y=df['BB_Lower'],
        mode='lines',
        name='Lower BB',
        line=dict(color='#4ECDC4', width=1, dash='dash'),
        opacity=0.7
    )
    
    if show_volume:
        fig.add_trace(lower_bb, row=1, col=1)
    else:
        fig.add_trace(lower_bb)
    
    # Fill the area between the bands
    fill_trace = go.Scatter(
        x=df.index.tolist() + df.index.tolist()[::-1],
        y=df['BB_Upper'].tolist() + df['BB_Lower'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(128,128,128,0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        name='BB Band',
        hoverinfo="skip",
        showlegend=False
    )
    
    if show_volume:
        fig.add_trace(fill_trace, row=1, col=1)
    else:
        fig.add_trace(fill_trace)
    
    # Add volume bars if requested
    if show_volume and 'Volume' in df.columns:
        colors = ['green' if close >= open else 'red' 
                 for close, open in zip(df['Close'], df['Open'])]
        
        volume_trace = go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        )
        fig.add_trace(volume_trace, row=2, col=1)
    
    # Update layout
    layout_updates = {
        'title': title if not show_volume else None,
        'xaxis_title': 'Time',
        'yaxis_title': 'Price',
        'hovermode': 'x unified',
        'width': width,
        'height': height,
        'showlegend': True,
        'template': 'plotly_white',
        'xaxis_rangeslider_visible': False
    }
    
    fig.update_layout(**layout_updates)
    
    # Update axes for subplots if volume is shown
    if show_volume:
        fig.update_xaxes(showticklabels=False, row=1, col=1)
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    # Display statistics if requested
    if show_stats:
        print("=" * 50)
        print("🔍 BOLLINGER BANDS ANALYSIS")
        print("=" * 50)
        print(f"📊 Data points: {len(df):,}")
        print(f"💰 Price range: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
        print(f"📏 Average band width: ${df['BB_Width'].mean():.2f}")
        print(f"🔴 Upper band touches: {(df['Close'] >= df['BB_Upper']).sum()}")
        print(f"🟢 Lower band touches: {(df['Close'] <= df['BB_Lower']).sum()}")
        
        # Calculate squeeze periods (when bands are narrow)
        avg_width = df['BB_Width'].mean()
        squeeze_periods = (df['BB_Width'] < avg_width * 0.8).sum()
        print(f"🤏 Squeeze periods: {squeeze_periods} ({squeeze_periods/len(df)*100:.1f}%)")
        
        # Recent volatility
        recent_volatility = df['STD'].tail(20).mean()
        print(f"📈 Recent volatility (20 periods): {recent_volatility:.2f}")
        
        print("=" * 50)
    
    return fig
