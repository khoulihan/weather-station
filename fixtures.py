"""
Fixture data for testing.
"""

import random
from datetime import date, datetime, timedelta, timezone


start = datetime.utcnow().replace(minute=0, microsecond=0, second=0)
temperatures = []
for minutes in range(0, 1440, 15):
    current = start - timedelta(minutes=minutes)
    temperatures.append({
        'when_recorded': current,
        'temperature': random.uniform(16.0, 24.0),
        'resolution': 15
    })


pressures = []
for minutes in range(0, 1440, 15):
    current = start - timedelta(minutes=minutes)
    pressures.append({
        'when_recorded': current,
        'pressure': random.uniform(98.0, 102.0),
        'resolution': 15
    })


daily_temperatures = [
    { 'day': (date.today() - timedelta(days=47)), "mean": 16.2, "median": 16.2, "high": 22.4, "low": 10.2 },
    { 'day': (date.today() - timedelta(days=46)), "mean": 17.1, "median": 17.1, "high": 25.2, "low": 10.4 },
    { 'day': (date.today() - timedelta(days=45)), "mean": 16.2, "median": 16.2, "high": 20.8, "low": 11.9 },
    { 'day': (date.today() - timedelta(days=44)), "mean": 15.2, "median": 15.2, "high": 19.9, "low": 11.3 },
    { 'day': (date.today() - timedelta(days=43)), "mean": 14.9, "median": 14.9, "high": 19.6, "low": 8.9 },
    { 'day': (date.today() - timedelta(days=42)), "mean": 19.5, "median": 19.5, "high": 29.7, "low": 10.9 },
    { 'day': (date.today() - timedelta(days=41)), "mean": 13.7, "median": 13.7, "high": 17.4, "low": 10.8 },
    { 'day': (date.today() - timedelta(days=40)), "mean": 13.2, "median": 13.2, "high": 16.2, "low": 11.2 },
    { 'day': (date.today() - timedelta(days=39)), "mean": 13.6, "median": 13.6, "high": 17.5, "low": 10.9 },
    { 'day': (date.today() - timedelta(days=38)), "mean": 14.1, "median": 14.1, "high": 16.8, "low": 11.3 },
    { 'day': (date.today() - timedelta(days=37)), "mean": 17.1, "median": 17.1, "high": 21.9, "low": 13.9 },
    { 'day': (date.today() - timedelta(days=36)), "mean": 14.9, "median": 14.9, "high": 18.0, "low": 12.0 },
    { 'day': (date.today() - timedelta(days=35)), "mean": 15.3, "median": 15.3, "high": 18.3, "low": 13.3 },
    { 'day': (date.today() - timedelta(days=34)), "mean": 14.4, "median": 14.4, "high": 16.9, "low": 11.9 },
    { 'day': (date.today() - timedelta(days=33)), "mean": 12.6, "median": 12.6, "high": 14.6, "low": 9.8 },
    { 'day': (date.today() - timedelta(days=32)), "mean": 12.5, "median": 12.5, "high": 18.7, "low": 7.6 },
    { 'day': (date.today() - timedelta(days=31)), "mean": 11.5, "median": 11.5, "high": 17.0, "low": 6.8 },
    { 'day': (date.today() - timedelta(days=30)), "mean": 13.3, "median": 13.3, "high": 17.4, "low": 9.9 },
    { 'day': (date.today() - timedelta(days=29)), "mean": 16.1, "median": 16.1, "high": 22.1, "low": 8.8 },
    { 'day': (date.today() - timedelta(days=28)), "mean": 16.4, "median": 16.4, "high": 19.9, "low": 14.3 },
    { 'day': (date.today() - timedelta(days=27)), "mean": 16.1, "median": 16.1, "high": 20.1, "low": 14.0 },
    { 'day': (date.today() - timedelta(days=26)), "mean": 15.3, "median": 15.3, "high": 18.5, "low": 13.3 },
    { 'day': (date.today() - timedelta(days=25)), "mean": 15.3, "median": 15.3, "high": 19.6, "low": 11.6 },
    { 'day': (date.today() - timedelta(days=24)), "mean": 15.9, "median": 15.9, "high": 18.7, "low": 13.2 },
    { 'day': (date.today() - timedelta(days=23)), "mean": 18.5, "median": 18.5, "high": 22.3, "low": 14.8 },
    { 'day': (date.today() - timedelta(days=22)), "mean": 16.9, "median": 16.9, "high": 21.0, "low": 14.4 },
    { 'day': (date.today() - timedelta(days=21)), "mean": 18.1, "median": 18.1, "high": 23.9, "low": 14.6 },
    { 'day': (date.today() - timedelta(days=20)), "mean": 18.1, "median": 18.1, "high": 23.4, "low": 13.4 },
    { 'day': (date.today() - timedelta(days=19)), "mean": 18.8, "median": 18.8, "high": 24.0, "low": 13.9 },
    { 'day': (date.today() - timedelta(days=18)), "mean": 18.0, "median": 18.0, "high": 22.2, "low": 13.8 },
    { 'day': (date.today() - timedelta(days=17)), "mean": 19.4, "median": 19.4, "high": 25.1, "low": 15.5 },
    { 'day': (date.today() - timedelta(days=16)), "mean": 17.7, "median": 17.7, "high": 22.6, "low": 14.0 },
    { 'day': (date.today() - timedelta(days=15)), "mean": 16.9, "median": 16.9, "high": 21.0, "low": 14.2 },
    { 'day': (date.today() - timedelta(days=14)), "mean": 17.3, "median": 17.3, "high": 21.1, "low": 13.2 },
    { 'day': (date.today() - timedelta(days=13)), "mean": 17.6, "median": 17.6, "high": 21.5, "low": 12.6 },
    { 'day': (date.today() - timedelta(days=12)), "mean": 18.3, "median": 18.3, "high": 22.9, "low": 13.2 },
    { 'day': (date.today() - timedelta(days=11)), "mean": 21.8, "median": 21.8, "high": 29.4, "low": 14.8 },
    { 'day': (date.today() - timedelta(days=10)), "mean": 20.2, "median": 20.2, "high": 24.1, "low": 15.3 },
    { 'day': (date.today() - timedelta(days=9)), "mean": 21.4, "median": 21.4, "high": 26.2, "low": 17.1 },
    { 'day': (date.today() - timedelta(days=8)), "mean": 19.7, "median": 19.7, "high": 23.0, "low": 18.2 },
    { 'day': (date.today() - timedelta(days=7)), "mean": 19.4, "median": 19.4, "high": 25.2, "low": 14.9 },
    { 'day': (date.today() - timedelta(days=6)), "mean": 20.3, "median": 20.3, "high": 25.0, "low": 12.8 },
    { 'day': (date.today() - timedelta(days=5)), "mean": 21.3, "median": 21.3, "high": 24.6, "low": 17.9 },
    { 'day': (date.today() - timedelta(days=4)), "mean": 21.4, "median": 21.4, "high": 28.2, "low": 18.0 },
    { 'day': (date.today() - timedelta(days=3)), "mean": 26.3, "median": 26.3, "high": 35.8, "low": 17.8 },
    { 'day': (date.today() - timedelta(days=2)), "mean": 22.0, "median": 22.0, "high": 25.9, "low": 17.6 },
    { 'day': (date.today() - timedelta(days=1)), "mean": 20.2, "median": 20.2, "high": 24.1, "low": 16.0 },
    { 'day': date.today(), "mean": 20.2, "median": 20.2, "high": 23.9, "low": 17.4 }
]

daily_pressures = []
today = date.today()
for d in range(1, 47):
    high = random.uniform(100.0, 102.0)
    low = random.uniform(98.0, 100.0)
    mean = (high + low) / 2
    median = mean
    daily_pressures.append({
        'day': today - timedelta(days=d),
        'high': high,
        'low': low,
        'mean': mean,
        'median': median
    })
