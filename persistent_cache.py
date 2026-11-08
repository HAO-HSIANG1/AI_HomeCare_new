"""Local, versioned road-leg cache; no transit dates or identifiers are stored.

Cached durations are directional, expire, and are invalidated by map version or
endpoint changes. This database is runtime data and is excluded from releases.
"""
from pathlib import Path
import json
import os
import sqlite3
import time


def cache_path():
    folder = Path(os.getenv('CAREFLOW_CACHE_DIR',str(Path(__file__).parent/'output_results'/'cache')))
    folder.mkdir(parents=True,exist_ok=True)
    return folder/'road_legs.sqlite3'


def read_legs(keys):
    encoded = {json.dumps(key,separators=(',',':'),ensure_ascii=True):key for key in keys}
    if not encoded:
        return {}
    result = {}
    try:
        with sqlite3.connect(cache_path(),timeout=3) as db:
            db.execute('CREATE TABLE IF NOT EXISTS road_legs (key TEXT PRIMARY KEY, minutes REAL NOT NULL, updated REAL NOT NULL)')
            items = list(encoded)
            cutoff = time.time()-max(1,int(os.getenv('CAREFLOW_ROAD_CACHE_DAYS','30')))*86400
            for i in range(0,len(items),400):
                batch = items[i:i+400]
                query = 'SELECT key,minutes FROM road_legs WHERE updated>=? AND key IN ('+','.join('?' for _ in batch)+')'
                for key,minutes in db.execute(query,[cutoff,*batch]):
                    result[encoded[key]] = float(minutes)
    except (OSError,sqlite3.Error,ValueError):
        # Cache failure only means a fresh real-road request; it never supplies
        # a guessed route or makes a missing duration appear valid.
        return {}
    return result


def write_legs(values):
    if not values:
        return
    try:
        now = time.time()
        with sqlite3.connect(cache_path(),timeout=3) as db:
            db.execute('CREATE TABLE IF NOT EXISTS road_legs (key TEXT PRIMARY KEY, minutes REAL NOT NULL, updated REAL NOT NULL)')
            db.executemany('INSERT OR REPLACE INTO road_legs VALUES(?,?,?)',
                [(json.dumps(key,separators=(',',':'),ensure_ascii=True),float(minutes),now) for key,minutes in values.items()])
    except (OSError,sqlite3.Error,ValueError):
        pass



# ---- Google 大眾運輸路段（只存「星期幾＋時刻」，不存日期） ----
# 同一份資料重排時不再重查 Google，結果才會每次一致。查無路線也存（記成 -1），
# 否則每次都重查、每次都可能改用估算值。
_NO_ROUTE = -1.0


def _transit_cutoff():
    return time.time()-max(1,int(os.getenv('CAREFLOW_TRANSIT_CACHE_DAYS','30')))*86400


def read_transit(keys):
    """回傳 {key: 分鐘}；查無路線的回傳 inf。快取壞掉時回傳空字典（改成重新查 Google）。"""
    encoded = {json.dumps(key,separators=(',',':'),ensure_ascii=True):key for key in keys}
    if not encoded:
        return {}
    result = {}
    try:
        with sqlite3.connect(cache_path(),timeout=3) as db:
            db.execute('CREATE TABLE IF NOT EXISTS transit_legs (key TEXT PRIMARY KEY, minutes REAL NOT NULL, updated REAL NOT NULL)')
            items = list(encoded)
            cutoff = _transit_cutoff()
            for i in range(0,len(items),400):
                batch = items[i:i+400]
                query = 'SELECT key,minutes FROM transit_legs WHERE updated>=? AND key IN ('+','.join('?' for _ in batch)+')'
                for key,minutes in db.execute(query,[cutoff,*batch]):
                    minutes = float(minutes)
                    result[encoded[key]] = float('inf') if minutes < 0 else minutes
    except (OSError,sqlite3.Error,ValueError):
        return {}
    return result


def write_transit(values):
    if not values:
        return
    rows = []
    now = time.time()
    for key,minutes in values.items():
        minutes = float(minutes)
        if minutes != minutes:      # NaN 不存
            continue
        rows.append((json.dumps(key,separators=(',',':'),ensure_ascii=True),
                     _NO_ROUTE if minutes == float('inf') or minutes < 0 else minutes, now))
    if not rows:
        return
    try:
        with sqlite3.connect(cache_path(),timeout=3) as db:
            db.execute('CREATE TABLE IF NOT EXISTS transit_legs (key TEXT PRIMARY KEY, minutes REAL NOT NULL, updated REAL NOT NULL)')
            db.executemany('INSERT OR REPLACE INTO transit_legs VALUES(?,?,?)', rows)
    except (OSError,sqlite3.Error,ValueError):
        pass
