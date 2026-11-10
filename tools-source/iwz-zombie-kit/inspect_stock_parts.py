import json,struct,sys,os,glob
import numpy as np
root=sys.argv[1]
def readglb(p):
    b=open(p,'rb').read()
    l=struct.unpack_from('<I',b,12)[0]; js=json.loads(b[20:20+l])
    off=20+l; bl=struct.unpack_from('<I',b,off)[0]; bin_=b[off+8:off+8+bl]
    return js,bin_
CT={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def acc(js,bin_,i):
    a=js['accessors'][i]; bv=js['bufferViews'][a['bufferView']]
    dt=np.dtype(CT[a['componentType']]); n=NC[a['type']]
    o=bv.get('byteOffset',0)+a.get('byteOffset',0); st=bv.get('byteStride',dt.itemsize*n)
    raw=np.frombuffer(bin_,dtype=np.uint8,count=st*(a['count']-1)+dt.itemsize*n,offset=o)
    out=np.lib.stride_tricks.as_strided(raw,shape=(a['count'],dt.itemsize*n),strides=(st,1)).copy().view(dt).reshape(a['count'],n)
    return out
res={}
for p in sorted(glob.glob(os.path.join(root,'*','*.glb'))):
    js,bin_=readglb(p); name=os.path.basename(os.path.dirname(p))
    nodes=js['nodes']; skin=js.get('skins',[{}])[0]; joints=[nodes[j].get('name') for j in skin.get('joints',[])]
    tris=0; prims=[]; allv=[]; usedj=set()
    for m in js['meshes']:
        for pr in m['primitives']:
            idx=acc(js,bin_,pr['indices']); t=len(idx)//3; tris+=t
            P=acc(js,bin_,pr['attributes']['POSITION']); allv.append(P)
            mat=js['materials'][pr['material']]['name'] if 'material' in pr else None
            J=acc(js,bin_,pr['attributes']['JOINTS_0']) if 'JOINTS_0' in pr['attributes'] else None
            W=acc(js,bin_,pr['attributes']['WEIGHTS_0']) if 'WEIGHTS_0' in pr['attributes'] else None
            jl=[]
            if J is not None:
                for k in range(4):
                    sel=W[:,k]>0.01; jl+=list(np.unique(J[sel,k]))
            js_used=sorted(set(joints[int(x)] for x in jl)); usedj|=set(js_used)
            prims.append({'mat':mat,'tris':t,'verts':len(P),'bbmin':P.min(0).round(3).tolist(),'bbmax':P.max(0).round(3).tolist()})
    V=np.concatenate(allv)
    res[name]={'tris':tris,'prims':prims,'nskinjoints':len(joints),'joints_weighted':sorted(usedj),'bbmin':V.min(0).round(3).tolist(),'bbmax':V.max(0).round(3).tolist()}
json.dump(res,open(sys.argv[2],'w'),indent=1)
for k,v in res.items():
    print(k,v['tris'],'bb',v['bbmin'],v['bbmax'],'mats',[ (p['mat'],p['tris']) for p in v['prims']])
    print('   weighted:',' '.join(v['joints_weighted']))
