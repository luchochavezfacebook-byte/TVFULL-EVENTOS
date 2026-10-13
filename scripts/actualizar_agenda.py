#!/usr/bin/env python3
"""Actualiza UN manifiesto público TV FULL PRO con eventos de agenda Olé.

No contiene enlaces IPTV, no descarga imágenes editoriales, no compila APK.
La estructura web externa puede cambiar: fallo seguro y conservador.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TIMEZONE = ZoneInfo('America/Argentina/Buenos_Aires')
AGENDA_URLS = (
    'https://www.ole.com.ar/agenda-deportiva',
    'https://movil.ole.com.ar/agenda-deportiva',
    'https://buscador.ole.com.ar/agenda-deportiva',
)
MESES = dict(zip(
    ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
     'septiembre', 'setiembre', 'octubre', 'noviembre', 'diciembre'],
    [1,2,3,4,5,6,7,8,9,9,10,11,12],
))
DATE_RE = re.compile(r'(?i)(?:agenda\s+deportiva\s+del\s+)?'
                     r'(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)'
                     r'\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(20\d{2})')
TIME_RE = re.compile(r'^(\d{1,2}):(\d{2})$')
LABELS = {'formaciones y mas datos','formaciones y más datos','mas datos','más datos',
          'impecable','imperdible','agenda deportiva','deporte','competicion','competición',
          'horario','dia','día','x','resultados','noticias'}
CHANNEL_PATTERNS = [
  ('TNT Sports Premium', r'\bTNT\s+Sports\s+Premium\b'),
  ('TNT Sports', r'\bTNT\s+Sports\b'),
  ('TyC Sports', r'\bTyC\s+Sports\b'),
  ('ESPN Premium', r'\bESPN\s+Premium\b'),
  ('ESPN 4', r'\bESPN\s*4\b'),
  ('ESPN 3', r'\bESPN\s*3\b'),
  ('ESPN 2', r'\bESPN\s*2\b'),
  ('ESPN', r'\bESPN\b(?!\s*(?:Premium|[234]))'),
  ('DSports 2', r'\bDSports\s*2\b'),
  ('DSports', r'\bDSports\b(?!\s*2)'),
  ('Fox Sports 2', r'\bFox\s+Sports\s*2\b'),
  ('Fox Sports', r'\bFox\s+Sports\b(?!\s*2)'),
  ('TV Pública', r'\bTV\s+P[uú]blica\b'),
  ('Telefe', r'\bTelefe\b'),
  ('Canal 9', r'\b(?:El\s+Nueve|Canal\s*9)\b'),
  ('América TV', r'\bAm[eé]rica\s*TV\b'),
  ('Canal 13', r'\b(?:El\s+Trece|Canal\s*13)\b'),
]
SORTED_PATTERNS = [(name, re.compile(pattern, re.I)) for name, pattern in CHANNEL_PATTERNS]
# No se incluyen apps que no son señales lineales (Disney+, DGO, LPF Play).


def nrm(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c))


def channels(text: str) -> list[str]:
    """Extrae señales de TV; ESPN no es sinónimo de ESPN Premium."""
    result: list[str] = []
    for name, pattern in SORTED_PATTERNS:
        if pattern.search(text):
            if name == 'TNT Sports' and 'TNT Sports Premium' in result:
                continue
            if name == 'DSports' and 'DSports 2' in result and not re.search(r'\bDSports\b(?!\s*2)', text, re.I):
                continue
            if name == 'Fox Sports' and 'Fox Sports 2' in result and not re.search(r'\bFox\s+Sports\b(?!\s*2)', text, re.I):
                continue
            result.append(name)
    return result[:5]


def _day(line: str) -> dt.date | None:
    m = DATE_RE.search(line)
    if not m:
        return None
    month = MESES.get(nrm(m.group(2)))
    if not month:
        return None
    try:
        return dt.date(int(m.group(3)), month, int(m.group(1)))
    except ValueError:
        return None


def _team(s: str) -> bool:
    t = nrm(s).strip()
    return (2 <= len(t) <= 55 and t not in LABELS and not _day(t)
            and not TIME_RE.match(t) and not channels(t)
            and not re.search(r'^\d+\s*(?:hs|h)$', t)
            and not re.search(r'\b(?:disney|premium|dgo|lpf play|paramount|apple tv|star\+)\b', t)
            and not re.search(r'\b(?:minuto|hoy|ayer|mañana|agenda deportiva|partidos de)\b', t))


def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+','-', nrm(s)).strip('-')[:62]


def fixture_key(title: str, starts_at: str) -> str:
    # Truncar la competencia agregada manualmente después de «·».
    return starts_at[:10] + ':' + slug(title.split('·')[0].strip())


def _candidate(tokens: list[str], pos: int, day: dt.date,
               now: dt.datetime) -> dict | None:
    tm = TIME_RE.fullmatch(tokens[pos]); assert tm
    hour, minute = int(tm.group(1)), int(tm.group(2))
    if hour > 23 or minute > 59: return None
    start = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=TIMEZONE)
    if start < now - dt.timedelta(hours=6) or start > now + dt.timedelta(days=8):
        return None
    previous = [t for t in tokens[max(0,pos-4):pos] if _team(t)]
    if not previous: return None
    team1 = previous[-1]
    lookahead=[]
    after_detail=False
    for token in tokens[pos+1:pos+18]:
        if _day(token) or TIME_RE.fullmatch(token):
            break
        if nrm(token) in {'mas datos', 'formaciones y mas datos'}:
            after_detail=True
            continue
        if after_detail:
            # Olé a veces coloca el canal después de «Más datos».
            if channels(token):lookahead.append(token)
            break
        lookahead.append(token)
    team2 = next((t for t in lookahead if _team(t)), None)
    if not team2 or team1 == team2: return None
    media = ' '.join(lookahead)
    names = channels(media)
    if not names: return None
    title = f'{team1} vs {team2}'
    show_from = start - dt.timedelta(hours=8)
    show_until = start + dt.timedelta(hours=3,minutes=30)
    return {
      'id': f'agenda-{day.isoformat()}-{slug(team1)}-{slug(team2)}'[:80],
      'title': title[:90],
      'image': 'imagenes/agenda.webp',
      'starts_at': start.isoformat(timespec='seconds'),
      'show_from': show_from.isoformat(timespec='seconds'),
      'show_until': show_until.isoformat(timespec='seconds'),
      'channel_names': names,
    }


def parse_html(html: str, now: dt.datetime | None = None) -> list[dict]:
    """Analiza texto semántico de la agenda. Carga solo partidos inequívocos."""
    now = (now or dt.datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    soup = BeautifulSoup(html, 'html.parser')
    for item in soup.select('script,style,nav,footer,header,noscript,iframe'):
        item.decompose()
    text = soup.get_text('\n', strip=True)
    tokens = [t.strip() for t in text.splitlines() if t.strip()]
    # Limitar al contenido de la agenda para no confundir relojes / titulares de publicidad.
    beginning=next((i for i,t in enumerate(tokens)
        if 'agenda deportiva' in nrm(t)),0)
    tokens=tokens[beginning:beginning+1600]
    date: dt.date | None = None
    events: dict[str,dict] = {}
    for i, token in enumerate(tokens):
        initial=nrm(token).split()[0] if token else ''
        if initial in {'lunes','martes','miercoles','jueves','viernes',
                       'sabado','domingo','agenda'}:
            potential=next((_day(' '.join(tokens[i:i+n]))
                for n in range(1,9) if _day(' '.join(tokens[i:i+n]))),None)
            if potential:
                date=potential
                continue
        if date is None or not TIME_RE.fullmatch(token):
            continue
        item = _candidate(tokens, i, date, now)
        if item is None: continue
        key = fixture_key(item['title'], item['starts_at'])
        if key not in events:
            events[key] = item
    return sorted(events.values(), key=lambda e:e['starts_at'])


def download_ole() -> str:
    failures=[]
    for url in AGENDA_URLS:
        try:
            req=urllib.request.Request(url,headers={
              'User-Agent':'TVFULL-Eventos-Agenda/1.0 (+https://github.com/luchochavezfacebook-byte/TVFULL-EVENTOS)',
              'Accept':'text/html,application/xhtml+xml',
            })
            with urllib.request.urlopen(req,timeout=20) as response:
                if response.status != 200: raise ValueError(f'HTTP {response.status}')
                if 'html' not in response.headers.get('Content-Type','').lower():
                    raise ValueError('No es HTML')
                raw=response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError('Tamaño excesivo')
                html=raw.decode('utf-8',errors='replace')
                if 'agenda' not in nrm(html[:100000]):
                    raise ValueError('Página diferente de la agenda')
                games=parse_html(html,dt.datetime.now(TIMEZONE))
                print(f'Fuente {url}: {len(raw)} bytes, {len(games)} partidos TV reconocidos')
                if not games:
                    soup=BeautifulSoup(html,'html.parser')
                    strings=list(soup.stripped_strings)
                    print('Diagnostico: h2=',len(soup.select('h2')),
                          'h3=',len(soup.select('h3')),
                          'fechas=',sum(_day(t) is not None for t in strings),
                          'horas=',sum(TIME_RE.fullmatch(t) is not None for t in strings))
                    for needle in ['Boca Juniors', 'River Plate']:
                        if any(needle in t for t in strings):
                            i=next(i for i,t in enumerate(strings) if needle in t)
                            print('Contexto',needle,[v[:55] for v in strings[max(0,i-3):i+9]])
                    continue
                return html
        except Exception as e:
            failures.append(f'{url}: {type(e).__name__} {str(e)[:120]}')
    raise RuntimeError('No se pudo obtener la agenda Olé: '+'; '.join(failures))


def validate_event(event: dict, root: Path) -> bool:
    required={'id','title','image','starts_at','show_from','show_until','channel_names'}
    if set(event) != required: return False
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,79}', event['id']): return False
    if not isinstance(event['title'],str) or not (1<=len(event['title'])<=90):return False
    if not re.fullmatch(r'imagenes/[a-zA-Z0-9_-]+\.(?:webp|png|jpg|jpeg)',event['image']):return False
    if not (root/event['image']).is_file():return False
    if not isinstance(event['channel_names'],list) or not (1<=len(event['channel_names'])<=5):return False
    if not all(isinstance(n,str) and 3<=len(n)<=70 for n in event['channel_names']):return False
    try:
        for k in ['starts_at','show_from','show_until']:
            if not event[k].endswith('-03:00'):return False
        a,b,c=(dt.datetime.fromisoformat(event[k]) for k in ['starts_at','show_from','show_until'])
        return b<c and c-b <=dt.timedelta(days=7)
    except (KeyError,TypeError,ValueError):return False


def merged_events(manual: list[dict], auto: list[dict], root: Path,
                  now: dt.datetime | None=None) -> list[dict]:
    now=(now or dt.datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    seen:set[str]=set();ids:set[str]=set();out=[]
    for entry in manual+auto:
        if not isinstance(entry,dict) or not validate_event(entry,root):
            raise ValueError(f'Evento inválido: {str(entry)[:160]}')
        # Excluimos eventos terminados; los manuales siguen editables en config/.
        if dt.datetime.fromisoformat(entry['show_until']) < now:
            continue
        key=fixture_key(entry['title'],entry['starts_at'])
        if key in seen or entry['id'] in ids:
            continue
        seen.add(key); ids.add(entry['id']);out.append(entry)
    out.sort(key=lambda e:e['starts_at'])
    return out[:120]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--html-fixture',type=Path)
    parser.add_argument('--now',help='ISO con zona horaria, solo para pruebas')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    root=args.root
    now=dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(TIMEZONE)
    now=now.astimezone(TIMEZONE)
    html=args.html_fixture.read_text(encoding='utf-8') if args.html_fixture else download_ole()
    parsed=parse_html(html,now)
    if not parsed:
        print('ERROR: no se pudieron extraer partidos confirmados con canal lineal. NO sobreescribir JSON.',file=sys.stderr)
        return 1
    config=json.loads((root/'config/manuales.json').read_text(encoding='utf-8'))
    if set(config)!={'events'} or not isinstance(config['events'],list):
        raise ValueError('config/manuales.json inválido')
    final=merged_events(config['events'],parsed,root,now)
    output={'version':1,'timezone':'America/Argentina/Buenos_Aires','events':final}
    raw=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    if len(raw.encode('utf-8'))>128*1024: raise ValueError('JSON excede tamaño aceptado por APK')
    if args.dry_run:
        print(f'Simulacro: {len(parsed)} automáticos, {len(final)} publicados')
    else:
        (root/'eventos.json').write_text(raw,encoding='utf-8')
        print(f'Agenda validada: {len(parsed)} Olé, {len(final)} publicables')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
