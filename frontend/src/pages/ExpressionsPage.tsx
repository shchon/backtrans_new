import { useState, useEffect } from 'react';
import { getAllExpressions, deleteExpression } from '../db/operations';
import type { ExpressionRow } from '../db/operations';

export default function ExpressionsPage() {
  const [expressions, setExpressions] = useState<ExpressionRow[]>([]);
  const [search, setSearch] = useState('');

  const load = () => { try { setExpressions(getAllExpressions()); } catch {} };
  useEffect(() => { load(); }, []);

  const del = (id: number) => { deleteExpression(id); load(); };

  const filtered = search ? expressions.filter(e => e.phrase.toLowerCase().includes(search.toLowerCase())) : expressions;

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:'bold',marginBottom:16}}>表达库</h1>
      <input type="text" placeholder="搜索表达..." value={search} onChange={e=>setSearch(e.target.value)}
        style={{width:'100%',padding:'8px 12px',border:'1px solid #ccc',borderRadius:4,fontSize:14,marginBottom:12}} />
      <div style={{display:'flex',flexDirection:'column',gap:4}}>
        {filtered.map(e => (
          <div key={e.id} style={{border:'1px solid #ddd',borderRadius:6,padding:'8px 12px',background:'white',display:'flex',alignItems:'center',gap:10}}>
            <span style={{flex:1,fontSize:15,fontWeight:'bold'}}>{e.phrase}</span>
            {e.notes && <span style={{color:'#666',fontSize:13}}>{e.notes}</span>}
            <button onClick={()=>del(e.id)} style={{color:'#e74c3c',border:'none',background:'none',cursor:'pointer',fontSize:14}}>删除</button>
          </div>
        ))}
        {!filtered.length && <p style={{color:'#999',textAlign:'center',padding:40}}>{search?'没有匹配的表达':'还没有收藏的表达'}</p>}
      </div>
    </div>
  );
}
