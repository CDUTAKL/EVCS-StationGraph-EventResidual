#!/usr/bin/env python3
"""Verify an LFS-only history migration without dumping binary contents."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--repo',required=True);p.add_argument('--old',required=True);p.add_argument('--new',required=True);p.add_argument('--published',required=True);p.add_argument('--out',required=True)
a=p.parse_args();root=Path(a.repo)
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
def tree(ref):
 result={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode().split();result[path.decode()]={'mode':mode,'kind':kind,'oid':oid}
 return result
def digest_blob(oid):
 h=hashlib.sha256();n=0
 with subprocess.Popen(['git','cat-file','blob',oid],cwd=root,stdout=subprocess.PIPE) as pr:
  for b in iter(lambda:pr.stdout.read(1024*1024),b''):h.update(b);n+=len(b)
  if pr.wait():raise RuntimeError('cat-file failed')
 return h.hexdigest(),n
def digest_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def inventory(ref):
 objects=git('rev-list','--objects',a.published+'..'+ref)
 raw=git('cat-file','--batch-check=%(objecttype) %(objectsize) %(objectname) %(rest)',input=objects)
 found=[]
 for row in raw.decode().splitlines():
  kind,size,oid,*path=row.split(' ',3)
  if kind=='blob' and int(size)>100*1024**2:found.append({'git_blob':oid,'bytes':int(size),'path':path[0] if path else ''})
 return found
old,new=tree(a.old),tree(a.new)
if old.keys()!=new.keys():raise SystemExit('migration changed path inventory')
subprocess.run(['git','merge-base','--is-ancestor',a.published,a.new],cwd=root,check=True)
common=Path(git('rev-parse','--git-common-dir').decode().strip())
if not common.is_absolute():common=root/common
changed=[]
for path in old:
 if old[path]==new[path]:continue
 if old[path]['mode']!=new[path]['mode']:raise SystemExit('migration changed file mode: '+path)
 if path=='.gitattributes':continue
 pointer=git('cat-file','blob',new[path]['oid']).decode()
 fields=dict(line.split(' ',1) for line in pointer.strip().splitlines())
 if fields.get('version')!='https://git-lfs.github.com/spec/v1':raise SystemExit('unexpected source change: '+path)
 oid=fields['oid'].removeprefix('sha256:');size=int(fields['size'])
 actual,n=digest_blob(old[path]['oid'])
 obj=common/'lfs/objects'/oid[:2]/oid[2:4]/oid
 if (actual,n)!=(oid,size) or not obj.is_file() or digest_file(obj)!=oid:raise SystemExit('LFS content mismatch: '+path)
 changed.append({'path':path,'original_git_blob':old[path]['oid'],'lfs_oid_sha256':oid,'bytes':size,'content_identical':True})
before=inventory(a.old);after=inventory(a.new)
if after:raise SystemExit('oversize regular Git blobs remain')
for item in before:
 oid,n=digest_blob(item['git_blob']);obj=common/'lfs/objects'/oid[:2]/oid[2:4]/oid
 if n!=item['bytes'] or not obj.is_file() or digest_file(obj)!=oid:raise SystemExit('historical LFS object mismatch')
 item['sha256']=oid
result={'status':'PASS','old_main':git('rev-parse',a.old).decode().strip(),'migrated_main':git('rev-parse',a.new).decode().strip(),'published_ancestor':a.published,'head_file_count':len(old),'head_changed_binary_paths':changed,'allowed_metadata_change':'.gitattributes','all_other_head_git_blobs_unchanged':True,'oversize_git_blobs_before':before,'oversize_git_blobs_after':after,'verification_script_sha256':digest_file(Path(__file__))}
Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'head_file_count':len(old),'changed_binary_paths':len(changed),'oversize_unique_blobs':len(before),'remaining_oversize':len(after)},ensure_ascii=False))
