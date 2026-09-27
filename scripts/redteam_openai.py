#!/usr/bin/env python3
"""Trusted-side red-team caller. Reads prompt as DATA; never executes PR code."""
from pathlib import Path
import json, os, sys, urllib.request

prompt_path=Path(sys.argv[1])
out_path=Path(sys.argv[2])
key=os.environ.get('OPENAI_API_KEY')
if not key: raise SystemExit('OPENAI_API_KEY is not set')
model=os.environ.get('MATH_CICD_REDTEAM_MODEL','gpt-5')
if prompt_path.stat().st_size > 200_000: raise SystemExit('red-team prompt exceeds 200 KB limit')
prompt=prompt_path.read_text(encoding='utf-8')
payload={"model":model,"input":prompt,"store":False}
req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=180) as r: data=json.loads(r.read())
text=data.get('output_text','')
if not text:
    chunks=[]
    for item in data.get('output',[]):
        for c in item.get('content',[]):
            if c.get('type')=='output_text': chunks.append(c.get('text',''))
    text='\n'.join(chunks)
out_path.parent.mkdir(parents=True,exist_ok=True)
out_path.write_text(text or json.dumps(data,indent=2),encoding='utf-8')
