"""Full-text validation and safe XML field edits; no medical-certification claims."""
from __future__ import annotations
import hashlib,re,unicodedata,xml.etree.ElementTree as ET
from collections import Counter

FORMAT_PATTERNS=(r'\\n',r'\{[^}]*\}',r'%[0-9.]*[sdf]',r'</?(?:b|i|color|size|br)(?:=[^>]+|\s[^>]*)?/?>')
NUMBERS=r'\d+(?:[.,]\d+)?'
ALLOWED={
    'en':{'text'},'nih_en':{'text','@disease'},
    'node':{'@name','@text'},'qv':{'@full','@short'},'prompt':{'text'},
    'region':{'@name'},'action':{'@name'},'view':{'@name'},
    'movie':{'@full','@short','@name','@title','@description'},
    'pack':{'@full','@short','@name','@title','@description'},
    'iap':{'@title','@description','@name'},'text':{'text'}
}

def validate_unit(source,target):
    if target.get('unit_id')!=source['unit_id']:raise ValueError('Unit identity mismatch')
    original=source['en']; hu=target.get('hu')
    if not isinstance(hu,str) or not hu.strip():raise ValueError('Missing/empty translation')
    if hu!=unicodedata.normalize('NFC',hu):raise ValueError('Translation must use NFC')
    if any(ord(c)<32 and c not in '\n\r\t' or c in '\ufffe\uffff' for c in hu):raise ValueError('Invalid XML character')
    for pattern in FORMAT_PATTERNS:
        if Counter(re.findall(pattern,original))!=Counter(re.findall(pattern,hu)):raise ValueError('Formatting/placeholder token mismatch')
    warnings=[]
    if Counter(re.findall(NUMBERS,original))!=Counter(re.findall(NUMBERS,hu)):warnings.append('numeric-content-changed')
    if original==hu:
        if re.search(r'\b(?:the|and|this|that|with|without|select|artery|vein|nerve|bone|muscle)\b',original,re.I):raise ValueError('Untranslated English text')
        warnings.append('unchanged-text-needs-Latin-or-proper-name-review')
    if re.search(r"\b(?:not|no|without|never|cannot|doesn't|isn't)\b",original,re.I) and not re.search(r'\b(?:nem|nincs|nincsen|nincsenek|ne|soha|semm|nélkül)',hu,re.I):
        warnings.append('negation-needs-review')
    return warnings

def apply_unit_corrections(units,targets,corrections):
    """Apply parent-approved draft changes, never rewriting the audited worker files."""
    import copy
    source={u['unit_id']:u for u in units};result=copy.deepcopy(targets);dest={t['unit_id']:t for t in result};seen=set()
    for e in corrections.get('entries',[]):
        ident=e['unit_id']
        if ident in seen or ident not in source or e.get('approved') is not True or not e.get('evidence'):
            raise ValueError('Duplicate/unknown/unapproved/unsupported correction')
        seen.add(ident)
        if hashlib.sha256(source[ident]['en'].encode()).hexdigest()!=e['source_en_sha256']:raise ValueError('Correction source baseline changed')
        if ident not in dest:continue # An explicitly partial collection may not include this finished unit yet.
        old=dest[ident]['hu']
        if hashlib.sha256(old.encode()).hexdigest()!=e['expected_hu_sha256']:raise ValueError('Correction translation baseline changed')
        new=old
        for replacement in e['replacements']:
            a,b=replacement['old'],replacement['new']
            if not a or new.count(a)!=1:raise ValueError('Correction phrase is missing or ambiguous')
            new=new.replace(a,b,1)
        if new==old:raise ValueError('No-op correction')
        validate_unit(source[ident],{'unit_id':ident,'hu':new})
        dest[ident]['hu']=new
    return result


def materialize_fields(units,translations):
    src={u['unit_id']:u for u in units}; dst={t['unit_id']:t for t in translations}
    if len(src)!=len(units) or len(dst)!=len(translations) or set(src)!=set(dst):raise ValueError('Incomplete/duplicate/extra unit coverage')
    fields={}; warnings=[]
    for ident,u in src.items():
        flags=validate_unit(u,dst[ident])
        if flags:warnings.append({'unit_id':ident,'flags':flags})
        for key in u['keys']:
            if key in fields:raise ValueError('Duplicate field identity')
            fields[key]=dst[ident]['hu']
    return fields,warnings

def walk(node,route='0'):
    yield node,route
    for i,child in enumerate(node):yield from walk(child,route+'.'+str(i))

def snapshot(root):
    return {route:(n.tag,dict(n.attrib),n.text,n.tail) for n,route in walk(root)}

def edit_xml_fields(source_script,entries,translations,expected_script_hash=None):
    if expected_script_hash and hashlib.sha256(source_script.encode('utf-8','surrogateescape')).hexdigest()!=expected_script_hash:
        raise ValueError('Source script hash mismatch')
    root=ET.fromstring(source_script); nodes={route:n for n,route in walk(root)}; original=snapshot(root); allowed_changes={}
    for entry in entries:
        key=entry['key']; route=entry['node_route']; field=entry['field']; tag=entry['tag']
        if route not in nodes or nodes[route].tag!=tag or field not in ALLOWED.get(tag,set()):raise ValueError('Unauthorized field or wrong XML route')
        if (route,field) in allowed_changes:raise ValueError('Duplicate field edit')
        node=nodes[route]
        before=node.text if field=='text' else node.attrib.get(field[1:])
        if before!=entry['en']:raise ValueError('Stale source text')
        if key not in translations:raise ValueError('Missing field translation')
        target=translations[key]
        # Here warnings are retained by the unit validator; exact formatting failures still refuse edits.
        validate_unit({'unit_id':key,'en':before},{'unit_id':key,'hu':target})
        if field=='text':node.text=target
        else:node.attrib[field[1:]]=target
        allowed_changes[(route,field)]=target
    result='<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='unicode')
    parsed=ET.fromstring(result); after=snapshot(parsed)
    if set(after)!=set(original):raise ValueError('XML node structure changed')
    for route,(tag,attrs,text,tail) in original.items():
        tag2,attrs2,text2,tail2=after[route]
        if tag2!=tag or tail2!=tail or set(attrs2)!=set(attrs):raise ValueError('XML schema/program data changed')
        if text2!=allowed_changes.get((route,'text'),text):raise ValueError('Unrequested text changed')
        for attr,value in attrs.items():
            if attrs2[attr]!=allowed_changes.get((route,'@'+attr),value):raise ValueError('Unrequested attribute changed')
    return result
