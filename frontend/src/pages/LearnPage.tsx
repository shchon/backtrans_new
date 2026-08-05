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

const RECENT_KEY = 'backtranslate_recents';
interface RecentSession {
  name: string;
  chinese_srt: string;
  english_srt: string;
  time: number;
}

function loadRecents(): RecentSession[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveRecents(recents: RecentSession[]): void {
  localStorage.setItem(RECENT_KEY, JSON.stringify(recents.slice(0, 8)));
}

function addRecent(name: string, chineseSrt: string, englishSrt: string): void {
  const recents = loadRecents().filter(r => r.name !== name);
  recents.unshift({ name, chinese_srt: chineseSrt, english_srt: englishSrt, time: Date.now() });
  saveRecents(recents);
}

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
  const [pendingChFile, setPendingChFile] = useState<File | null>(null);
  const [pendingEnFile, setPendingEnFile] = useState<File | null>(null);
  const [recents, setRecents] = useState<RecentSession[]>(loadRecents());
  const inputRef = useRef<HTMLInputElement>(null);
  const jumpInputRef = useRef<HTMLInputElement>(null);

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

  const handleSubmit = useCallback(() => {
    const text = input.trim();
    if (!text || sessionId === null || currentIdx >= subtitles.length) return;

    setLoading(true);
    setError(null);
    const sub = subtitles[currentIdx];

    const tid = createTranslation(sub.id, text, 1);
    const eid = createEvaluation(tid, "pending");

    // Fire and forget AI call
    const config = loadConfig();
    const context = buildContext(subtitles, sub.idx, config.contextN);
    callAi(config, context, text, sub.english_official).then(r => {
      if (r.ok) {
        updateEvaluationStatus(eid, "done",
          r.result.meaning_score, r.result.grammar_score,
          r.result.naturalness_score, r.result.subtitle_style_score,
          r.result.analysis, JSON.stringify(r.result.suggested_expressions),
        );
      } else {
        updateEvaluationStatus(eid, "failed", null, null, null, null, null, null, r.error);
      }
    });

    // Move to next sentence immediately
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
  }, [input, sessionId, currentIdx, subtitles, completedCount, onNavigateToReview]);

  const doImport = async (chFile: File, enFile: File) => {
    setLoading(true);
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

      // Save to recent sessions for quick reload
      addRecent(name, chText, enText);

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
      setPendingChFile(null);
      setPendingEnFile(null);
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '导入失败');
      setLoading(false);
    }
  };

  const handleRecentClick = async (recent: RecentSession) => {
    setLoading(true);
    setError(null);
    try {
      const chSubs = parseSrt(recent.chinese_srt);
      const enSubs = parseSrt(recent.english_srt);
      if (!chSubs.length || !enSubs.length) throw new Error('无法解析字幕文件');
      const pairs = pairByIndex(chSubs, enSubs);
      if (!pairs.length) throw new Error('没有可配对的中英字幕');
      // Bump to top of recents
      addRecent(recent.name, recent.chinese_srt, recent.english_srt);
      setRecents(loadRecents());

      const sid = createSession(recent.name, pairs.length);
      const subsList = pairs.map(([ch, en], i) => ({
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
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
      setLoading(false);
    }
  };

  const handleImportCh = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '*/*';
    const file = await new Promise<File | null>(resolve => {
      input.onchange = () => resolve(input.files?.[0] ?? null);
      input.click();
    });
    if (!file) return;
    setPendingChFile(file);
    // If English already selected, auto-import
    setPendingEnFile(prev => {
      if (prev) setTimeout(() => doImport(file, prev), 100);
      return prev;
    });
  };

  const handleImportEn = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '*/*';
    const file = await new Promise<File | null>(resolve => {
      input.onchange = () => resolve(input.files?.[0] ?? null);
      input.click();
    });
    if (!file) return;
    setPendingEnFile(file);
    setPendingChFile(prev => {
      if (prev) setTimeout(() => doImport(prev, file), 100);
      return prev;
    });
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

  const handleJump = () => {
    const v = parseInt(jumpInputRef.current?.value || '') - 1;
    if (v >= 0 && v < totalCount) {
      setCurrentIdx(v);
      setInput('');
      inputRef.current?.focus();
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
        {error && <div style={{background:'#fdd',color:'#c33',padding:'8px 12px',borderRadius:4,marginBottom:12}}>{error}</div>}
        <div style={{textAlign:'center',padding:40,color:'#999',fontSize:16}}>
          <p style={{marginBottom:20}}>导入中英文字幕文件开始学习</p>
          <div style={{display:'flex',gap:12,justifyContent:'center',flexWrap:'wrap'}}>
            <button onClick={handleImportCh} disabled={loading}
              style={{background: pendingChFile ? '#27ae60' : '#4a90d9', color:'white', border:'none', padding:'10px 20px', borderRadius:4, fontSize:14, cursor:'pointer'}}>
              {pendingChFile ? '✅ 中文已选' : '导入中文字幕'}
            </button>
            <button onClick={handleImportEn} disabled={loading}
              style={{background: pendingEnFile ? '#27ae60' : '#4a90d9', color:'white', border:'none', padding:'10px 20px', borderRadius:4, fontSize:14, cursor:'pointer'}}>
              {pendingEnFile ? '✅ 英文已选' : '导入英文字幕'}
            </button>
          </div>
          {loading && <p style={{marginTop:16,color:'#666'}}>处理中...</p>}

          {recents.length > 0 && (
            <div style={{marginTop:24,width:'100%'}}>
              <p style={{fontSize:13,color:'#666',marginBottom:8,fontWeight:'bold'}}>最近字幕</p>
              <div style={{display:'flex',flexDirection:'column',gap:4}}>
                {recents.slice(0, 8).map((r, i) => (
                  <button key={i}
                    onClick={() => handleRecentClick(r)}
                    disabled={loading}
                    style={{
                      textAlign:'left',padding:'10px 14px',border:'1px solid #e0e0e0',
                      borderRadius:6,background:'white',cursor:'pointer',fontSize:13,color:'#333',
                      display:'flex',justifyContent:'space-between',alignItems:'center'
                    }}>
                    <span>{r.name}</span>
                    <span style={{color:'#bbb',fontSize:11}}>{new Date(r.time).toLocaleDateString('zh-CN', {month:'short',day:'numeric'})}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  const currentSub = subtitles[currentIdx];
  return (
    <div className="learn-page">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <h1 style={{fontSize:20,fontWeight:'bold'}}>回译训练</h1>
        <button onClick={() => { if (sessionId !== null) { updateSessionCompleted(sessionId, completedCount); recordSentenceCompleted(); setHasSession(false); onNavigateToReview?.(sessionId); } }} style={{background:'#e74c3c',color:'white',border:'none',padding:'6px 14px',borderRadius:4,fontSize:13,cursor:'pointer'}}>
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
            <input ref={jumpInputRef} type="number" min={1} max={totalCount} defaultValue={currentIdx + 1}
              style={{width:56,padding:'4px 8px',border:'1px solid #ccc',borderRadius:3,fontSize:13}} />
            <span style={{fontSize:13,color:'#666'}}>/ {totalCount} 句</span>
            <button onClick={handleJump}
              style={{padding:'4px 10px',border:'1px solid #4a90d9',color:'#4a90d9',background:'white',borderRadius:3,fontSize:12,cursor:'pointer'}}>
              GO
            </button>
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
