import re,sys,pathlib
H=lambda names: re.compile(r'^\s*(?:(?:\d+(?:\.\d+)*|[A-H](?:\.\d+)*)\s*)?(?:'+names+r')\b[^\n]{0,40}$',re.I)
pats={
 'abstract':H('Abstract|ABSTRACT'),
 'intro':H('Introduction|INTRODUCTION'),
 'related':H('Related Work|RELATED WORK|Background|Preliminaries'),
 'method':H('Method|Methods|Methodology|Approach|Framework|Benchmark Construction|BENCHMARK CONSTRUCTION|Benchmark Design|BENCHMARK DESIGN|Dataset Construction|Problem Formulation|Preliminaries'),
 'exp':H('Experiments|EXPERIMENTS|Experimental Setup|EXPERIMENTAL SETUP|Experiment Setup|Evaluation|EVALUATION|Setup'),
 'results':H('Results|Main Results|MAIN RESULTS|RESULTS'),
 'limit':H('Limitations?|LIMITATIONS|Discussion and Limitations|DISCUSSION AND LIMITATIONS|Limitations and Conclusion|Conclusion and Limitations|Conclusion and Future Work|Limitations and future directions'),
 'concl':H('Conclusions?|CONCLUSIONS?'),
}
def first(lines,pat,start=0,stop=None):
    stop=stop or len(lines)
    for i in range(start,stop):
        l=lines[i].strip()
        if len(l)<60 and pat.match(l): return i
    return None
def win(lines,i,n): return '\n'.join(f'{i+k+1}:{lines[i+k]}' for k in range(n) if i+k<len(lines))
for f in sys.argv[1:]:
    L=pathlib.Path(f).read_text(encoding='utf-8',errors='replace').replace('\x00','').splitlines()
    out=[f'##### {f}  ({len(L)} lines)']
    a=first(L,pats['abstract']) or 0
    out.append('--ABSTRACT--\n'+win(L,a,34))
    it=first(L,pats['intro'],a+1)
    nxt=first(L,pats['related'],(it or 0)+5) or first(L,pats['method'],(it or 0)+5)
    if it is not None and nxt:
        s=max(it,nxt-28); out.append('--INTRO END--\n'+win(L,s,28))
    m=first(L,pats['method'],(it or 0)+5, int(len(L)*0.6))
    if m is not None: out.append('--METHOD--\n'+win(L,m,40))
    e=first(L,pats['exp'],(m or it or 0)+5, int(len(L)*0.75))
    if e is not None: out.append('--EXP SETUP--\n'+win(L,e,50))
    r=first(L,pats['results'],(e or 0)+3, int(len(L)*0.8))
    if r is not None: out.append('--RESULTS--\n'+win(L,r,30))
    li=first(L,pats['limit'],int(len(L)*0.2))
    if li is not None: out.append('--LIMITATIONS--\n'+win(L,li,24))
    c=first(L,pats['concl'],int(len(L)*0.2))
    if c is not None and (li is None or abs(c-li)>20): out.append('--CONCLUSION--\n'+win(L,c,16))
    print('\n'.join(out)); print()
