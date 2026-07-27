declare module 'sql.js' {
  interface ExecResult {
    columns: string[];
    values: unknown[][];
  }

  class Database {
    run(sql: string, params?: unknown[]): Database;
    exec(sql: string, params?: unknown[]): ExecResult[];
  }

  interface SqlJsStatic {
    Database: typeof Database;
  }

  export { Database };
  export type { Database as SqlJsDatabase };
  export default function initSqlJs(config?: { locateFile: (file: string) => string }): Promise<SqlJsStatic>;
}
