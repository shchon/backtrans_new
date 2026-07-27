import { useState, useEffect, useRef, useCallback } from 'react';
import type { SubtitleRow } from '../db/operations';
import {
  createSession, createSubtitlesBatch, getSubtitlesForSession,
  createTranslation, createEvaluation, updateEvaluationStatus,
  updateSessionCompleted, getAllStats, recordSentenceCompleted,
} from '../db/operations';
import { callAi, buildContext } from '../ai/client';
import { parseSrt } from '../srt/parser';
import { pairByIndex } from '../srt/pairing';
import { loadConfig } from '../config/index';

interface Props {
  onNavigateToReview?: (sessionId: number) => void;
  pendingSessionId?: number | null;
}

export default function LearnPage({ onNavigateToReview, pendingSessionId }: Props) {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [subtitles, setSubtitles] = useState<SubtitleRow[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [hasSession, setHasSession] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{today: number; total: number; streak: number}>({today: 0, total: 0, streak: 0});
  const [input, setInput] = useState('');
  const [importStep, setImportStep] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setStats(getAllStats());
  }, [completedCount]);

  useEffect(() => {
    if (!pendingSessionId) return;
    const subs = getSubtitlesForSession(pendingSessionId);
    setSessionId(pendingSessionId);
    setSubtitles(subs);
    setTotalCount(subs.length);
    setCurrentIdx(0);
    setCompletedCount(0);
    setHasSession(true);
    setTimeout(() => inputRef.current?.focus(), 100);
  }, [pendingSessionId]);

  const handleSubmit = useCallback(async () => {
    const text = input.trim();
    if (!text || sessionId === null || currentIdx >= subtitles.length) return;

    setLoading(true);
    setError(null);
    const sub = subtitles[currentIdx];

    try {
      const tid = createTranslation(sub.id, text, 1);
      const eid = createEvaluation(tid, "pending");

      // AI call in background
      const config = loadConfig();
      const context = buildContext(subtitles, sub.idx, config.contextN);
      const result = await callAi(config, context, text, sub.english_official);

      if (result) {
        updateEvaluationStatus(eid, "done",
          result.meaning_score, result.grammar_score,
          result.naturalness_score, result.subtitle_style_score,
          result.analysis, JSON.stringify(result.suggested_expressions),
        );
      } else {
        updateEvaluationStatus(eid, "failed", null, null, null, null, null, null, "AI call failed");
      }

      setCompletedCount(prev => prev + 1);
      setCurrentIdx(prev => prev + 1);
      setInput('');
      setLoading(false);
      recordSentenceCompleted();
      updateSessionCompleted(sessionId, completedCount + 1);
      inputRef.current?.focus();

      if (currentIdx + 1 >= subtitles.length) {
        setTimeout(() => onNavigateToReview?.(sessionId), 800);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '提交失败');
      setLoading(false);
    }
  }, [input, sessionId, currentIdx, subtitles, completedCount, onNavigateToReview]);

  const handleImport = async () => {
    setError(null);

    // Step 1: Pick Chinese SRT
    setImportStep('① 请选择中文 SRT 文件');
    const chInput = document.createElement('input');
    chInput.type = 'file';
    chInput.accept = '*/*';
    const chFile = await new Promise<File | null>(resolve => {
      chInput.onchange = () => resolve(chInput.files?.[0] ?? null);
      chInput.click();
    });
    if (!chFile) { setImportStep(null); return; }

    // Step 2: Pick English SRT
    setImportStep('② 请选择英文 SRT 文件');
    const enInput = document.createElement('input');
    enInput.type = 'file';
    enInput.accept = '*/*';
    const enFile = await new Promise<File | null>(resolve => {
      enInput.onchange = () => resolve(enInput.files?.[0] ?? null);
      enInput.click();
    });
    if (!enFile) { setImportStep(null); return; }

    setLoading(true);
    setImportStep(null);
    setError(null);
    try {
      const chText = await chFile.text();
      const enText = await enFile.text();
      const name = chFile.name.replace(/\.srt$/i, '').replace(/\.txt$/i, '');

      const chSubs = parseSrt(chText);
      const enSubs = parseSrt(enText);
      if (!chSubs.length || !enSubs.length) {
        throw new Error('无法解析字幕文件');
      }

      const pairs = pairByIndex(chSubs, enSubs);
      if (!pairs.length) throw new Error('没有可配对的中英字幕');

      const sid = createSession(name, pairs.length);
      const subsList: Record<string, unknown>[] = pairs.map(([ch, en], i) => ({
        idx: i + 1, chinese: ch.text, english_official: en.text,
        prev_chinese: i > 0 ? pairs[i-1][0].text : '',
        prev_english: i > 0 ? pairs[i-1][1].text : '',
        next_chinese: i < pairs.length - 1 ? pairs[i+1][0].text : '',
        next_english: i < pairs.length - 1 ? pairs[i+1][1].text : '',
      }));
      createSubtitlesBatch(sid, subsList);

      const dbSubs = getSubtitlesForSession(sid);
      setSessionId(sid);
      setSubtitles(dbSubs);
      setTotalCount(dbSubs.length);
      setCurrentIdx(0);
      setCompletedCount(0);
      setHasSession(true);
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '导入失败');
      setLoading(false);
    }
  };

  const handleSkip = () => {
    setCompletedCount(prev => prev + 1);
    setCurrentIdx(prev => prev + 1);
    setInput('');
    inputRef.current?.focus();
    if (sessionId !== null && currentIdx + 1 >= subtitles.length) {
      setTimeout(() => onNavigateToReview?.(sessionId), 500);
    }
  };

  // Render
  if (!hasSession) {
    return (
      <div className="learn-page">
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
          <h1 style={{fontSize:20,fontWeight:'bold'}}>回译训练</h1>
        </div>
        <div style={{background:'#f0f7ff',border:'1px solid #d0e4f7',borderRadius:8,padding:'10px 16px',display:'flex',gap:24,marginBottom:16,fontSize:14}}>
          <span style={{color:'#e67e22',fontWeight:'bold'}}>🔥 连续 {stats.streak} 天</span>
          <span style={{color:'#4a90d9',fontWeight:'bold'}}>今日 {stats.today} 句</span>
          <span style={{color:'#27ae60',fontWeight:'bold'}}>总计 {stats.total} 句</span>
        </div>
        {importStep && <div style={{background:'#fff3cd',color:'#856404',padding:'8px 12px',borderRadius:4,marginBottom:12,fontSize:14,textAlign:'center'}}>{importStep}</div>}
        {error && <div className="error" style={{background:'#fdd',color:'#c33',padding:'8px 12px',borderRadius:4,marginBottom:12}}>{error}</div>}
        <div style={{textAlign:'center',padding:60,color:'#999',fontSize:16}}>
          <p>点击下方按钮导入字幕文件开始学习</p>
          <button onClick={handleImport} disabled={loading} style={{marginTop:20,background:'#4a90d9',color:'white',border:'none',padding:'10px 24px',borderRadius:4,fontSize:14,cursor:'pointer'}}>
            {loading ? '处理中...' : '导入字幕'}
          </button>
        </div>
      </div>
    );
  }

  const currentSub = subtitles[currentIdx];
  return (
    <div className="learn-page">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <h1 style={{fontSize:20,fontWeight:'bold'}}>回译训练</h1>
        <button onClick={() => { setHasSession(false); }} style={{background:'#e74c3c',color:'white',border:'none',padding:'6px 14px',borderRadius:4,fontSize:13,cursor:'pointer'}}>
          结束学习
        </button>
      </div>
      <div style={{marginBottom:8}}>
        <div style={{height:8,background:'#e0e0e0',borderRadius:4,overflow:'hidden'}}>
          <div style={{height:'100%',width:`${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%`,background:'#4a90d9',transition:'width 0.3s'}} />
        </div>
        <div style={{color:'#666',fontSize:13,marginTop:4}}>第 {Math.min(currentIdx + 1, totalCount)}/{totalCount} 句</div>
      </div>
      {error && <div style={{background:'#fdd',color:'#c33',padding:'8px 12px',borderRadius:4,marginBottom:12}}>{error}</div>}
      {currentSub && (
        <div style={{marginTop:16}}>
          <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:12}}>
            <span style={{fontSize:13,color:'#666'}}>跳转到第</span>
            <input type="number" min={1} max={totalCount} defaultValue={currentIdx + 1}
              onKeyDown={(e) => { if (e.key === 'Enter') { const v = parseInt((e.target as HTMLInputElement).value) - 1; if (v >= 0 && v < totalCount) { setCurrentIdx(v); setInput(''); }}}}
              style={{width:60,padding:'4px 8px',border:'1px solid #ccc',borderRadius:3,fontSize:13}} />
            <span style={{fontSize:13,color:'#666'}}>/ {totalCount} 句</span>
          </div>
          <div style={{fontSize:20,minHeight:60,marginBottom:16,lineHeight:1.5}}>{currentSub.chinese}</div>
          <input ref={inputRef} type="text" value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !loading) handleSubmit(); }}
            placeholder="输入英文翻译，按 Enter 提交..." disabled={loading}
            style={{width:'100%',padding:'10px 12px',fontSize:15,border:'1px solid #ccc',borderRadius:4,outline:'none',marginBottom:8}} />
          <div style={{display:'flex',gap:8}}>
            <button onClick={handleSkip} disabled={loading} style={{padding:'8px 20px',border:'1px solid #ccc',borderRadius:4,fontSize:13,cursor:'pointer',background:'white',color:'#888'}}>跳过</button>
            <button onClick={handleSubmit} disabled={loading || !input.trim()} style={{padding:'8px 20px',border:'none',borderRadius:4,fontSize:13,cursor:'pointer',background:loading?'#999':'#4a90d9',color:'white'}}>{loading ? 'AI 批改中...' : '下一句'}</button>
          </div>
        </div>
      )}
      <div style={{background:'#f0f7ff',border:'1px solid #d0e4f7',borderRadius:8,padding:'10px 16px',display:'flex',gap:24,marginTop:24,fontSize:14}}>
        <span style={{color:'#e67e22',fontWeight:'bold'}}>🔥 连续 {stats.streak} 天</span>
        <span style={{color:'#4a90d9',fontWeight:'bold'}}>今日 {stats.today} 句</span>
        <span style={{color:'#27ae60',fontWeight:'bold'}}>总计 {stats.total} 句</span>
      </div>
    </div>
  );
}
