from backtranslate.srt.pairing import pair_by_index, pair_by_timecode


def make_entry(index, start, end, text):
    return {"index": index, "start": start, "end": end, "text": text}


def test_pair_by_index_equal_lengths():
    ch_list = [make_entry(1, 0, 0, "你好"), make_entry(2, 0, 0, "再见")]
    en_list = [make_entry(1, 0, 0, "Hello"), make_entry(2, 0, 0, "Goodbye")]
    result = pair_by_index(ch_list, en_list)
    assert len(result) == 2
    assert result[0][0]["text"] == "你好"
    assert result[0][1]["text"] == "Hello"
    assert result[1][0]["text"] == "再见"
    assert result[1][1]["text"] == "Goodbye"


def test_pair_by_index_mismatched_lengths():
    ch_list = [make_entry(1, 0, 0, "你好"), make_entry(2, 0, 0, "再见"), make_entry(3, 0, 0, "谢谢")]
    en_list = [make_entry(1, 0, 0, "Hello"), make_entry(2, 0, 0, "Goodbye")]
    result = pair_by_index(ch_list, en_list)
    assert len(result) == 2


def test_pair_by_timecode_overlap():
    ch_list = [
        make_entry(1, 1000, 3000, "你好"),
        make_entry(2, 4000, 6000, "再见"),
    ]
    en_list = [
        make_entry(1, 1200, 2800, "Hello"),
        make_entry(2, 4100, 5900, "Goodbye"),
    ]
    result = pair_by_timecode(ch_list, en_list)
    assert len(result) == 2
    assert result[0][0]["text"] == "你好"
    assert result[0][1]["text"] == "Hello"


def test_pair_by_timecode_no_overlap():
    ch_list = [make_entry(1, 1000, 2000, "你好")]
    en_list = [make_entry(1, 3000, 4000, "Hello")]
    result = pair_by_timecode(ch_list, en_list)
    assert len(result) == 0


def test_pair_by_index_empty_lists():
    assert pair_by_index([], []) == []


def test_pair_by_timecode_empty_lists():
    assert pair_by_timecode([], []) == []
