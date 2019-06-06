#!/usr/bin/env python3.6
"""Helper functions.

Attributes:
    ASCII_SYMBOLS (set): Valid input symbols. Everything else is str_ripped.
    ASCII_SYMBOLS_FIX (TYPE): Workaround for Telegram's autoreplace "feature".
    UNICODE_SYMBOLS (TYPE): Prettify the output
"""

ASCII_SYMBOLS = {'?', '+', '-'}
ASCII_SYMBOLS_FIX = {
    '—': '--'
}
UNICODE_SYMBOLS = {
    '?' : '❔',
    '+' : '✅',
    '-' : '❌',
    '0' : '0️⃣',
    '1' : '1️⃣',
    '2' : '2️⃣',
    '3' : '3️⃣',
    '4' : '4️⃣',
    '5' : '5️⃣',
    '6' : '6️⃣',
    '7' : '7️⃣',
    '8' : '8️⃣',
    '9' : '9️⃣',
    '10': '🔟',
    '-1': '🚫'
}

def fix(str_):
    """Workaround for Telegram's autoreplace "feature".
    
    Args:
        str_ (str): The string to fix.
    
    Returns:
        str: The fixed string.
    """
    for err in ASCII_SYMBOLS_FIX:
        str_ = str_.replace(err, ASCII_SYMBOLS_FIX[err])
    return str_

def reduce(str_, length):
    """Strip everything that is not a valid input character and cuts/ pads to correct length.
    
    Args:
        str_ (str): The raw input.
        length (int): The length for cutting/ padding.
    
    Returns:
        str: The cleaned-up string.
    """
    str_ = fix(str_)
    out = ''
    for char in str_:
        if char in ASCII_SYMBOLS:
            out = out + char
        if len(out) == length:
            break
    while len(out) < length:
        out = out + '?'
    return out

def parse(str_):
    """Prettify output.
    
    Args:
        str_ (str): The raw input
    
    Returns:
        str: Unicode symbol representation of input.
    """
    out = ''
    for char in str_:
        out += UNICODE_SYMBOLS.get(str(char), '♾')
    return out

def markdown_safe(str_):
    """Replace any character that might make Telegram's markdown parser unhappy.
    
    Args:
        str_ (str): String to make markdown safe.
    
    Returns:
        str: Markdown safe version of input string.
    """
    str_ = str_.replace('_', '\\_')
    str_ = str_.replace('*', '\\*')
    str_ = str_.replace('`', '\\`')
    return str_

def html_safe(str_):
    """Replace any character that might make Telegram's html parser unhappy.
    
    Args:
        str_ (str): String to make html safe.
    
    Returns:
        str: html safe version of input string.
    """
    str_ = str_.replace('<', '&lt;')
    str_ = str_.replace('>', '&gt;')
    str_ = str_.replace('&', '&amp;')
    return str_
