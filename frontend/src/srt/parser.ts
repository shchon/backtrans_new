export interface SrtEntry {
  index: number;
  start: number;
  end: number;
  text: string;
}

function timestampToMs(ts: string): number {
  const [h, m, rest] = ts.split(':');
  const [s, ms] = rest.split(',');
  return Number(h) * 3600000 + Number(m) * 60000 + Number(s) * 1000 + Number(ms);
}

function stripTags(text: string): string {
  return text.replace(/<[^>]+>/g, '');
}

export function parseSrt(content: string): SrtEntry[] {
  let cleaned = content;
  if (cleaned.charCodeAt(0) === 0xFEFF) cleaned = cleaned.slice(1);
  cleaned = cleaned.replace(/\r\n/g, '\n');
  if (!cleaned.trim()) return [];

  const blocks = cleaned.trim().split(/\n\n+/).map(b => b.trim()).filter(Boolean);
  const result: SrtEntry[] = [];
  const pattern = /^(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]+)$/m;

  for (const block of blocks) {
    const m = block.match(pattern);
    if (!m) continue;
    result.push({
      index: Number(m[1]),
      start: timestampToMs(m[2]),
      end: timestampToMs(m[3]),
      text: stripTags(m[4].trim()),
    });
  }
  return result;
}
