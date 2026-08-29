BASE_ONLY = '<div type="juan"><p>學而時習之不亦說乎</p></div>'

BASE_WITH_COMM = (
    '<div type="juan"><p>學而時習之'
    '<note type="comm">說音悅</note>'
    "不亦說乎</p></div>"
)
GAIJI_PB = '<div type="juan"><p>君子<pb n="1a"/>曰學</p></div>'

GOLD_BASE_INSERTIONS = [
    {"afterHan": 4, "mark": "，", "left": "之", "occurrence": 1},
    {"afterHan": 8, "mark": "。", "left": "乎", "occurrence": 1},
]

GOLD_COMM_INSERTIONS = [
    {"afterHan": 1, "mark": "，", "left": "音", "occurrence": 1},
]
