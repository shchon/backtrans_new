import initSqlJs, { Database as SqlJsDatabase } from 'sql.js';
import { CREATE_TABLES_SQL } from './schema';

const STORAGE_KEY = 'backtranslate_db';

let db: SqlJsDatabase | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function dbToBase64(): string {
  const data = (db! as unknown as { export: () => Uint8Array }).export();
  const bytes = new Uint8Array(data);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToDb(base64: string): Uint8Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function saveDatabase(): void {
  if (!db) return;
  try {
    localStorage.setItem(STORAGE_KEY, dbToBase64());
  } catch (e) {
    console.error('Failed to save database', e);
  }
}

export function persistDatabase(): void {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(saveDatabase, 500);
}

export async function initDatabase(): Promise<void> {
  const SQL = await initSqlJs({
    locateFile: (file: string) => `/${file}`,
  });

  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && saved.length > 10) {
    try {
      db = new (SQL.Database as unknown as new (data: Uint8Array) => SqlJsDatabase)(base64ToDb(saved));
    } catch (e) {
      console.error('Failed to load saved database, creating new', e);
      db = new SQL.Database();
      db.run(CREATE_TABLES_SQL);
    }
  } else {
    db = new SQL.Database();
    db.run(CREATE_TABLES_SQL);
  }

  // Wrap db.run to auto-persist after every write
  const origRun = db.run.bind(db);
  db.run = function(sql: string, params?: unknown[]) {
    const result = origRun(sql, params);
    persistDatabase();
    return result;
  } as typeof db.run;

  // Also save on page unload
  window.addEventListener('beforeunload', () => saveDatabase());
}

export function getDb(): SqlJsDatabase {
  if (!db) throw new Error('Database not initialized');
  return db;
}
