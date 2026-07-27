import type { SrtEntry } from './parser';

export function pairByIndex(chinese: SrtEntry[], english: SrtEntry[]): [SrtEntry, SrtEntry][] {
  const n = Math.min(chinese.length, english.length);
  const pairs: [SrtEntry, SrtEntry][] = [];
  for (let i = 0; i < n; i++) {
    pairs.push([chinese[i], english[i]]);
  }
  return pairs;
}

export function pairByTimecode(chinese: SrtEntry[], english: SrtEntry[]): [SrtEntry, SrtEntry][] {
  const pairs: [SrtEntry, SrtEntry][] = [];
  let enIdx = 0;
  for (const ch of chinese) {
    while (enIdx < english.length && english[enIdx].end <= ch.start) {
      enIdx++;
    }
    if (enIdx < english.length && english[enIdx].start < ch.end) {
      pairs.push([ch, english[enIdx]]);
      enIdx++;
    }
  }
  return pairs;
}
