"""Compare ordinary string token boundaries against CPython, including UTF-8 offsets."""
from pathlib import Path
import io,json,os,platform,subprocess,tempfile,tokenize
ROOT=Path(__file__).resolve().parents[1]
prefixes=['','r','R','u','U','b','B','br','bR','Br','BR','rb','rB','Rb','RB']
quotes=['"',"'",'"""',"'''"]
bodies=['','abc','日本語🪨','\\n','\\\\','\\"',"\\'",'one\ntwo','one\r\ntwo','one\rtwo','one\\\ntwo','one\\\r\ntwo','one\\\rtwo','"',"'",'""',"''",'\\x','\\uZZZZ','{not interpolation}']
cases=[];expected=[]
for prefix in prefixes:
    for quote in quotes:
        for body in bodies:
            literal=prefix+quote+body+quote
            normalized=literal.replace('\r\n','\n').replace('\r','\n')
            stream=tokenize.generate_tokens(io.StringIO(normalized+' + 1').readline)
            try:first=next(stream)
            except (tokenize.TokenError,SyntaxError):continue
            if first.type!=tokenize.STRING:continue
            # Python's tokenizer does not validate ASCII bytes content; the
            # compiler does. This stage deliberately enforces that restriction.
            if 'b' in prefix.lower() and any(ord(c)>127 for c in first.string):continue
            # CPython reads universal newlines. Map its character boundary back to
            # original bytes so CRLF and non-ASCII source positions stay exact.
            end=0
            for _ in first.string:
                end+=2 if literal[end:end+2]=='\r\n' else 1
            expected_end=len(literal[:end].encode())
            for offset in ['', '🪨 ']:
                cases.append({'source':offset+literal+' + 1','start':len(offset.encode())})
                expected.append(len(offset.encode())+expected_end)
valid=len(cases)
invalid=['"unterminated',"'unterminated",'"""unterminated',"'''unterminated",'r"trailing\\"','"raw\nnewline"','"raw\rnewline"','b"日本語"','br"🪨"','b"\\🪨"','"null\x00byte"','r"\\\x00"']
for source in invalid:
    try:compile(source,'fixture','eval')
    except SyntaxError:pass
    else:raise AssertionError(('CPython accepted invalid fixture',source))
    cases.append({'source':source,'start':0});expected.append(None)
with tempfile.TemporaryDirectory() as tmp:
    binary=Path(tmp)/'probe';data=Path(tmp)/'cases.json'
    subprocess.run([os.environ.get('ALMIDE_BIN','almide'),'build','ci/python_strings_probe.almd','-o',str(binary)],cwd=ROOT,check=True)
    data.write_text(json.dumps({'cases':cases},ensure_ascii=False))
    result=json.loads(subprocess.check_output([str(binary),str(data)],text=True))
    assert len(result)==len(expected)
    for case,want,actual in zip(cases,expected,result):
        assert actual['ok']==(want is not None),(case,want,actual)
        if want is not None:assert actual['end']==want,(case,want,actual)
print(f'CPython {platform.python_version()}: {valid} ordinary string boundaries and {len(invalid)} rejected strings match')
