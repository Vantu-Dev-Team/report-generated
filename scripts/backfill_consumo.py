#!/usr/bin/env python3
"""
Backfill consumo_dia, consumo_semana, consumo_mes from raw ch1 hourly data.

- consumo_dia   : sum(ch1) por día local (UTC-5), publicado a las 12:00 local del mismo día
- consumo_semana: sum(consumo_dia) por semana sáb→vie, publicado a las 12:00 local del sábado
- consumo_mes   : sum(consumo_dia) del mes, publicado a las 12:00 local del 1° del mes siguiente

Ignorar valores negativos de ch1 (anomalías de sensor).
Solo postea fechas que faltan — no duplica datos existentes.
"""

import json
import os
import datetime
import urllib.request
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────────────

TZ_H = -5  # UTC-5

DEVICES = [
    "borsea-240ac4c79d94",  # Inhisalm
    "borsea-a4cf1281b49c",  # Adinox
]

def load_token():
    env = os.path.join(os.path.dirname(__file__), '..', '.env')
    for line in open(env):
        if line.startswith('UBIDOTS_TOKEN'):
            return line.split('=', 1)[1].strip()
    raise ValueError('UBIDOTS_TOKEN not found in .env')

TOKEN = os.environ.get('UBIDOTS_TOKEN') or load_token()
BASE  = 'https://industrial.api.ubidots.com'

# ── Ubidots helpers ──────────────────────────────────────────────────────────

def get_all_values(device, variable, start_ms=None, end_ms=None):
    params = '?page_size=2000'
    if start_ms: params += f'&start={start_ms}'
    if end_ms:   params += f'&end={end_ms}'
    url = f'{BASE}/api/v1.6/devices/{device}/{variable}/values/{params}'
    results = []
    while url:
        req = urllib.request.Request(url, headers={'X-Auth-Token': TOKEN})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        results.extend(data.get('results', []))
        url = data.get('next')
    return results

def post_values(device, variable, values):
    """values: list of {'value': float, 'timestamp': int_ms}"""
    if not values:
        return
    url  = f'{BASE}/api/v1.6/devices/{device}/{variable}/values/'
    body = json.dumps(values).encode()
    req  = urllib.request.Request(url, data=body, method='POST', headers={
        'X-Auth-Token': TOKEN,
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# ── Time helpers ─────────────────────────────────────────────────────────────

def utc_ms_to_local(ts_ms):
    return datetime.datetime.utcfromtimestamp(ts_ms / 1000 + TZ_H * 3600)

def local_noon_ms(d):
    """12:00 local of date d → UTC milliseconds"""
    noon_utc = datetime.datetime(d.year, d.month, d.day, 12 - TZ_H, 0, 0)
    return int(noon_utc.timestamp() * 1000)

def week_start_saturday(d):
    """Returns the Saturday on or before date d."""
    return d - datetime.timedelta(days=(d.weekday() - 5) % 7)

# ── Main logic ───────────────────────────────────────────────────────────────

def process(device):
    print(f'\n{"=" * 55}')
    print(f'  {device}')
    print(f'{"=" * 55}')

    now_local = datetime.datetime.utcnow() + datetime.timedelta(hours=TZ_H)
    today     = now_local.date()
    yesterday = today - datetime.timedelta(days=1)

    # ── 1. consumo_dia ───────────────────────────────────────────────────────

    print('\n[consumo_dia]')
    existing_dia = get_all_values(device, 'consumo_dia')
    dia_dates    = {utc_ms_to_local(r['timestamp']).date() for r in existing_dia}
    all_dia      = {utc_ms_to_local(r['timestamp']).date(): r['value'] for r in existing_dia}

    last_dia = max(dia_dates) if dia_dates else yesterday - datetime.timedelta(days=30)
    print(f'  Último consumo_dia: {last_dia}')

    # Fetch ch1 desde el día siguiente al último conocido
    fetch_from_local = datetime.datetime(last_dia.year, last_dia.month, last_dia.day)
    start_ms = int((fetch_from_local - datetime.timedelta(hours=TZ_H)).timestamp() * 1000)
    end_ms   = int((datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
                    - datetime.timedelta(hours=TZ_H)).timestamp() * 1000)

    print(f'  Descargando ch1 desde {last_dia} hasta {yesterday}...')
    ch1_raw = get_all_values(device, 'ch1', start_ms=start_ms, end_ms=end_ms)
    print(f'  {len(ch1_raw)} puntos horarios encontrados')

    # Agrupar por día local, ignorar negativos
    daily_ch1 = defaultdict(float)
    for r in ch1_raw:
        d   = utc_ms_to_local(r['timestamp']).date()
        val = r['value']
        if val > 0:
            daily_ch1[d] += val

    # Publicar días faltantes (desde el día siguiente al último hasta ayer)
    new_dia = []
    d = last_dia + datetime.timedelta(days=1)
    while d <= yesterday:
        if d not in dia_dates:
            val = round(daily_ch1.get(d, 0.0), 2)
            new_dia.append({'value': val, 'timestamp': local_noon_ms(d)})
            all_dia[d] = val
            print(f'  {d}  →  {val:.2f} Kg')
        d += datetime.timedelta(days=1)

    if new_dia:
        print(f'  Publicando {len(new_dia)} valores...')
        post_values(device, 'consumo_dia', new_dia)
        print('  OK')
    else:
        print('  Nada nuevo que publicar')

    # ── 2. consumo_semana ────────────────────────────────────────────────────

    print('\n[consumo_semana]')
    existing_sem  = get_all_values(device, 'consumo_semana')
    sem_sat_dates = {utc_ms_to_local(r['timestamp']).date() for r in existing_sem}

    # Sumar consumo_dia por semana (sáb → vie)
    weekly = defaultdict(float)
    for d, val in all_dia.items():
        sat = week_start_saturday(d)
        weekly[sat] += val

    new_sem = []
    for sat in sorted(weekly):
        if sat in sem_sat_dates:
            continue
        fri = sat + datetime.timedelta(days=6)
        if fri > yesterday:          # semana incompleta
            continue
        val = round(weekly[sat], 2)
        new_sem.append({'value': val, 'timestamp': local_noon_ms(sat)})
        print(f'  {sat} → {fri}  =  {val:.2f} Kg')

    if new_sem:
        print(f'  Publicando {len(new_sem)} valores...')
        post_values(device, 'consumo_semana', new_sem)
        print('  OK')
    else:
        print('  Nada nuevo que publicar')

    # ── 3. consumo_mes ───────────────────────────────────────────────────────

    print('\n[consumo_mes]')
    existing_mes = get_all_values(device, 'consumo_mes')

    # El timestamp del mes está en el 1° del mes SIGUIENTE al que cubre
    covered_months = set()
    for r in existing_mes:
        d = utc_ms_to_local(r['timestamp']).date()  # 1° del mes siguiente
        covered = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
        covered_months.add(covered)

    # Sumar consumo_dia por mes
    monthly = defaultdict(float)
    for d, val in all_dia.items():
        monthly[(d.year, d.month)] += val

    new_mes = []
    for (yr, mo) in sorted(monthly):
        if (yr, mo) in covered_months:
            continue
        if (yr, mo) >= (today.year, today.month):   # mes en curso, aún no completo
            continue
        val       = round(monthly[(yr, mo)], 2)
        next_mo   = datetime.date(yr + (mo == 12), 1 if mo == 12 else mo + 1, 1)
        new_mes.append({'value': val, 'timestamp': local_noon_ms(next_mo)})
        print(f'  {yr}-{mo:02d}  =  {val:.2f} Kg  (publicado en {next_mo})')

    if new_mes:
        print(f'  Publicando {len(new_mes)} valores...')
        post_values(device, 'consumo_mes', new_mes)
        print('  OK')
    else:
        print('  Nada nuevo que publicar')


if __name__ == '__main__':
    print('=== Backfill consumo_dia / semana / mes ===')
    print(f'Fecha local hoy: {(datetime.datetime.utcnow() + datetime.timedelta(hours=TZ_H)).date()}')
    for device in DEVICES:
        process(device)
    print('\n=== Listo ===')
