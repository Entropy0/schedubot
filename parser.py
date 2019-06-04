#!/usr/bin/env python3.6

ASCII_SYMBOLS = {'?', '+', '-'}
ASCII_SYMBOLS_FIX = {
    '—': '--'
}
UNICODE_SYMBOLS = {
    '?': '❔',
    '+': '✅',
    '-': '❌',
    '0': '0️⃣',
    '1': '1️⃣',
    '2': '2️⃣',
    '3': '3️⃣',
    '4': '4️⃣',
    '5': '5️⃣',
    '6': '6️⃣',
    '7': '7️⃣',
    '8': '8️⃣',
    '9': '9️⃣',
   '10': '🔟',
   '-1': '🚫'
}

def fix(st):
    for e in ASCII_SYMBOLS_FIX:
        st = st.replace(e, ASCII_SYMBOLS_FIX[e])
    return st

def reduce(st, l):
    st = fix(st)
    out = ''
    for c in st:
        if c in ASCII_SYMBOLS:
            out = out + c
        if len(out) == l:
            break
    while len(out) < l:
        out = out + '?'
    return out

def parse(st):
    out = ''
    for c in st:
        out += UNICODE_SYMBOLS.get(str(c), '♾')
    return out
