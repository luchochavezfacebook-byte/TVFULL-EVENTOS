import datetime as dt
import importlib.util
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'scripts'))
from actualizar_agenda import channels, parse_html, merged_events, fixture_key

EXAMPLE='''<html><body>
<h1>Agenda deportiva</h1>
<h2>Agenda Deportiva del lunes 12 de octubre de 2026</h2>
<h2>Martes 13 de octubre de 2026</h2>
<h2>Copa Sudamericana</h2>
<h3>Boca Juniors</h3><div>21:30</div><span>ESPN Disney + Premium DSports</span>
<h3>Vasco da Gama</h3><p>Más datos</p>
<h2>Champions League</h2>
<h3>Inter</h3><div>16:00</div><h3>Brujas</h3><span>ESPN 2 Disney + Premium DGO</span><p>Más datos</p>
<h3>Arsenal</h3><div>16:00</div><h3>Lille</h3><p>Disney + Premium</p>
<h2>Miércoles 14 de octubre de 2026</h2>
<h2>Liga Profesional</h2>
<h3>Sarmiento</h3><div>19:00</div><h3>River Plate</h3><span>TNT Sports Premium</span><p>Más datos</p>
</body></html>'''

class Tests(unittest.TestCase):
 def setUp(self):self.now=dt.datetime(2026,10,13,10,tzinfo=ZoneInfo('America/Argentina/Buenos_Aires'))
 def test_streaming_only_excluded(self):
  self.assertEqual(channels('Disney + Premium DGO LPF PLAY'), [])
  self.assertEqual(channels('ESPN 2 Disney + Premium'), ['ESPN 2'])
  self.assertEqual(channels('TNT Sports Premium'), ['TNT Sports Premium'])
 def test_parse_fixture(self):
  games=parse_html(EXAMPLE,self.now)
  self.assertEqual(len(games),3,games)
  self.assertEqual(games[0]['title'],'Inter vs Brujas')
  self.assertEqual(games[1]['title'],'Boca Juniors vs Vasco da Gama')
  self.assertEqual(games[1]['channel_names'],['ESPN','DSports'])
  self.assertEqual(games[2]['channel_names'],['TNT Sports Premium'])
  self.assertTrue(all('stream' not in str(game).casefold() for game in games))
 def test_manual_override(self):
  games=parse_html(EXAMPLE,self.now)
  manual={'id':'boca-vasco-20261013','title':'Boca Juniors vs Vasco da Gama · Copa Sudamericana',
    'image':'imagenes/boca-vasco-20261013.webp',
    'starts_at':'2026-10-13T21:30:00-03:00','show_from':'2026-10-13T09:00:00-03:00',
    'show_until':'2026-10-14T02:00:00-03:00','channel_names':['SPEN','ESPN','ESPN HD']}
  merged=merged_events([manual],games,ROOT,self.now)
  matches=[e for e in merged if 'Boca' in e['title']]
  self.assertEqual(len(matches),1)
  self.assertEqual(matches[0]['channel_names'][0],'SPEN')
 def test_no_unconfirmed_match(self):
  fixture='''<h2>Martes 13 de octubre de 2026</h2><h3>Uno</h3><b>18:00</b><h3>Dos</h3><p>Disney + Premium</p>'''
  self.assertEqual(parse_html(fixture,self.now),[])
 def test_actual_ole_split_date_markup(self):
  html='''<h1>Agenda Deportiva</h1>
  <p>Martes</p><p>13</p><p>de</p><p>octubre</p><p>de</p><p>2026</p>
  <h2>Copa Sudamericana</h2><h3>Boca Juniors</h3>
  <p>21:30</p><p>ESPN</p><p>Disney + Premium</p><p>DSports</p>
  <h3>Vasco da Gama</h3><p>Más datos</p>
  <p>Miércoles</p><p>14</p><p>de</p><p>octubre</p><p>de</p><p>2026</p>
  <h2>Liga Profesional</h2><h3>Sarmiento</h3><p>19:00</p>
  <h3>River Plate</h3><p>Formaciones y más datos</p><p>TNT Sports Premium</p>'''
  games=parse_html(html,self.now)
  self.assertEqual(len(games),2,games)
  self.assertEqual(games[0]['title'],'Boca Juniors vs Vasco da Gama')
  self.assertEqual(games[1]['title'],'Sarmiento vs River Plate')
  self.assertEqual(games[1]['channel_names'],['TNT Sports Premium'])
 def test_dedupe_and_valid_window(self):
  self.assertNotEqual(fixture_key('Boca vs Vasco · Copa','2026-10-13T21:30:00-03:00'),fixture_key('Boca vs River','2026-10-13T21:30:00-03:00'))

if __name__=='__main__':unittest.main()
