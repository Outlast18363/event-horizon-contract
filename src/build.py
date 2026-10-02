import os
d=os.path.dirname(os.path.abspath(__file__))
t=open(os.path.join(d,'template.html')).read()
cm=open(os.path.join(d,'cm.css')).read()
h=open(os.path.join(d,'harness.py')).read()
assert '</script' not in h
t=t.replace('/*CM_CSS*/',cm).replace('#HARNESS#',h)
open(os.path.join(d,'..','page-body.html'),'w').write(t)
open(os.path.join(d,'..','index.html'),'w').write('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><style>[hidden]{display:none!important}</style></head><body>'+t+'</body></html>')
print(len(t))
