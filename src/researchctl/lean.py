from __future__ import annotations
from pathlib import Path
import re, subprocess, tempfile
from .model import sha256_text

DECL_RE = re.compile(r"^\s*(?:private\s+|protected\s+)?(?:theorem|lemma|def|abbrev)\s+([A-Za-z0-9_'.]+)\b")
FORBIDDEN = re.compile(r"\b(sorry|admit)\b")

def strip_comments_and_strings(src: str) -> str:
    out=[]; i=0; block=0; line=False; string=False; esc=False
    while i < len(src):
        c=src[i]; n=src[i+1] if i+1<len(src) else ""
        if line:
            if c=='\n': line=False; out.append(c)
            else: out.append(' ')
            i+=1; continue
        if block:
            if c=='/' and n=='-': block+=1; out.extend('  '); i+=2; continue
            if c=='-' and n=='/': block-=1; out.extend('  '); i+=2; continue
            out.append('\n' if c=='\n' else ' '); i+=1; continue
        if string:
            out.append(' ' if c!='\n' else '\n')
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': string=False
            i+=1; continue
        if c=='-' and n=='-': line=True; out.extend('  '); i+=2; continue
        if c=='/' and n=='-': block=1; out.extend('  '); i+=2; continue
        if c=='"': string=True; out.append(' '); i+=1; continue
        out.append(c); i+=1
    return ''.join(out)

def find_placeholders(path: Path) -> list[tuple[int,str]]:
    clean=strip_comments_and_strings(path.read_text(encoding='utf-8'))
    found=[]
    for i,line in enumerate(clean.splitlines(),1):
        for m in FORBIDDEN.finditer(line): found.append((i,m.group(1)))
    return found

def extract_declaration_header(path: Path, declaration: str) -> str:
    src=path.read_text(encoding='utf-8')
    lines=src.splitlines()
    start=None
    pat=re.compile(rf"^\s*(?:private\s+|protected\s+)?(?:theorem|lemma|def|abbrev)\s+{re.escape(declaration.split('.')[-1])}\b")
    for idx,line in enumerate(lines):
        if pat.search(line): start=idx; break
    if start is None: raise ValueError(f"declaration {declaration!r} not found in {path}")
    buf=[]; depth=0
    for line in lines[start:]:
        buf.append(line.rstrip())
        # Statement terminates at := or := by / where body starts; bare `by` can start theorem proof.
        clean=strip_comments_and_strings(line)
        depth += clean.count('(')+clean.count('[')+clean.count('{')-clean.count(')')-clean.count(']')-clean.count('}')
        if depth <= 0 and (':=' in clean or re.search(r"\bby\s*$", clean)):
            # remove proof/body marker from final line
            joined='\n'.join(buf)
            joined=re.split(r"\s*:=\s*(?:by\b)?", joined, maxsplit=1)[0]
            joined=re.sub(r"\s+by\s*$", "", joined)
            return '\n'.join(x.rstrip() for x in joined.splitlines()).strip()
    return '\n'.join(buf).strip()

def statement_hash(path: Path, declaration: str) -> tuple[str,str]:
    text=extract_declaration_header(path,declaration)
    return sha256_text(text), text

def run_lake(root: Path) -> tuple[int,str]:
    p=subprocess.run(["lake","build"],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return p.returncode,p.stdout

def print_axioms(root: Path, module: str, declaration: str) -> tuple[int,str]:
    content=f"import {module}\n#print axioms {declaration}\n#check {declaration}\n"
    with tempfile.NamedTemporaryFile('w',suffix='.lean',dir=root,delete=False,encoding='utf-8') as f:
        f.write(content); tmp=Path(f.name)
    try:
        p=subprocess.run(["lake","env","lean",str(tmp.name)],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        return p.returncode,p.stdout
    finally:
        tmp.unlink(missing_ok=True)
