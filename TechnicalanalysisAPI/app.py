from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import math
import os

app = Flask(__name__)
CORS(app)

def safe_float(value, default=0.0):
    """Safely convert value to float, handling NaN and Infinity"""
    if pd.isna(value) or math.isinf(value) or math.isnan(value):
        return default
    return float(value)

def calculate_rsi(data, period=14):
    """Calculate RSI with safe handling"""
    try:
        delta = data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        avg_loss = avg_loss.replace(0, 0.01)
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        result = rsi.iloc[-1] if len(rsi) > 0 else 50
        return safe_float(result, 50)
    except Exception:
        return 50

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD with safe handling"""
    try:
        exp1 = data['Close'].ewm(span=fast).mean()
        exp2 = data['Close'].ewm(span=slow).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': safe_float(macd_line.iloc[-1], 0),
            'signal': safe_float(signal_line.iloc[-1], 0),
            'histogram': safe_float(histogram.iloc[-1], 0)
        }
    except Exception:
        return {'macd': 0, 'signal': 0, 'histogram': 0}

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """Calculate Bollinger Bands with safe handling"""
    try:
        sma = data['Close'].rolling(window=period).mean()
        std = data['Close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        current_price = data['Close'].iloc[-1]
        
        return {
            'upper': safe_float(upper_band.iloc[-1], current_price * 1.1),
            'middle': safe_float(sma.iloc[-1], current_price),
            'lower': safe_float(lower_band.iloc[-1], current_price * 0.9),
            'current': safe_float(current_price, 0)
        }
    except Exception:
        current_price = safe_float(data['Close'].iloc[-1], 100)
        return {
            'upper': current_price * 1.1,
            'middle': current_price,
            'lower': current_price * 0.9,
            'current': current_price
        }

def calculate_moving_average_crossover(data, short=50, long=200):
    """Calculate Moving Average Crossover with safe handling"""
    try:
        if len(data) < long:
            short, long = min(5, len(data)//2), min(10, len(data)-1)
        
        short_ma = data['Close'].rolling(window=short).mean()
        long_ma = data['Close'].rolling(window=long).mean()
        
        short_val = safe_float(short_ma.iloc[-1], data['Close'].iloc[-1])
        long_val = safe_float(long_ma.iloc[-1], data['Close'].iloc[-1])
        
        return {
            'short_ma': short_val,
            'long_ma': long_val,
            'crossover': short_val > long_val
        }
    except Exception:
        current_price = safe_float(data['Close'].iloc[-1], 100)
        return {
            'short_ma': current_price,
            'long_ma': current_price,
            'crossover': False
        }

def calculate_volatility(data, period=14):
    """Calculate Volatility with safe handling"""
    try:
        if len(data) < period:
            return 2.0
        
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        current_price = safe_float(data['Close'].iloc[-1], 100)
        atr_val = safe_float(atr.iloc[-1], current_price * 0.02)
        
        if current_price <= 0:
            return 2.0
        
        volatility_pct = (atr_val / current_price) * 100
        return safe_float(volatility_pct, 2.0)
    except Exception:
        return 2.0

def get_indicator_signals(indicators):
    """Get individual indicator signals"""
    signals = {}
    
    # RSI Signal
    rsi = indicators['rsi']
    if rsi < 30:
        signals['rsi'] = 'Buy'
    elif rsi > 70:
        signals['rsi'] = 'Sell'
    else:
        signals['rsi'] = 'Hold'
    
    # MACD Signal
    macd_data = indicators['macd']
    if macd_data['macd'] > macd_data['signal'] and macd_data['histogram'] > 0:
        signals['macd'] = 'Buy'
    elif macd_data['macd'] < macd_data['signal'] and macd_data['histogram'] < 0:
        signals['macd'] = 'Sell'
    else:
        signals['macd'] = 'Hold'
    
    # Moving Average Signal
    ma_data = indicators['moving_average']
    if ma_data['crossover']:
        signals['moving_average'] = 'Buy'
    else:
        signals['moving_average'] = 'Sell'
    
    # Bollinger Bands Signal
    bb_data = indicators['bollinger_bands']
    if bb_data['current'] < bb_data['lower']:
        signals['bollinger_bands'] = 'Buy'
    elif bb_data['current'] > bb_data['upper']:
        signals['bollinger_bands'] = 'Sell'
    else:
        signals['bollinger_bands'] = 'Hold'
    
    # Volatility Signal
    volatility = indicators['volatility']
    if volatility > 5:
        signals['volatility'] = 'Sell'
    elif volatility < 2:
        signals['volatility'] = 'Buy'
    else:
        signals['volatility'] = 'Hold'
    
    return signals

def calculate_final_suggestion(signals):
    """Calculate final suggestion based on priority system"""
    buy_count = sum(1 for signal in signals.values() if signal == 'Buy')
    sell_count = sum(1 for signal in signals.values() if signal == 'Sell')
    
    if buy_count >= 3:
        return 'Strong Buy'
    elif sell_count >= 3:
        return 'Strong Sell'
    elif buy_count > sell_count:
        return 'Buy'
    elif sell_count > buy_count:
        return 'Sell'
    else:
        return 'Hold'

# Comprehensive Indian stocks database
INDIAN_STOCKS = [
    {'symbol': 'RELIANCE.NS', 'name': 'Reliance Industries Ltd'},
    {'symbol': 'TCS.NS', 'name': 'Tata Consultancy Services Ltd'},
    {'symbol': 'HDFCBANK.NS', 'name': 'HDFC Bank Ltd'},
    {'symbol': 'ICICIBANK.NS', 'name': 'ICICI Bank Ltd'},
    {'symbol': 'SBIN.NS', 'name': 'State Bank of India'},
    {'symbol': 'INFY.NS', 'name': 'Infosys Ltd'},
    {'symbol': 'HINDUNILVR.NS', 'name': 'Hindustan Unilever Ltd'},
    {'symbol': 'ITC.NS', 'name': 'ITC Ltd'},
    {'symbol': 'KOTAKBANK.NS', 'name': 'Kotak Mahindra Bank Ltd'},
    {'symbol': 'AXISBANK.NS', 'name': 'Axis Bank Ltd'},
    {'symbol': 'LT.NS', 'name': 'Larsen & Toubro Ltd'},
    {'symbol': 'WIPRO.NS', 'name': 'Wipro Ltd'},
    {'symbol': 'MARUTI.NS', 'name': 'Maruti Suzuki India Ltd'},
    {'symbol': 'BAJFINANCE.NS', 'name': 'Bajaj Finance Ltd'},
    {'symbol': 'HCLTECH.NS', 'name': 'HCL Technologies Ltd'},
    {'symbol': 'ASIANPAINT.NS', 'name': 'Asian Paints Ltd'},
    {'symbol': 'BHARTIARTL.NS', 'name': 'Bharti Airtel Ltd'},
    {'symbol': 'SUNPHARMA.NS', 'name': 'Sun Pharmaceutical Industries Ltd'},
    {'symbol': 'TITAN.NS', 'name': 'Titan Company Ltd'},
    {'symbol': 'ULTRACEMCO.NS', 'name': 'UltraTech Cement Ltd'},
    {'symbol': 'NESTLEIND.NS', 'name': 'Nestle India Ltd'},
    {'symbol': 'POWERGRID.NS', 'name': 'Power Grid Corporation of India Ltd'},
    {'symbol': 'NTPC.NS', 'name': 'NTPC Ltd'},
    {'symbol': 'ONGC.NS', 'name': 'Oil and Natural Gas Corporation Ltd'},
    {'symbol': 'TATASTEEL.NS', 'name': 'Tata Steel Ltd'},
    {'symbol': 'TECHM.NS', 'name': 'Tech Mahindra Ltd'},
    {'symbol': 'JSWSTEEL.NS', 'name': 'JSW Steel Ltd'},
    {'symbol': 'INDUSINDBK.NS', 'name': 'IndusInd Bank Ltd'},
    {'symbol': 'DRREDDY.NS', 'name': 'Dr. Reddy\'s Laboratories Ltd'},
    {'symbol': 'CIPLA.NS', 'name': 'Cipla Ltd'},
    {'symbol': 'ADANIPORTS.NS', 'name': 'Adani Ports and SEZ Ltd'},
    {'symbol': 'ADANIGREEN.NS', 'name': 'Adani Green Energy Ltd'},
    {'symbol': 'BAJAJ-AUTO.NS', 'name': 'Bajaj Auto Ltd'},
    {'symbol': 'BPCL.NS', 'name': 'Bharat Petroleum Corporation Ltd'},
    {'symbol': 'COALINDIA.NS', 'name': 'Coal India Ltd'},
    {'symbol': 'DIVISLAB.NS', 'name': 'Divi\'s Laboratories Ltd'},
    {'symbol': 'EICHERMOT.NS', 'name': 'Eicher Motors Ltd'},
    {'symbol': 'GRASIM.NS', 'name': 'Grasim Industries Ltd'},
    {'symbol': 'HDFCLIFE.NS', 'name': 'HDFC Life Insurance Company Ltd'},
    {'symbol': 'HEROMOTOCO.NS', 'name': 'Hero MotoCorp Ltd'},
    {'symbol': 'HINDALCO.NS', 'name': 'Hindalco Industries Ltd'},
    {'symbol': 'IOC.NS', 'name': 'Indian Oil Corporation Ltd'},
    {'symbol': 'M&M.NS', 'name': 'Mahindra & Mahindra Ltd'},
    {'symbol': 'SBILIFE.NS', 'name': 'SBI Life Insurance Company Ltd'},
    {'symbol': 'TATACONSUM.NS', 'name': 'Tata Consumer Products Ltd'},
    {'symbol': 'TATAMOTORS.NS', 'name': 'Tata Motors Ltd'},
    {'symbol': 'UPL.NS', 'name': 'UPL Ltd'},
    {'symbol': 'VEDL.NS', 'name': 'Vedanta Ltd'},
    {'symbol': 'APOLLOHOSP.NS', 'name': 'Apollo Hospitals Enterprise Ltd'},
    {'symbol': 'BRITANNIA.NS', 'name': 'Britannia Industries Ltd'},
    {'symbol': 'DABUR.NS', 'name': 'Dabur India Ltd'},
    {'symbol': 'GODREJCP.NS', 'name': 'Godrej Consumer Products Ltd'},
    {'symbol': 'MARICO.NS', 'name': 'Marico Ltd'},
    {'symbol': 'PIDILITIND.NS', 'name': 'Pidilite Industries Ltd'},
    {'symbol': 'DMART.NS', 'name': 'Avenue Supermarts Limited'},
    {'symbol': 'BANDHANBNK.NS', 'name': 'Bandhan Bank Ltd'},
    {'symbol': 'FEDERALBNK.NS', 'name': 'Federal Bank Ltd'},
    {'symbol': 'IDFCFIRSTB.NS', 'name': 'IDFC First Bank Ltd'},
    {'symbol': 'PNB.NS', 'name': 'Punjab National Bank'},
    {'symbol': 'CANBK.NS', 'name': 'Canara Bank'},
    {'symbol': 'BANKBARODA.NS', 'name': 'Bank of Baroda'},
    {'symbol': 'YESBANK.NS', 'name': 'Yes Bank Ltd'},
    {'symbol': 'MINDTREE.NS', 'name': 'Mindtree Ltd'},
    {'symbol': 'MPHASIS.NS', 'name': 'Mphasis Ltd'},
    {'symbol': 'LTI.NS', 'name': 'L&T Infotech Ltd'},
    {'symbol': 'COFORGE.NS', 'name': 'Coforge Ltd'},
    {'symbol': 'ASHOKLEY.NS', 'name': 'Ashok Leyland Ltd'},
    {'symbol': 'TVSMOTOR.NS', 'name': 'TVS Motor Company Ltd'},
    {'symbol': 'BAJAJFINSV.NS', 'name': 'Bajaj Finserv Ltd'},
    {'symbol': 'LUPIN.NS', 'name': 'Lupin Ltd'},
    {'symbol': 'BIOCON.NS', 'name': 'Biocon Ltd'},
    {'symbol': 'CADILAHC.NS', 'name': 'Cadila Healthcare Ltd'},
    {'symbol': 'TORNTPHARM.NS', 'name': 'Torrent Pharmaceuticals Ltd'},
    {'symbol': 'COLPAL.NS', 'name': 'Colgate Palmolive India Ltd'},
    {'symbol': 'JUBLFOOD.NS', 'name': 'Jubilant FoodWorks Ltd'},
    {'symbol': 'ZEEL.NS', 'name': 'Zee Entertainment Enterprises Ltd'},
    {'symbol': 'SAIL.NS', 'name': 'Steel Authority of India Ltd'},
    {'symbol': 'GMRINFRA.NS', 'name': 'GMR Infrastructure Ltd'},
    {'symbol': 'RPOWER.NS', 'name': 'Reliance Power Ltd'},
    {'symbol': 'SUZLON.NS', 'name': 'Suzlon Energy Ltd'},
    {'symbol': 'FORCEMOT.NS', 'name': 'Force Motors Ltd'},
]

def search_yahoo_finance_api(query):
    """Search using Yahoo Finance API with proper error handling"""
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10&newsCount=0"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            stocks = []
            
            for quote in data.get('quotes', []):
                symbol = quote.get('symbol', '')
                if symbol.endswith(('.NS', '.BO')):
                    stocks.append({
                        'symbol': symbol,
                        'name': quote.get('longname', quote.get('shortname', symbol))
                    })
            
            return stocks
        else:
            return []
            
    except Exception as e:
        return []

@app.route('/search', methods=['GET'])
def search_stocks():
    """Search stocks with fallback to local database"""
    query = request.args.get('q', '').strip().upper()
    
    if len(query) < 2:
        return jsonify([])
    
    try:
        # First try Yahoo Finance API
        live_results = search_yahoo_finance_api(query)
        
        # Search local database
        local_results = []
        for stock in INDIAN_STOCKS:
            if (query in stock['symbol'].upper() or 
                query in stock['name'].upper() or
                any(word.startswith(query) for word in stock['name'].upper().split())):
                local_results.append(stock)
        
        # Combine and remove duplicates
        all_results = live_results + local_results
        seen = set()
        unique_results = []
        for stock in all_results:
            if stock['symbol'] not in seen:
                seen.add(stock['symbol'])
                unique_results.append(stock)
        
        return jsonify(unique_results[:10])
        
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze stock with comprehensive error handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        symbol = data.get('symbol')
        if not symbol:
            return jsonify({'error': 'No stock symbol provided'}), 400
        
        # Fetch stock data from Yahoo Finance
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1y')
        
        if len(hist) < 20:
            return jsonify({'error': f'Insufficient data for {symbol}. Stock may not exist.'}), 400
        
        current_price = safe_float(hist['Close'].iloc[-1], 0)
        
        if current_price <= 0:
            return jsonify({'error': f'Invalid price data for {symbol}'}), 400
        
        # Get company info safely
        try:
            stock_info = stock.info
            company_name = stock_info.get('longName', symbol) if stock_info else symbol
        except Exception:
            company_name = symbol
        
        # Calculate all indicators
        indicators = {
            'rsi': calculate_rsi(hist),
            'macd': calculate_macd(hist),
            'moving_average': calculate_moving_average_crossover(hist),
            'bollinger_bands': calculate_bollinger_bands(hist),
            'volatility': calculate_volatility(hist)
        }
        
        signals = get_indicator_signals(indicators)
        final_suggestion = calculate_final_suggestion(signals)
        
        response_data = {
            'stock': symbol,
            'company_name': company_name,
            'current_price': round(current_price, 2),
            'indicators': {
                'rsi': {
                    'value': round(indicators['rsi'], 2),
                    'signal': signals['rsi']
                },
                'macd': {
                    'value': round(indicators['macd']['histogram'], 4),
                    'signal': signals['macd']
                },
                'moving_average': {
                    'short_ma': round(indicators['moving_average']['short_ma'], 2),
                    'long_ma': round(indicators['moving_average']['long_ma'], 2),
                    'signal': signals['moving_average']
                },
                'bollinger_bands': {
                    'current': round(indicators['bollinger_bands']['current'], 2),
                    'upper': round(indicators['bollinger_bands']['upper'], 2),
                    'lower': round(indicators['bollinger_bands']['lower'], 2),
                    'signal': signals['bollinger_bands']
                },
                'volatility': {
                    'value': round(indicators['volatility'], 2),
                    'signal': signals['volatility']
                }
            },
            'final_suggestion': final_suggestion,
            'signal_summary': {
                'buy_count': sum(1 for signal in signals.values() if signal == 'Buy'),
                'sell_count': sum(1 for signal in signals.values() if signal == 'Sell'),
                'hold_count': sum(1 for signal in signals.values() if signal == 'Hold')
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
@app.route('/')
def home():
    return "API is working"



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
