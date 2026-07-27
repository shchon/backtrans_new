from backtranslate.srt.parser import parse_srt
from backtranslate.srt.pairing import pair_by_index, pair_by_timecode


class SrtService:
    @staticmethod
    def parse(content: str) -> list[dict]:
        return parse_srt(content)

    @staticmethod
    def parse_file(filepath: str) -> list[dict]:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            return parse_srt(f.read())

    @staticmethod
    def pair_by_index(chinese: list, english: list) -> list[tuple]:
        return pair_by_index(chinese, english)

    @staticmethod
    def pair_by_timecode(chinese: list, english: list) -> list[tuple]:
        return pair_by_timecode(chinese, english)
