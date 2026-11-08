"""公車／捷運交通存到硬碟：同一份資料重排時不再重查 Google，結果才會每次一致。"""
import math

import caregiver_engine as engine
import persistent_cache


A, B, C = (25.0330, 121.5654), (25.0478, 121.5170), (25.0950, 121.5250)   # 彼此都超過步行距離


def _fake_google(monkeypatch, calls, minutes_by_dest):
    def fetch(origins, destinations, departure=None, arrival=None):
        calls.append((tuple(origins), tuple(destinations), departure, arrival))
        return {engine._google_transit_key(*o, *d, departure=departure, arrival=arrival): minutes_by_dest[d]
                for o in origins for d in destinations}
    monkeypatch.setattr(engine, '_fetch_google_transit_matrix_raw', fetch)


def _rounded(p):
    return (engine._round_coord(p[0]), engine._round_coord(p[1]))


def _ask(dest, departure):
    return engine.get_google_travel_time(*A, *dest, '大眾運輸', departure_time=departure)


def test_second_run_uses_disk_and_never_calls_google(monkeypatch):
    calls = []
    _fake_google(monkeypatch, calls, {_rounded(B): 21.0, _rounded(C): float('inf')})
    monkeypatch.setattr(engine, 'transit_fallback_minutes', lambda *a, **k: None)

    engine.begin_travel_query_run(1000)
    first = (_ask(B, '2026-10-05 09:00'), _ask(C, '2026-10-05 09:00'))
    assert first[0] == 21.0 and math.isinf(first[1])      # 查無路線也要存，否則每次重查
    assert len(calls) == 2

    # 模擬重開 app：記憶體 memo 清空，但硬碟還在；換成同星期幾、同時刻的另一天也要命中
    engine.begin_travel_query_run(1000)
    calls.clear()
    second = (_ask(B, '2026-10-12 09:00'), _ask(C, '2026-10-12 09:00'))
    assert second[0] == first[0] and math.isinf(second[1])
    assert calls == []
    assert engine.google_query_summary() == {'queried': 0, 'disk_hits': 2}


def test_different_weekday_or_time_is_a_separate_entry(monkeypatch):
    calls = []
    _fake_google(monkeypatch, calls, {_rounded(B): 30.0})
    engine.begin_travel_query_run(1000)
    _ask(B, '2026-10-05 09:00')                 # 星期一 09:00
    engine.begin_travel_query_run(1000)
    _ask(B, '2026-10-06 09:00')                 # 星期二：不能沿用星期一
    _ask(B, '2026-10-12 10:00')                 # 星期一但時刻不同
    assert len(calls) == 3


def test_disk_key_has_no_date():
    key = engine._google_transit_key(*A, *B, departure='2026-10-05T09:00:00+08:00', arrival=None)
    disk = engine._transit_disk_key(key)
    assert disk[-3:] == ('dep', 1, '09:00')
    assert '2026' not in repr(disk)


def test_expired_transit_entry_is_a_cache_miss(monkeypatch):
    persistent_cache.write_transit({('k',): 12.0})
    assert persistent_cache.read_transit([('k',)]) == {('k',): 12.0}
    monkeypatch.setattr(persistent_cache, '_transit_cutoff', lambda: float('inf'))
    assert persistent_cache.read_transit([('k',)]) == {}
