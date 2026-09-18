import importlib.util
import sys
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / 'scripts' / 'update_airwindows.py'
spec = importlib.util.spec_from_file_location('aw', MOD)
aw = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = aw
spec.loader.exec_module(aw)

SAMPLE = '''<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>VerbThing</title><link>https://example.com/v</link><guid>v1</guid><pubDate>Fri, 18 Sep 2026 00:00:00 +0000</pubDate><category>Reverb</category><content:encoded><![CDATA[<p>A new room reverb with deep space.</p>]]></content:encoded></item>
</channel></rss>'''

def test_parse_feed():
    x=aw.parse_feed(SAMPLE)[0]
    assert x.title == 'VerbThing'
    assert 'リバーブ' in x.summary_ja
    assert x.categories == ['Reverb']

def test_airwindopedia_categories():
    txt='''# Categories\nReverb: Verbity, Galactic\nBass: SubTight\n############ Verbity is a reverb for spaces.\nLong explanation.\n############ SubTight is for low bass.\nMore.\n'''
    items=aw.parse_airwindopedia(txt)
    by={x['name']:x for x in items}
    assert 'Verbity' in by
    assert by['Verbity']['categories']==['Reverb']
    assert 'SubTight' in by
