import { useState, useEffect } from 'react';
import {
  getFavorites, removeFavorite, clearFavorites,
  createSession, createSubtitlesBatch,
} from '../db/operations';

interface Props { onStartReview: (sessionId: number) => void; }

export default function FavoritesPage({ onStartReview }: Props) {
  const [favorites, setFavorites] = useState<Record<string, unknown>[]>([]);

  const load = () => { try { setFavorites(getFavorites()); } catch {} };
  useEffect(() => { load(); }, []);

  const del = (subId: number) => { removeFavorite(subId); load(); };
  const clearAll = () => { clearFavorites(); load(); };

  const startReview = () => {
    if (!favorites.length) return;
    const sid = createSession('收藏复习', favorites.length);
    const subs = favorites.map((fav, i) => ({
      idx: i + 1, chinese: fav.chinese as string, english_official: fav.english_official as string,
      prev_chinese: '', prev_english: '', next_chinese: '', next_english: '',
    }));
    createSubtitlesBatch(sid, subs);
    onStartReview(sid);
  };

  const [visibleEn, setVisibleEn] = useState<Set<number>>(new Set());
  const toggleEn = (id: number) => { const n = new Set(visibleEn); n.has(id) ? n.delete(id) : n.add(id); setVisibleEn(n); };

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:'bold',marginBottom:16}}>收藏夹</h1>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        <button onClick={startReview} disabled={!favorites.length} style={{background:'#4a90d9',color:'white',border:'none',padding:'8px 16px',borderRadius:4,fontSize:14,cursor:'pointer'}}>复习收藏</button>
        <button onClick={clearAll} disabled={!favorites.length} style={{background:'#e74c3c',color:'white',border:'none',padding:'8px 16px',borderRadius:4,fontSize:14,cursor:'pointer'}}>清空</button>
        <span style={{color:'#666',lineHeight:'36px'}}>共 {favorites.length} 句</span>
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:4}}>
        {favorites.map((fav,i) => (
          <div key={i} style={{border:'1px solid #ddd',borderRadius:6,padding:'8px 12px',background:'white',display:'flex',alignItems:'center',gap:10}}>
            <span style={{color:'#999',fontSize:12}}>#{i+1}</span>
            <span style={{flex:1,fontSize:14}}>{fav.chinese as string}</span>
            <button onClick={()=>toggleEn(fav.id as number)} style={{color:'#4a90d9',border:'none',background:'none',cursor:'pointer',fontSize:12}}>查看英文 ▸</button>
            {visibleEn.has(fav.id as number) && <span style={{color:'#666',fontSize:13,fontStyle:'italic'}}>{fav.english_official as string}</span>}
            <button onClick={()=>del(fav.id as number)} style={{color:'#e74c3c',border:'none',background:'none',cursor:'pointer',fontSize:16}}>×</button>
          </div>
        ))}
        {!favorites.length && <p style={{color:'#999',textAlign:'center',padding:40}}>暂无收藏句子</p>}
      </div>
    </div>
  );
}
