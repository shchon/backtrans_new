import { useState, useEffect } from 'react';
import { loadConfig, saveConfig } from '../config/index';
import type { AppConfig } from '../config/index';
import { testConnection } from '../ai/client';

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

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
    const ok = await testConnection(config.baseUrl, config.apiKey, config.model);
    setMessage(ok ? '连接成功' : '连接失败');
    setTesting(false);
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
        <div style={{display:'flex',gap:8}}>
          <button onClick={handleTest} disabled={testing} style={{padding:'8px 16px',border:'1px solid #4a90d9',color:'#4a90d9',background:'white',borderRadius:4,cursor:'pointer',fontSize:14}}>{testing?'测试中...':'测试连接'}</button>
          <button onClick={handleSave} style={{background:'#4a90d9',color:'white',border:'none',padding:'8px 24px',borderRadius:4,fontSize:14,cursor:'pointer'}}>保存</button>
        </div>
        {message && <div style={{padding:'8px 12px',borderRadius:4,background:message.includes('成功')?'#dfd':'#fdd',color:message.includes('成功')?'#272':'#c33',fontSize:13}}>{message}</div>}
      </div>
    </div>
  );
}
