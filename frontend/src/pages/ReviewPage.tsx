import { useState, useEffect, useRef } from 'react';
import type { SubtitleRow } from '../db/operations';
import {
  getSubtitlesForSession, getEvaluationsForSession,
  getAllTranslationsForSubtitle,
  addFavorite, removeFavorite, addExpression, isFavorite,
} from '../db/operations';
import type { EvalRow } from '../db/operations';

interface Props { sessionId: number | null; active?: boolean; }

interface EvalWithSub { eval: EvalRow; sub: SubtitleRow; userTranslation: string; }

export default function ReviewPage({ sessionId, active }: Props) {
  const [items, setItems] = useState<EvalWithSub[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  const [collectTexts, setCollectTexts] = useState<Record<number, string>>({});

  const loadData = () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const evals = getEvaluationsForSession(sessionId);
      const subs = getSubtitlesForSession(sessionId);
      const subMap = new Map(subs.map(s => [s.id, s]));
      const combined: EvalWithSub[] = [];
      for (const ev of evals) {
        const sub = subMap.get((ev as unknown as Record<string, unknown>).subtitle_id as number);
        if (!sub) continue;
        const translations = getAllTranslationsForSubtitle(sub.id);
        const userTranslation = translations.length > 0 ? translations[translations.length - 1].user_input : '';
        combined.push({ eval: ev, sub, userTranslation });
      }
      combined.sort((a, b) => a.sub.idx - b.sub.idx);
      setItems(combined);

      // Load existing favorites
      const favSet = new Set<number>();
      for (const item of combined) {
        if (isFavorite(item.sub.id)) favSet.add(item.sub.id);
      }
      setFavorites(favSet);
    } catch { setError('加载失败'); }
    setLoading(false);
  };

  useEffect(() => { loadData(); setExpanded(new Set()); }, [sessionId]);

  // Reload when page becomes active (pages stay mounted)
  const prevActive = useRef(false);
  useEffect(() => {
    if (active && !prevActive.current) loadData();
    prevActive.current = !!active;
  }, [active]);

  // Poll for pending evaluations every 2s
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (!sessionId) return;
    pollRef.current = setInterval(() => {
      // Always refresh data first, then check if done
      loadData();
      const current = getEvaluationsForSession(sessionId);
      const hasPending = current.some(e => e.status === 'pending' || e.status === 'processing');
      if (!hasPending && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 2000);
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [sessionId]);

  const toggleExpand = (id: number) => {
    const next = new Set(expanded);
    next.has(id) ? next.delete(id) : next.add(id);
    setExpanded(next);
  };

  const toggleFav = (subId: number) => {
    if (favorites.has(subId)) { removeFavorite(subId); favorites.delete(subId); }
    else { addFavorite(subId); favorites.add(subId); }
    setFavorites(new Set(favorites));
  };

  const doCollect = (subId: number) => {
    const text = collectTexts[subId]?.trim();
    if (text) { addExpression(text, subId); setCollectTexts(p => ({...p, [subId]: ''})); }
  };

  const scoreColor = (s: number | null) =>
    s === null ? '#999' : s >= 80 ? '#27ae60' : s >= 60 ? '#f39c12' : '#e74c3c';

  if (!sessionId) return <div><h1 style={{fontSize:20,fontWeight:'bold',marginBottom:16}}>复盘</h1><p style={{color:'#999'}}>请先完成学习</p></div>;

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:'bold',marginBottom:16}}>复盘</h1>
      {loading && <p style={{color:'#999'}}>加载中...</p>}
      {error && <div style={{background:'#fdd',color:'#c33',padding:'8px 12px',borderRadius:4,marginBottom:12}}>{error}</div>}
      <div style={{display:'flex',flexDirection:'column',gap:6}}>
        {items.map(({ eval: ev, sub, userTranslation }) => {
          const avg = ((ev.meaning_score ?? 0) + (ev.grammar_score ?? 0) + (ev.naturalness_score ?? 0) + (ev.subtitle_style_score ?? 0)) / 4;
          const exp = expanded.has(sub.id);
          return (
            <div key={sub.id} onClick={() => toggleExpand(sub.id)} style={{border:'1px solid #ddd',borderRadius:6,padding:10,background:'white',cursor:'pointer'}}>
              <div style={{display:'flex',alignItems:'center',gap:10}}>
                <span style={{color:'#999',fontSize:12,minWidth:30}}>#{sub.idx}</span>
                <span style={{flex:1,fontSize:14}}>{sub.chinese}</span>
                {ev.status === 'done' ? (
                  <span style={{color:scoreColor(Math.round(avg)),fontWeight:'bold',fontSize:13,padding:'2px 8px',border:`1px solid ${scoreColor(Math.round(avg))}`,borderRadius:10}}>综合 {Math.round(avg)}</span>
                ) : ev.status === 'failed' ? <span style={{color:'#e74c3c',fontSize:13}}>❌ 失败</span> : <span style={{color:'#888',fontSize:13}}>⏳ 等待批改</span>}
                <span onClick={(e) => { e.stopPropagation(); toggleFav(sub.id); }} style={{cursor:'pointer',fontSize:18,color:favorites.has(sub.id)?'#f1c40f':'#bbb'}}>{favorites.has(sub.id)?'★':'☆'}</span>
                <span style={{color:'#999'}}>{exp?'▾':'▸'}</span>
              </div>
              {exp && (
                <div style={{marginTop:12,paddingTop:12,borderTop:'1px solid #eee'}}>
                  {userTranslation && (
                    <div style={{fontSize:14,color:'#4a90d9',fontStyle:'italic',marginBottom:12,padding:8,background:'#f0f5ff',borderRadius:4,whiteSpace:'pre-wrap'}}>
                      你的翻译: {userTranslation}
                    </div>
                  )}
                  {ev.status === 'done' && <>
                    <div style={{display:'flex',gap:8,marginBottom:12}}>
                      {[['意思',ev.meaning_score],['语法',ev.grammar_score],['自然度',ev.naturalness_score],['字幕风格',ev.subtitle_style_score]].map(([n,s]) => (
                        <span key={n as string} style={{fontSize:12,color:scoreColor(s as number|null),padding:'3px 8px',border:`1px solid ${scoreColor(s as number|null)}`,borderRadius:10}}>{n as string} {s}</span>
                      ))}
                    </div>
                    {ev.analysis_text && <div style={{fontSize:14,color:'#333',lineHeight:1.6,marginBottom:12,whiteSpace:'pre-wrap'}}>{ev.analysis_text}</div>}
                  </>}
                  <div style={{marginBottom:8}}>
                    <span style={{color:'#4a90d9',fontSize:13,cursor:'pointer'}} onClick={(e) => { e.stopPropagation(); const el = (e.target as HTMLElement).nextElementSibling as HTMLElement; if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none'; }}>查看官方字幕 ▸</span>
                    <div style={{display:'none',color:'#666',fontSize:14,padding:8,background:'#fafafa',borderRadius:4,marginTop:4}}>{sub.english_official}</div>
                  </div>
                  {ev.status === 'done' && ev.suggested_expressions && (() => {
                    let suggested: string[] = [];
                    try { suggested = typeof ev.suggested_expressions === 'string' ? JSON.parse(ev.suggested_expressions) : ev.suggested_expressions; } catch { suggested = []; }
                    return suggested.length ? <div style={{marginBottom:8}}>{suggested.map((expr,i) => (
                      <button key={i} onClick={(e) => { e.stopPropagation(); addExpression(expr, sub.id); }} style={{marginRight:6,marginBottom:4,fontSize:13,color:'#4a90d9',border:'1px solid #4a90d9',background:'white',padding:'3px 10px',borderRadius:12,cursor:'pointer'}}>收藏: {expr}</button>
                    ))}</div> : null;
                  })()}
                  <div style={{display:'flex',gap:6,marginBottom:8}}>
                    <input type="text" placeholder="手动添加表达..." value={collectTexts[sub.id]||''} onChange={e => setCollectTexts(p=>({...p,[sub.id]:e.target.value}))} onClick={e=>e.stopPropagation()} style={{flex:1,padding:'6px 10px',border:'1px solid #ccc',borderRadius:4,fontSize:13}} />
                    <button onClick={(e)=>{e.stopPropagation();doCollect(sub.id);}} style={{padding:'6px 12px',border:'1px solid #4a90d9',color:'#4a90d9',background:'white',borderRadius:4,cursor:'pointer',fontSize:13}}>添加</button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
        {!loading && items.length === 0 && !error && <p style={{color:'#999',textAlign:'center',padding:40}}>暂无评估数据</p>}
      </div>
    </div>
  );
}
