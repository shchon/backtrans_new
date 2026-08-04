import { useState, useEffect, useRef } from 'react';
import { loadConfig, saveConfig } from '../config/index';
import type { AppConfig } from '../config/index';
import { testConnection } from '../ai/client';
import { getFavorites, addFavorite } from '../db/operations';
import { getAllExpressions, addExpression } from '../db/operations';

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [exportJson, setExportJson] = useState<string | null>(null);
  const exportTextareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { setConfig(loadConfig()); }, []);

  const update = (field: keyof AppConfig, value: string | number) => {
    setConfig(prev => prev ? { ...prev, [field]: value } : prev);
  };

  const handleSave = () => {
    if (!config) return;
    saveConfig(config);
    setMessage('保存成功');
    setTimeout(() => setMessage(null), 2000);
  };

  const handleTest = async () => {
    if (!config) return;
    setTesting(true);
    setMessage(null);
    const result = await testConnection(config.baseUrl, config.apiKey, config.model);
    setMessage(result.ok ? '连接成功' : `连接失败: ${result.error}`);
    setTesting(false);
  };

  const handleExport = () => {
    const data = {
      version: 1,
      exported_at: new Date().toISOString(),
      config: loadConfig(),
      favorites: getFavorites(),
      expressions: getAllExpressions(),
    };
    setExportJson(JSON.stringify(data, null, 2));
  };

  const handleCopy = () => {
    const ta = exportTextareaRef.current;
    if (!ta) return;
    ta.select();
    ta.setSelectionRange(0, 999999);
    document.execCommand('copy');
    setMessage('已复制到剪贴板');
    setTimeout(() => setMessage(null), 2000);
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json,*/*';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (!data.version || !data.config) {
          setMessage('导入失败: 无效的备份文件格式');
          return;
        }

        // Restore config
        saveConfig({ ...loadConfig(), ...data.config });

        // Restore favorites (skip duplicates via INSERT OR IGNORE)
        if (Array.isArray(data.favorites)) {
          for (const fav of data.favorites) {
            if (fav.id) addFavorite(Number(fav.id));
          }
        }

        // Restore expressions (skip duplicates)
        if (Array.isArray(data.expressions)) {
          for (const expr of data.expressions) {
            if (expr.phrase) {
              addExpression(expr.phrase, expr.source_subtitle_id ?? 0, expr.notes ?? '');
            }
          }
        }

        // Reload config into state
        setConfig(loadConfig());
        setMessage('导入成功');
        setTimeout(() => setMessage(null), 3000);
      } catch {
        setMessage('导入失败: 无法解析文件');
      }
    };
    input.click();
  };

  if (!config) return <div><p style={{color:'#999'}}>加载中...</p></div>;

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:'bold',marginBottom:16}}>设置</h1>
      <div style={{maxWidth:500,display:'flex',flexDirection:'column',gap:12}}>
        {[
          ['Base URL', 'baseUrl', 'text'],
          ['API Key', 'apiKey', 'password'],
          ['Model', 'model', 'text'],
        ].map(([label, field, type]) => (
          <div key={field}>
            <label style={{display:'block',fontSize:13,color:'#666',marginBottom:4}}>{label}</label>
            <input type={type} value={config[field as keyof AppConfig] as unknown as string}
              onChange={e => update(field as keyof AppConfig, e.target.value)}
              style={{width:'100%',padding:'8px 10px',border:'1px solid #ccc',borderRadius:4,fontSize:14}} />
          </div>
        ))}
        <div>
          <label style={{display:'block',fontSize:13,color:'#666',marginBottom:4}}>上下文句数</label>
          <input type="number" min={0} max={5} value={config.contextN}
            onChange={e => update('contextN', parseInt(e.target.value) || 0)}
            style={{width:80,padding:'8px 10px',border:'1px solid #ccc',borderRadius:4,fontSize:14}} />
        </div>
        <div>
          <label style={{display:'block',fontSize:13,color:'#666',marginBottom:4}}>复盘字体大小</label>
          <input type="number" min={10} max={24} value={config.fontSize}
            onChange={e => update('fontSize', parseInt(e.target.value) || 14)}
            style={{width:80,padding:'8px 10px',border:'1px solid #ccc',borderRadius:4,fontSize:14}} />
        </div>
        <div>
          <label style={{display:'block',fontSize:13,color:'#666',marginBottom:4}}>Prompt 模板</label>
          <textarea value={config.promptTemplate} onChange={e => update('promptTemplate', e.target.value)}
            rows={10} style={{width:'100%',padding:'8px 10px',border:'1px solid #ccc',borderRadius:4,fontSize:13,fontFamily:'monospace'}} />
        </div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <button onClick={handleTest} disabled={testing} style={{padding:'8px 16px',border:'1px solid #4a90d9',color:'#4a90d9',background:'white',borderRadius:4,cursor:'pointer',fontSize:14}}>{testing?'测试中...':'测试连接'}</button>
          <button onClick={handleSave} style={{background:'#4a90d9',color:'white',border:'none',padding:'8px 24px',borderRadius:4,fontSize:14,cursor:'pointer'}}>保存</button>
        </div>
        <div style={{borderTop:'1px solid #eee',paddingTop:12,display:'flex',gap:8,flexWrap:'wrap'}}>
          <button onClick={handleExport} style={{padding:'8px 16px',border:'1px solid #27ae60',color:'#27ae60',background:'white',borderRadius:4,cursor:'pointer',fontSize:14}}>导出备份</button>
          <button onClick={handleImport} style={{padding:'8px 16px',border:'1px solid #f39c12',color:'#f39c12',background:'white',borderRadius:4,cursor:'pointer',fontSize:14}}>导入备份</button>
        </div>
        {message && <div style={{padding:'8px 12px',borderRadius:4,background:message.includes('成功')?'#dfd':'#fdd',color:message.includes('成功')?'#272':'#c33',fontSize:13}}>{message}</div>}

        {exportJson && (
          <div style={{borderTop:'1px solid #eee',paddingTop:12}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6}}>
              <span style={{fontSize:13,color:'#666'}}>备份数据（复制内容保存为 .json 文件）</span>
              <div style={{display:'flex',gap:6}}>
                <button onClick={handleCopy} style={{padding:'6px 14px',border:'1px solid #4a90d9',color:'#4a90d9',background:'white',borderRadius:4,cursor:'pointer',fontSize:13}}>复制</button>
                <button onClick={() => setExportJson(null)} style={{padding:'6px 14px',border:'1px solid #ccc',color:'#666',background:'white',borderRadius:4,cursor:'pointer',fontSize:13}}>关闭</button>
              </div>
            </div>
            <textarea ref={exportTextareaRef} readOnly value={exportJson}
              style={{width:'100%',height:200,padding:8,border:'1px solid #ccc',borderRadius:4,fontSize:12,fontFamily:'monospace'}} />
          </div>
        )}
      </div>
    </div>
  );
}
