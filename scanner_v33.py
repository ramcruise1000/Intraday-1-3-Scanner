#!/usr/bin/env python3
"""
Scanner v3.3 - Extended Session Adaptive System
09:30-14:30 IST | 1:3 RR | 10-Day Adaptive Learning
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('scanner_v33.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class AdaptiveScannerV33:
    def __init__(self):
        self.version = "3.3.0"
        self.config = self._load_config()
        self.journal_path = "journal_v33/"
        self.trade_journal = f"{self.journal_path}trade_journal_v33.csv"
        self.daily_summary = f"{self.journal_path}daily_summary_v33.csv"
        self.scan_start = "09:30"
        self.scan_end = "14:30"
        self.capital = self.config.get('capital', 25000)
        self.risk_pct = self.config.get('risk_pct', 0.25)
        self.rr = 3.0
        self.lookback_days = 10
        self.min_confluence_score = 7
        self._init_journal()

    def _load_config(self):
        config = {}
        if os.path.exists('config_v33.json'):
            with open('config_v33.json', 'r') as f:
                config = json.load(f)
        config['capital'] = float(os.getenv('SCANNER_V33_CAPITAL', config.get('capital', 25000)))
        config['risk_pct'] = float(os.getenv('SCANNER_V33_RISK', config.get('risk_pct', 0.25)))
        config['telegram_token'] = os.getenv('TELEGRAM_BOT_TOKEN_V33', config.get('telegram_token', ''))
        config['telegram_chat'] = os.getenv('TELEGRAM_CHAT_ID_V33', config.get('telegram_chat', ''))
        return config

    def _init_journal(self):
        os.makedirs(self.journal_path, exist_ok=True)
        if not os.path.exists(self.trade_journal):
            pd.DataFrame(columns=['TradeID','Timestamp','Symbol','Direction','Entry','SL','Target','Qty','Risk_R','Confluence_Score','Status','Exit_Price','Exit_Time','PnL_R','PnL_Rs','Exit_Reason','DayOfWeek','Hour']).to_csv(self.trade_journal, index=False)
        if not os.path.exists(self.daily_summary):
            pd.DataFrame(columns=['Date','Trades_Taken','Win_Rate','Net_R','Net_Rs','Avg_Confluence','Verdict']).to_csv(self.daily_summary, index=False)

    def calculate_confluence_score(self, symbol, data):
        score = 0
        if len(data) < 20:
            return 0, {}
        ema_9 = data['Close'].ewm(span=9).mean().iloc[-1]
        ema_20 = data['Close'].ewm(span=20).mean().iloc[-1]
        price = data['Close'].iloc[-1]
        trend_score = 2 if price > ema_9 > ema_20 else (1 if price > ema_9 or ema_9 > ema_20 else 0)
        score += trend_score
        vol_avg = data['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = data['Volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
        vol_score = 2 if vol_ratio > 2.0 else (1.5 if vol_ratio > 1.5 else (0.5 if vol_ratio > 1.0 else 0))
        score += vol_score
        atr = (data['High'] - data['Low']).rolling(14).mean().iloc[-1]
        atr_pct = (atr / price) * 100
        vol_regime_score = 2 if 0.5 <= atr_pct <= 1.5 else (1 if 0.3 <= atr_pct <= 2.0 else 0)
        score += vol_regime_score
        rsi = self._calculate_rsi(data['Close'], 14).iloc[-1]
        momentum_score = 2 if 45 <= rsi <= 65 else (1 if 35 <= rsi <= 75 else 0)
        score += momentum_score
        current_hour = datetime.now().hour
        time_score = 1 if 10 <= current_hour <= 13 else 0
        score += time_score
        adaptive_score = self._get_adaptive_score(symbol)
        score += adaptive_score
        return score, {'trend': trend_score, 'volume': vol_score, 'volatility': vol_regime_score, 'momentum': momentum_score, 'time': time_score, 'adaptive': adaptive_score}

    def _calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _get_adaptive_score(self, symbol):
        if not os.path.exists(self.trade_journal):
            return 0.5
        df = pd.read_csv(self.trade_journal)
        if len(df) == 0:
            return 0.5
        cutoff = datetime.now() - timedelta(days=self.lookback_days)
        df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
        recent = df[df['Date'] >= cutoff.date()]
        symbol_recent = recent[recent['Symbol'] == symbol]
        if len(symbol_recent) == 0:
            return 0.5
        win_rate = len(symbol_recent[symbol_recent['PnL_R'] > 0]) / len(symbol_recent)
        avg_r = symbol_recent['PnL_R'].mean()
        if win_rate > 0.6 and avg_r > 1.0:
            return 1.0
        elif win_rate > 0.4:
            return 0.7
        elif win_rate < 0.3:
            return 0.0
        return 0.5

    def get_adaptive_position_size(self, base_qty):
        if not os.path.exists(self.trade_journal):
            return base_qty
        df = pd.read_csv(self.trade_journal)
        if len(df) < 5:
            return base_qty
        cutoff = datetime.now() - timedelta(days=self.lookback_days)
        df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
        recent = df[df['Date'] >= cutoff.date()]
        if len(recent) == 0:
            return base_qty
        net_r = recent['PnL_R'].sum()
        win_rate = len(recent[recent['PnL_R'] > 0]) / len(recent)
        multiplier = 1.0
        if win_rate > 0.5 and net_r > 5:
            multiplier = 1.5
        elif win_rate < 0.3 or net_r < -5:
            multiplier = 0.5
        return max(1, int(base_qty * multiplier))

    def generate_signal(self, symbol, data):
        score, factors = self.calculate_confluence_score(symbol, data)
        if score < self.min_confluence_score:
            return None
        price = data['Close'].iloc[-1]
        atr = (data['High'] - data['Low']).rolling(14).mean().iloc[-1]
        stop_distance = max(atr * 1.5, price * 0.005)
        target_distance = stop_distance * self.rr
        direction = "LONG" if price > data['Close'].ewm(span=20).mean().iloc[-1] else "SHORT"
        if direction == "LONG":
            entry, sl, target = price, price - stop_distance, price + target_distance
        else:
            entry, sl, target = price, price + stop_distance, price - target_distance
        risk_amount = self.capital * (self.risk_pct / 100)
        qty = int(risk_amount / stop_distance)
        qty = self.get_adaptive_position_size(qty)
        if qty * entry > self.capital:
            qty = int(self.capital / entry)
        if qty < 1:
            return None
        return {'symbol': symbol, 'direction': direction, 'entry': round(entry,2), 'sl': round(sl,2), 'target': round(target,2), 'qty': qty, 'risk_r': 1.0, 'confluence_score': score, 'factors': factors, 'timestamp': datetime.now().isoformat()}

    def run_once(self):
        logger.info(f"Scanner v{self.version} - Extended Session Mode")
        logger.info(f"Session: {self.scan_start} - {self.scan_end} IST")
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        if current_time < self.scan_start or current_time > self.scan_end:
            logger.info(f"Outside session window ({current_time})")
            return
        universe_file = 'universe_nifty100.txt'
        if not os.path.exists(universe_file):
            logger.error(f"Universe file not found")
            return
        with open(universe_file, 'r') as f:
            symbols = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        signals_generated = 0
        for symbol in symbols:
            try:
                import yfinance as yf
                data = yf.download(symbol, period='1d', interval='5m', progress=False)
                if len(data) < 20:
                    continue
                signal = self.generate_signal(symbol, data)
                if signal:
                    self._record_signal(signal)
                    signals_generated += 1
                    logger.info(f"SIGNAL: {symbol} {signal['direction']} @ {signal['entry']} Score: {signal['confluence_score']}/10")
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        logger.info(f"Cycle complete. Signals: {signals_generated}")
        self._update_daily_summary()

    def _record_signal(self, signal):
        trade_id = f"V33_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{signal['symbol']}"
        new_row = {'TradeID': trade_id, 'Timestamp': signal['timestamp'], 'Symbol': signal['symbol'], 'Direction': signal['direction'], 'Entry': signal['entry'], 'SL': signal['sl'], 'Target': signal['target'], 'Qty': signal['qty'], 'Risk_R': signal['risk_r'], 'Confluence_Score': signal['confluence_score'], 'Status': 'OPEN', 'DayOfWeek': datetime.now().strftime('%A'), 'Hour': datetime.now().hour}
        df = pd.read_csv(self.trade_journal)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.trade_journal, index=False)
        if self.config.get('telegram_token'):
            self._send_telegram_alert(signal, trade_id)

    def _send_telegram_alert(self, signal, trade_id):
        try:
            import requests
            message = f"🎯 V33 Signal (Quality: {signal['confluence_score']}/10)
Symbol: {signal['symbol']}
Direction: {signal['direction']}
Entry: ₹{signal['entry']}
SL: ₹{signal['sl']}
Target: ₹{signal['target']} (1:3 RR)
Qty: {signal['qty']}
ID: {trade_id}"
            url = f"https://api.telegram.org/bot{self.config['telegram_token']}/sendMessage"
            requests.post(url, json={'chat_id': self.config['telegram_chat'], 'text': message})
        except Exception as e:
            logger.error(f"Telegram error: {e}")

    def _update_daily_summary(self):
        if not os.path.exists(self.trade_journal):
            return
        df = pd.read_csv(self.trade_journal)
        today = datetime.now().date()
        df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
        today_df = df[df['Date'] == today]
        if len(today_df) == 0:
            return
        closed = today_df[today_df['Status'] == 'CLOSED']
        summary = {'Date': str(today), 'Trades_Taken': len(today_df), 'Win_Rate': len(closed[closed['PnL_R'] > 0]) / len(closed) if len(closed) > 0 else 0, 'Net_R': closed['PnL_R'].sum() if len(closed) > 0 else 0, 'Avg_Confluence': today_df['Confluence_Score'].mean(), 'Verdict': 'SUCCESS' if (len(closed) > 0 and closed['PnL_R'].sum() > 0) else 'PENDING'}
        summary_df = pd.read_csv(self.daily_summary)
        summary_df = summary_df[summary_df['Date'] != str(today)]
        summary_df = pd.concat([summary_df, pd.DataFrame([summary])], ignore_index=True)
        summary_df.to_csv(self.daily_summary, index=False)

if __name__ == "__main__":
    scanner = AdaptiveScannerV33()
    if "--once" in sys.argv:
        scanner.run_once()
    elif "--loop" in sys.argv:
        while True:
            now = datetime.now()
            if now.strftime("%H:%M") > scanner.scan_end:
                break
            scanner.run_once()
            time.sleep(300)
    else:
        print("Usage: python scanner_v33.py [--once|--loop]")
