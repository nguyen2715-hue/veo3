
# Minimal soft-Telex IME fallback for Vietnamese.
# Applies transforms on the last syllable when user types spaces/punctuations.
# Supports: dd->đ, aw->ă, aa->â, ee->ê, oo->ô, ow->ơ, uw->ư; tone: s,f,r,x,j.
import re

VOWELS = "aăâeêioôơuưyAĂÂEÊIOÔƠUƯY"
TONE_MAP = {
    '': 0, 's': 1, 'f': 2, 'r': 3, 'x': 4, 'j': 5,
    'S': 1, 'F': 2, 'R': 3, 'X': 4, 'J': 5
}
# base -> [level0, level1, level2, level3, level4, level5]
ACCENT_TABLE = {
    'a': ['a','á','à','ả','ã','ạ'], 'ă': ['ă','ắ','ằ','ẳ','ẵ','ặ'], 'â': ['â','ấ','ầ','ẩ','ẫ','ậ'],
    'e': ['e','é','è','ẻ','ẽ','ẹ'], 'ê': ['ê','ế','ề','ể','ễ','ệ'],
    'i': ['i','í','ì','ỉ','ĩ','ị'],
    'o': ['o','ó','ò','ỏ','õ','ọ'], 'ô': ['ô','ố','ồ','ổ','ỗ','ộ'], 'ơ': ['ơ','ớ','ờ','ở','ỡ','ợ'],
    'u': ['u','ú','ù','ủ','ũ','ụ'], 'ư': ['ư','ứ','ừ','ử','ữ','ự'],
    'y': ['y','ý','ỳ','ỷ','ỹ','ỵ'],
    'A': ['A','Á','À','Ả','Ã','Ạ'], 'Ă': ['Ă','Ắ','Ằ','Ẳ','Ẵ','Ặ'], 'Â': ['Â','Ấ','Ầ','Ẩ','Ẫ','Ậ'],
    'E': ['E','É','È','Ẻ','Ẽ','Ẹ'], 'Ê': ['Ê','Ế','Ề','Ể','Ễ','Ệ'],
    'I': ['I','Í','Ì','Ỉ','Ĩ','Ị'],
    'O': ['O','Ó','Ò','Ỏ','Õ','Ọ'], 'Ô': ['Ô','Ố','Ồ','Ổ','Ỗ','Ộ'], 'Ơ': ['Ơ','Ớ','Ờ','Ở','Ỡ','Ợ'],
    'U': ['U','Ú','Ù','Ủ','Ũ','Ụ'], 'Ư': ['Ư','Ứ','Ừ','Ử','Ữ','Ự'],
    'Y': ['Y','Ý','Ỳ','Ỷ','Ỹ','Ỵ'],
}
def _core_marks(s):
    # dd->đ ; DD->Đ
    s = re.sub(r'(?<!\w)dd', 'đ', s)
    s = re.sub(r'(?<!\w)DD', 'Đ', s)
    # aw/aa, ee, oo, ow, uw
    s = s.replace('aw','ă').replace('Aw','Ă').replace('AW','Ă')
    s = s.replace('aa','â').replace('Aa','Â').replace('AA','Â')
    s = s.replace('ee','ê').replace('Ee','Ê').replace('EE','Ê')
    s = s.replace('oo','ô').replace('Oo','Ô').replace('OO','Ô')
    s = s.replace('ow','ơ').replace('Ow','Ơ').replace('OW','Ơ')
    s = s.replace('uw','ư').replace('Uw','Ư').replace('UW','Ư')
    return s

def _apply_tone(s):
    # find tone key at end (s,f,r,x,j)
    m = re.search(r'([sfrxjSFRXJ])$', s)
    if not m:
        return s
    tone_key = m.group(1)
    tone = TONE_MAP.get(tone_key, 0)
    s_base = s[:-1]
    # place tone on the rightmost vowel, prefer â/ă/ê/ô/ơ/ư if present
    for pos in range(len(s_base)-1, -1, -1):
        ch = s_base[pos]
        if ch in VOWELS and ch in ACCENT_TABLE:
            repl = ACCENT_TABLE[ch][tone]
            return s_base[:pos] + repl + s_base[pos+1:]
    return s  # fallback

def transform_last_token(text):
    # apply only on last token (letters inside [\w] and diacritics)
    parts = re.split(r'(\s+)', text)
    if not parts:
        return text
    last = parts[-1]
    if re.fullmatch(r'[\wăâêôơưĂÂÊÔƠƯ]+', last, re.IGNORECASE):
        token = _apply_tone(_core_marks(last))
        parts[-1] = token
        return ''.join(parts)
    return text
