import { useState, useEffect } from 'react';
import { initDatabase } from './db/index';
import LearnPage from './pages/LearnPage';
import ReviewPage from './pages/ReviewPage';
import FavoritesPage from './pages/FavoritesPage';
import ExpressionsPage from './pages/ExpressionsPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

type Page = 'learn' | 'review' | 'favorites' | 'expressions' | 'settings';

const NAV_ITEMS: {key: Page; label: string}[] = [
  {key: 'learn', label: '学习'},
  {key: 'review', label: '复盘'},
  {key: 'favorites', label: '收藏夹'},
  {key: 'expressions', label: '表达库'},
  {key: 'settings', label: '设置'},
];

export default function App() {
  const [page, setPage] = useState<Page>('learn');
  const [reviewSessionId, setReviewSessionId] = useState<number | null>(null);
  const [pendingLearnSessionId, setPendingLearnSessionId] = useState<number | null>(null);
  const [dbReady, setDbReady] = useState(false);

  useEffect(() => {
    initDatabase().then(() => setDbReady(true)).catch(console.error);
  }, []);

  if (!dbReady) {
    return <div style={{display:'flex',justifyContent:'center',alignItems:'center',height:'100vh',color:'#999'}}>初始化中...</div>;
  }

  return (
    <div className="app-layout">
      <nav className="sidebar">
        {NAV_ITEMS.map(item => (
          <button
            key={item.key}
            className={`nav-btn ${page === item.key ? 'active' : ''}`}
            onClick={() => setPage(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <main className="content">
        {page === 'learn' && (
          <LearnPage
            onNavigateToReview={(sid) => { setReviewSessionId(sid); setPage('review'); }}
            pendingSessionId={pendingLearnSessionId}
          />
        )}
        {page === 'review' && <ReviewPage sessionId={reviewSessionId} />}
        {page === 'favorites' && (
          <FavoritesPage
            onStartReview={(sid) => { setPendingLearnSessionId(sid); setPage('learn'); }}
          />
        )}
        {page === 'expressions' && <ExpressionsPage />}
        {page === 'settings' && <SettingsPage />}
      </main>
    </div>
  );
}
