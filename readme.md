# 📊 ArthaPulse | 
Indonesia Financial Dashboard

ArthaPulse is a web-based financial dashboard application providing real-time analysis of IDX stock market data, USD/IDR exchange rates, and the Jakarta Composite Index (IHSG). Built entirely in Python using Streamlit, this application leverages Yahoo Finance data to deliver in-depth technical indicators.

## 🚀 Key Features
* **Real-Time Market Summary**: Monitored tracking of daily USD/IDR exchange rates and IHSG movements.
* **Automated Technical Analysis**: Equipped with technical indicators including Relative Strength Index (RSI), Moving Averages (MA20 & MA50), Bollinger Bands, and MACD.
* **Multi-Stock Comparison**: Comprehensive features to compare absolute performance, relative performance (Base=100), daily returns, and cross-stock correlation matrices.
* **Historical Data Extraction**: Access to full OHLCV data tables with customizable row-limit extraction.

## 🛠️ Architecture & Tech Stack
* **Language**: Python 3.x
* **Web Framework**: Streamlit
* **Data Provider**: Yahoo Finance (`yfinance`)
* **Data Analysis**: Pandas & NumPy

## 📦 Local Installation
1. Clone this repository:
   ```bash
   git clone [https://github.com/username/arthapulse.git](https://github.com/username/arthapulse.git)
   cd arthapulse

## Installation Guide:
1. Install the required dependencies:
    ```bash
    pip install streamlit yfinance pandas numpy

2. Launch the application:
    ```bash
    streamlit run arthapulse.py