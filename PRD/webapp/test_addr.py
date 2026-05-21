import requests
import time

tests = [
    ('68 BINGARA RD',       'original failing case'),
    ('178A George Sydney',  'suffix test'),
    ('591 George Sydney',   'non-contiguous tokens'),
    ('Unit 214 George',     'unit+number+street'),
]

for q, label in tests:
    t0 = time.time()
    r = requests.get('http://localhost:5000/api/autocomplete/full-address', params={'q': q})
    elapsed = (time.time() - t0) * 1000
    data = r.json()
    print(f'[{label}] {elapsed:.0f}ms -> {len(data)} results')
    for a in data[:4]:
        print('  ' + a['full_address'])
    print()
