"""Maintenance-only, bounded conversion of official legacy resources.

Fresh untrusted profile, macros and link updates disabled, active content
preflight, no shell, hidden process and timeout. This is not an OS sandbox.
The caller receives derived bytes and must keep original/derived provenance
distinct. Neither native legacy upload nor an identity binding is implied.
"""
from io import BytesIO
import hashlib,json,os,re,shutil,subprocess,tempfile,zipfile
from pathlib import Path
from lxml import etree as ET

MAX_BYTES=8*1024*1024

def converter_path():
 for p in [shutil.which('soffice.com'),shutil.which('soffice'),shutil.which('libreoffice'),
           Path(os.environ.get('ProgramFiles',''))/'LibreOffice/program/soffice.com']:
  if p and Path(p).is_file():return Path(p).resolve()
 return None

def preflight(raw,suffix):
 if not raw or len(raw)>MAX_BYTES:raise ValueError('legacy_byte_limit')
 if suffix not in {'.doc','.rtf','.xls','.xlsx','.odt'}:raise ValueError('legacy_format_not_allowed')
 compact=raw.replace(b'\x00',b'').upper()
 if any(token in compact for token in [b'DDEAUTO',b'INCLUDETEXT',b'INCLUDEPICTURE',b'_VBA_PROJECT',b'AUTOOPEN',b'AUTOCLOSE',b'ACTIVEX',b'OLE10NATIVE',b'\\OBJECT',b'\\OBJDATA',b'\\FIELD']):
  raise ValueError('legacy_active_content_rejected')
 if suffix=='.rtf' and not raw.lstrip().startswith(b'{\\rtf'):raise ValueError('legacy_magic_mismatch')
 if suffix in {'.doc','.xls'} and not raw.startswith(b'\xd0\xcf\x11\xe0'):raise ValueError('legacy_magic_mismatch')
 if suffix in {'.xlsx','.odt'}:
  try:
   with zipfile.ZipFile(BytesIO(raw)) as z:
    infos=z.infolist()
    if len(infos)>2000 or sum(i.file_size for i in infos)>40*1024*1024:raise ValueError('legacy_zip_limit')
    for i in infos:
     n=i.filename.lower()
     if i.flag_bits&1 or i.compress_size and i.file_size/i.compress_size>1000:raise ValueError('legacy_zip_limit')
     if ':' in n or '\\' in n or n.startswith('/') or '..' in Path(n).parts or any(t in n for t in ['vbaproject','activex','embeddings/','scripts/','basic/','externallinks/']):raise ValueError('legacy_active_content_rejected')
     if n.endswith(('.xml','.rels')):
      xml=z.read(i)
      if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():raise ValueError('legacy_external_relationship_rejected')
      tree=ET.fromstring(xml,parser=ET.XMLParser(resolve_entities=False,no_network=True,load_dtd=False))
      for e in tree.iter():
       for k,v in e.attrib.items():
        if k.endswith('TargetMode') and v.lower()=='external':raise ValueError('legacy_external_relationship_rejected')
        if k.endswith('href') and (re.match(r'[a-zA-Z]+:',v) or v.startswith('//')):raise ValueError('legacy_external_relationship_rejected')
  except (zipfile.BadZipFile,ET.XMLSyntaxError) as exc:raise ValueError('legacy_magic_mismatch') from exc

def profile_xml():
 return '''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop><prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop><prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop><prop oor:name="BlockUntrustedRefererLinks" oor:op="fuse"><value>true</value></prop><prop oor:name="DisablePythonRuntime" oor:op="fuse"><value>true</value></prop></item>
<item oor:path="/org.openoffice.Office.Writer/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>0</value></prop><prop oor:name="Field" oor:op="fuse"><value>false</value></prop><prop oor:name="Chart" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>1</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Load"><prop oor:name="UserDefinedSettings" oor:op="fuse"><value>false</value></prop></item>
</oor:items>'''

def run_bounded(args,**kwargs):
 timeout=kwargs.pop('timeout');kwargs.pop('capture_output')
 with subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs) as process:
  try:stdout,stderr=process.communicate(timeout=timeout)
  except subprocess.TimeoutExpired:
   if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=10)
   else:process.kill()
   process.communicate();raise
  return subprocess.CompletedProcess(args,process.returncode,stdout,stderr)

def convert_official(raw,suffix,work,*,timeout=45,runner=run_bounded,converter=None):
 preflight(raw,suffix);exe=converter or converter_path()
 if not exe:raise ValueError('legacy_converter_unavailable')
 work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 if any(p.is_symlink() or p.is_junction() for p in [work,*work.parents]):raise ValueError('legacy_work_link_rejected')
 with tempfile.TemporaryDirectory(prefix='legacy-',dir=work) as folder:
  root=Path(folder);profile=root/'profile';(profile/'user').mkdir(parents=True)
  (profile/'user/registrymodifications.xcu').write_text(profile_xml(),encoding='utf8')
  source=root/('official'+suffix);source.write_bytes(raw);out=root/'output';out.mkdir()
  args=[str(exe),'-env:UserInstallation='+profile.as_uri(),'--headless','--nologo','--nodefault','--nofirststartwizard','--norestore','--convert-to','pdf','--outdir',str(out),str(source)]
  try:r=runner(args,capture_output=True,timeout=min(60,max(1,timeout)),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  except subprocess.TimeoutExpired as exc:raise ValueError('legacy_conversion_timeout') from exc
  target=out/'official.pdf'
  if r.returncode or not target.is_file() or target.stat().st_size>MAX_BYTES:raise ValueError('legacy_conversion_failed')
  pdf=target.read_bytes()
  import pymupdf
  with pymupdf.open(stream=pdf,filetype='pdf') as doc:
   if doc.needs_pass or not 1<=len(doc)<=100:raise ValueError('legacy_pdf_limits')
   page_count=len(doc);text='\n'.join(p.get_text() for p in doc)
   if len(text)>1_000_000:raise ValueError('legacy_text_limit')
  return pdf,dict(original_sha256=hashlib.sha256(raw).hexdigest(),derived_sha256=hashlib.sha256(pdf).hexdigest(),original_format=suffix,derived_mime='application/pdf',derivation='local_libreoffice_pdf',converter_executable_sha256=hashlib.sha256(Path(exe).read_bytes()).hexdigest(),pages=page_count,text_characters=len(text),scope='Derived content only, not an official PDF byte identity; no automatic catalog/unique identity promotion.')
