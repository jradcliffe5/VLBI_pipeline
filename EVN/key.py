## A python parser for SCHED's "keyin" files.
## 
## Syntax:
## !.*$ defines comments.
## KEY "=" VAL
## KEY VAL "the equals sign is optional so long as its absence doesn't lead to ambiguity"

## (1) Keys no longer than 8 chars(!)
## (1a) Except when they are ("overwrite" in first line of SCHED key files).
## (2) Keys are _not_ case sensitive(!) (normalise to GREAT RUNES in honour of FORTRAN
##     Alphabet for keywords?  [A-Za-z]*
## (3) Values are not case sensitive, except when they are. (E.g., unix paths.)
## (4) Values may be comma-separated lists ("arrays")
## (5) Values may be numbers or "character string".
## (6) Values are doubles.
## (7) Values may be expressions. (E.g., "5.5*4")
## (8) hh:mm:ss.ss dd:mm:ss.ss (no embedded blanks or signs; "2:40" is allowed and equal to "160")
## (9) Value may be blank ("").
## Entries terminated by "/"

import math, re, sys, logging

def s_err(scanner, error):
    raise RuntimeError, "line: %d", scanner.line_no

def s_keyword(scanner, token):
    if len(token) > 9 or '.' in token:
        res = ('value', token)
    else:
        res = ('key', token.upper())
    return res

def s_newline(scanner, token):
    scanner.line_no += 1
    return None

def s_quote(scanner, token):
    return ('quote', token[1:-1])

def s_number(scanner, token):
    return ('number', float(token))

def s_angle(scanner, token): # also time
    l = token.split(":")
    ## It's not python to use reduce.
    ## But I neither remember nor care what is.
    val = reduce(lambda acc, x: 60*acc+math.copysign(acc, float(x)), l, 0.0) 
    return ('number', val)

def s_value(scanner, token):
    return ('value', token)

def s_string(scanner, token):
    return ('value', token)

def s_misc(scanner, token):
    logging.debug("Misc token %s at line %d" % (str(token), scanner.line_no))
    return ('misc', token)

def s_comment(scanner, token): # was only used for debugging.
    scanner.line_no += 1
    return ('comment', token)

scanner = re.Scanner([
    ("\!.*\n", s_newline),
    ("[ \t]+", None),
    ("\n", s_newline),
    ("\r\n", s_newline),
    ("=", lambda s, t: ('equal',)),
    ("'[^'\n]*'", s_quote), 
    ("\"[^'\n]*\"", s_quote), # Sigh.  Double quotes used in freq.dat
    ("/", lambda s, t: ('end_chunk',)),
    (",", lambda s, t: ('comma',)),
    ("[+-]?[0-9]+:[0-9]+:[0-9]+(.[0-9]*)?", s_angle),
    ("[+-]?[0-9]+:[0-9]+(.[0-9]*)?", s_angle),
    ("[+-]?[0-9]*\.[0-9]+([Ee][+-][0-9]{1,3})?(?![A-Za-z_0-9()])", s_number),
    ("[+-]?[0-9]+\.?(?![A-Za-z_0-9()])", s_number),
    ## apparently parens and unquoted minus signs are allowed in keywords?
    ("[A-Za-z.0-9]([()A-Za-z_0-9._+-]+)?", s_keyword), 
    (".*", s_misc)
])

# Now have everything except arithmetic expressions.
# Which I don't actually want to support, I don't think.

## Parser!
## I could use one of those new-fangled 'objects' instead of a global lookahead.
## In principle.

def p_all():
    global tok
    chunks = []
    try:
        while True:
            if tok=='EOF':break
            chunks.append(p_chunk())
    except StopIteration:
        pass
    return chunks

def p_chunk():
    global tok
    entries = []
    while tok[0] != 'end_chunk':
        entries.append(p_item())
    logging.debug("p_chunk %s", str(tok))
    tok = tokIt.next()
    return entries

def p_item():
    global tok
    lhs = p_key()
    if tok==('equal',):
        logging.debug("p_item %s", str(tok))
        tok = tokIt.next()
        rhs = p_rhs()
    elif tok[0] in ['value', 'quote', 'number']:
        rhs = p_rhs()
    else:
        rhs = True # for unitary expressions.
    return (lhs, rhs)

def p_key():
    global tok
    logging.debug("p_key: %s", str(tok))
    if tok[0] == 'key':
        res = tok
        tok = tokIt.next()
    else:
        raise RuntimeError, "Expected key token, got %s" % str(tok)
    return res[1]

def p_rhs():
    global tok
    val = p_value()
    rhs = [val]
    while tok == ('comma',):
        logging.debug("p_rhs: %s", str(tok))
        tok = tokIt.next()
        rhs.append(p_value()) # p_value advances tok beyond the value.
    if len(rhs)==1:
        rhs = rhs[0]
    return rhs

def p_value():
    global tok
    if tok[0] not in ['value', 'quote', 'number', 'key']:
        raise RuntimeError, "Unexpected RHS token %s" % str(tok)
    val = tok
    logging.debug("p_value: %s", str(val))
    tok = tokIt.next()
    return val[1]

def print_tree(res):
    logging.debug("Result: %s", str(res))
    all_chunks_text = []
    for chunk in res:
        chunk_text = []
        for (k, v) in chunk:
            logging.debug("%s %s", str(k), str(v))
            e_text = "\t%s : %s" % (repr(k), repr(v))
            j_text = re.sub("'", '"', e_text)
            chunk_text.append(j_text)
        logging.debug("Rendered: %s", chunk_text)
        all_chunks_text.append("\t{\n%s\n\t}" % (",\n".join(chunk_text)))
    logging.debug("All: %s", all_chunks_text)
    contents = ",\n".join(all_chunks_text)
    logging.debug("Contents: %s", contents)
    print "[\n%s\n]\n" % contents

scanner.line_no = 0

def read_keyfile(f):
    global tok, tokIt
    scanner.line_no = 0
    try:
        res = scanner.scan(f.read())
        if res[1]!='':
            raise RuntimeError, "Unparsed text: %s." % (res[1][:20])
        tokIt = iter(res[0]+['EOF'])
        try: 
            tok = tokIt.next()
            res = p_all()
        except StopIteration: # empty file
            res = ''
    except RuntimeError, txt:
        print >>sys.stderr, "line %d:  %s" % (scanner.line_no, txt)
        raise RuntimeError
    return res

def process_file(f):
    res = read_keyfile(f)
    print_tree(res)


if __name__=="__main__":
    import sys, logging
    logging.basicConfig(filename='example.log', level=logging.DEBUG)
    logging.debug("Srsly you guys")
    process_file(file(sys.argv[1]))
    
## for i in  /export/jive/small/LocalProjects/WorkingCopies/sched-current/catalogs/sources.*; 
## do python key.py $i > $(basename $i).json; 
## done
