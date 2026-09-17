"""EOF recovery keeps the unmatched delimiter's logical line opaque."""
from pathlib import Path
import ast,json,re,subprocess,tempfile
BIN=Path(__file__).resolve().parents[1]/'gramide_python'
count=0

def run(command,path):
 return subprocess.run([str(BIN),command,str(path)],capture_output=True,text=True,timeout=10)

with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'editing.py'
 def case(source,names,owns_tail=True):
  global count
  try:ast.parse(source)
  except SyntaxError:pass
  else:raise AssertionError(source)
  path.write_bytes(source.encode())
  result=run('symbols-recovered',path)
  assert result.returncode==0,(source,result)
  doc=json.loads(result.stdout)
  assert not doc['complete'] and doc['diagnostic'] and doc['errors'],doc
  assert [s['name'] for s in doc['symbols']]==names,(source,doc)
  raw=source.encode()
  # an unclosed bracket owns the tail up to a line that begins a statement at
  # the opener's indentation or less; with none such it runs to the end
  if owns_tail:assert doc['errors'][-1]['end_byte']==len(raw),(source,doc)
  for e in doc['errors']:
   assert 0<=e['start_byte']<e['end_byte']<=len(raw),e
   line=len(re.findall(rb'\r\n|\r|\n',raw[:e['start_byte']]))+1
   endline=len(re.findall(rb'\r\n|\r|\n',raw[:e['end_byte']]))+1-int(raw[:e['end_byte']].endswith((b'\r',b'\n')))
   assert e['start']==line and e['end']==endline,(source,e,line,endline)
  for s in doc['symbols']:
   fragment=raw[s['start_byte']:s['end_byte']]
   assert fragment.startswith(('def '+s['name'].split('.')[-1]+'(').encode()),s
   assert b'\r' not in fragment and b'\n' not in fragment,s
   line=len(re.findall(rb'\r\n|\r|\n',raw[:s['start_byte']]))+1
   assert s['start']==s['end']==line,s
   assert all(s['end_byte']<=e['start_byte'] or s['start_byte']>=e['end_byte'] for e in doc['errors']),doc
  for cmd in ['check','symbols','tokens']:
   result=run(cmd,path)
   assert result.returncode!=0 and not result.stdout,(source,cmd,result)
  for cmd in ['outline','parse']:
   result=run(cmd,path)
   assert result.returncode==0 and '[recovered,' in result.stderr,(source,cmd,result)
   assert 'phantom' not in result.stdout,(source,cmd,result)
  count+=1

 for opening in ['(','[','{']:
  for newline in ['\n','\r\n','\r']:
   for indent,tail in [(None,''),(None,newline),(1,newline+' def NAME(): pass'+newline),(0,newline+'# 日本語'+newline+'def NAME(): pass'+newline)]:
    for prefix,names,opener_indent,owner in [
      ('def before(): pass'+newline+'x = ',['before'],0,''),
      ('class Box:'+newline+' def good(self): pass'+newline+' x = ',['Box.good'],1,'Box.'),
      ('def outer():'+newline+' def good(): pass'+newline+' x = ',['outer.good'],1,'outer.'),
      ('x = ',[],0,''),
    ]:
     # a def at the opener's indentation or less is a statement again — a
     # method or nested function at the opener's own indentation, a top-level
     # function at none; one written deeper is inside the bracket still
     promoted=indent is not None and indent<=opener_indent
     name='after' if promoted else 'phantom'
     listed=names+([(owner if indent==opener_indent and indent>0 else '')+name] if promoted else [])
     case(prefix+opening+tail.replace('NAME',name),listed,owns_tail=not promoted)
 for source in [
  'def before(): return [1]\nx = (\n def phantom(): pass\n',
  'def before(): pass\ndef damaged(\n def phantom(): pass\n',
  'def before(): pass\nclass Damaged(\n def phantom(): pass\n',
  'def before(): pass\nx = ([{}]\n def phantom(): pass\n',
  'def before(): pass\nx = (\n \\\n',
  'def before(): pass\nx = [t"{value\ndef phantom(): pass\n',
  'def before(): pass\nx = {"""bad\ndef phantom(): pass\n',
  'def before(): pass\nx = (\n'+''.join(f' def phantom{i}(): pass\n' for i in range(2000)),
 ]:case(source,['before'])
 # a string that fails inside the bracket costs its line; the `def` at the opener's indentation is a declaration
 for source in ['def before(): pass\nx = ("bad\ndef after(): pass\n','def before(): pass\nx = (f"bad\ndef after(): pass\n']:
  case(source,['before','after'],owns_tail=False)
 # Explicit edits are full reparses, not an incremental benchmark. The same
 # suffix is visible either way: open, the `def` at the opener's indentation ends the expression.
 for opening,closing in [('(',')'),('[',']'),('{','}')]:
  for close in ['',closing,'',closing]:
   source='def before(): pass\nx = '+opening+'1\n'+close+'\ndef after(): pass\n'
   if not close:case(source,['before','after'],owns_tail=False)
   else:
    ast.parse(source)
    path.write_text(source)
    strict=json.loads(subprocess.check_output([str(BIN),'symbols',str(path)]))
    recovered=json.loads(subprocess.check_output([str(BIN),'symbols-recovered',str(path)]))
    assert recovered['complete'] and recovered['symbols']==strict['symbols'],recovered
    assert [s['name'] for s in recovered['symbols']]==['before','after'],recovered
 # A mismatched closer recovers (an error token, the bracket open to the end); invalid indentation remains a failure even in recovery.
 path.write_text('x = (]\n')
 result=run('symbols-recovered',path)
 assert result.returncode==0 and not json.loads(result.stdout)['complete'],result
 for source in ['if True:\n  x = 1\n y = (\n']:
  path.write_text(source)
  result=run('symbols-recovered',path)
  assert result.returncode!=0 and not result.stdout,(source,result)
print(f'Python delimiter recovery: {count} invalid cases, exact ranges, containment, 2000 apparent declarations and repair cycles passed')
