def pair_by_index(chinese_list: list[dict], english_list: list[dict]) -> list[tuple[dict, dict]]:
    """Pair by sequential index. Stops at the shorter list length."""
    return [(chinese_list[i], english_list[i]) for i in range(min(len(chinese_list), len(english_list)))]


def pair_by_timecode(chinese_list: list[dict], english_list: list[dict]) -> list[tuple[dict, dict]]:
    """Pair subtitles with overlapping time ranges.

    Both lists must be sorted by start time. Assumes 1:1 pairing;
    one-to-many or many-to-one overlaps may result in dropped entries.
    """
    pairs = []

    ci = 0
    ei = 0
    while ci < len(chinese_list) and ei < len(english_list):
        ch = chinese_list[ci]
        en = english_list[ei]

        overlap_start = max(ch["start"], en["start"])
        overlap_end = min(ch["end"], en["end"])

        if overlap_start < overlap_end:
            pairs.append((ch, en))
            ci += 1
            ei += 1
        elif ch["start"] < en["start"]:
            ci += 1
        else:
            ei += 1

    return pairs
