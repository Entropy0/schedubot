#!/usr/bin/env python3.6

ascii_symbols = { '?', '+', '-'}
ascii_symbols_fix = {
    '—': '--'
}
unicode_symbols = {
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
   '10': '🔟'
}

def fix(st):
    for e in ascii_symbols_fix:
        st = st.replace(e, ascii_symbols_fix[e])
    return st

def reduce(st, l):
    st = fix(st)
    out = ''
    for c in st:
        if(c in ascii_symbols):
            out = out + c
        if(len(out) == l):
            break
    while(len(out) < l):
        out = out + '?'
    return out

def parse(st):
    out = ''
    for c in st:
        out += unicode_symbols.get(str(c), '🚫')
    return out