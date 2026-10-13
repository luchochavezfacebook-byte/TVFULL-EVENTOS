#!/usr/bin/env python3
"""Valida el JSON publicado y comprueba que no incluya URLs IPTV."""
import json
import pathlib
import re
import sys
from actualizar_agenda import validate_event

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    file=ROOT/'eventos.json'
    raw=file.read_bytes()
    if len(raw)>128*1024:
        raise ValueError('eventos.json supera 128 KiB')
    data=json.loads(raw)
    if set(data) != {'version','timezone','events'} or data['version']!=1 or data['timezone']!='America/Argentina/Buenos_Aires':
        raise ValueError('Cabecera incompatible con TV FULL PRO')
    events=data['events']
    if not isinstance(events,list) or len(events)>120:
        raise ValueError('Se admiten como máximo 120 eventos programados')
    ids=set()
    for item in events:
        if not isinstance(item,dict) or not validate_event(item,ROOT):
            raise ValueError('Evento inválido: '+str(item)[:160])
        if item['id'] in ids:
            raise ValueError('Evento duplicado')
        ids.add(item['id'])
        image=ROOT/item['image']
        if image.stat().st_size>400*1024:
            raise ValueError('Imagen superior a 400 KiB: '+str(image))
        if any(re.search(r'(?:https?://|user(?:name)?|password|stream|\.m3u8|\.mpd|\bdrm\b)',str(e),re.I) for e in item.values()):
            raise ValueError('Dato privado/URL IPTV en manifest')
    print('OK: JSON compatible, '+str(len(events))+' eventos, 0 enlaces IPTV')
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,TypeError,ValueError) as ex:
        print('ERROR:',ex,file=sys.stderr);raise SystemExit(1)
