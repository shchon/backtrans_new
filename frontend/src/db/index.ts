import initSqlJs, { Database as SqlJsDatabase } from 'sql.js';
import { CREATE_TABLES_SQL } from './schema';

let db: SqlJsDatabase | null = null;

export async function initDatabase(): Promise<void> {
  const SQL = await initSqlJs({
    locateFile: (file: string) => `https://sql.js.org/dist/${file}`,
  });
  db = new SQL.Database();
  db.run(CREATE_TABLES_SQL);
}

export function getDb(): SqlJsDatabase {
  if (!db) throw new Error('Database not initialized');
  return db;
}
