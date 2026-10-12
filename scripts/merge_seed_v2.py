import json, glob, re, hashlib, datetime, os
from urllib.parse import urlparse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data/clean/blogs.jsonl'); OUT = os.path.join(ROOT, 'data/clean/blogs_merged.jsonl')
REP = os.path.join(ROOT, 'docs/merge_report.md')
norm = lambda u: u.strip().rstrip('/').lower().replace('http://', 'https://')
recs = [json.loads(l) for l in open(SRC, encoding='utf-8')]
by_url = {norm(r['source_url']): r for r in recs}
added, skipped = [], []
for f in sorted(glob.glob(os.path.join(ROOT, 'data/seed_v2_web/*/*.txt'))):
    raw = open(f, encoding='utf-8').read()
    head, _, body = raw.partition('\n\n')
    h = dict(re.findall(r'^(SOURCE|TITLE|LOSS|LANGUAGE|EXTRACTION):\s*(.*)$', head, re.M))
    url = h.get('SOURCE', '').split(' ')[0]
    fname = os.path.basename(f)
    if norm(url) in by_url:
        by_url[norm(url)]['reuse_notes'] = (by_url[norm(url)].get('reuse_notes') or '') + f' | also in seed v2 as {fname}'
        skipped.append((fname, url)); continue
    lang = 'devanagari_hindi' if fname.startswith('hi_') and 'roman' not in h.get('LANGUAGE', '').lower() else ('romanized_hindi' if fname.startswith('hi_') else 'english')
    words = len(body.split())
    rid = 'blogs:cw_' + hashlib.sha1(url.encode()).hexdigest()[:12]
    flags = []
    if words > 5000: flags.append('length_outlier_gt5000w')
    if fname.startswith(('hi_018', 'en_019')): flags.append('same_author_pair')
    rec = {k: None for k in recs[0].keys()}
    rec.update(dict(record_id=rid, platform='web', genre='blog_or_personal_essay', source_url=url, source_record_id=rid.split(':')[1],
        collected_at=datetime.datetime(2026, 9, 16, tzinfo=datetime.timezone.utc).isoformat(), thread_id=urlparse(url).netloc.replace('www.', ''),
        author_group='au_' + hashlib.sha1(urlparse(url).netloc.encode()).hexdigest()[:10], text_original=body.strip(), text_clean=body.strip(),
        lang_provisional=lang, n_words=words, message_type_provisional='personal_disclosure', message_type_source='search tool after opening page (not human)',
        eligibility_status='provisionally_eligible', exclusion_reason=None, retrieval_route='seed v2 (WebFetch verbatim, 2026-09-16)',
        duplicate_group=rid, reuse_notes='copyright of author/site; local analysis copy; do not redistribute text', flags=flags, review_status='no_human_review',
        extra={'title': h.get('TITLE'), 'deceased_relation_as_stated': h.get('LOSS'), 'seed_file': fname, 'language_note': h.get('LANGUAGE')}, dedup_key=norm(url)))
    recs.append(rec); by_url[norm(url)] = rec; added.append((fname, url, lang, words))
with open(OUT, 'w', encoding='utf-8') as fo:
    for r in recs: fo.write(json.dumps(r, ensure_ascii=False) + '\n')
from collections import Counter
el = [r for r in recs if r['eligibility_status'] == 'provisionally_eligible']
c = Counter(r['lang_provisional'] for r in el); w = Counter()
for r in el: w[r['lang_provisional']] += r['n_words']
with open(REP, 'w', encoding='utf-8') as fo:
    fo.write(f"# Merge report ({datetime.date.today()})\n\nOriginal blogs.jsonl: 103 records. seed v2: 52 texts. Overlap (skipped): {len(skipped)}. Added: {len(added)}.\n\n")
    fo.write("## Provisionally eligible after merge\n\n| language | docs | words |\n|---|---:|---:|\n")
    for k in c: fo.write(f"| {k} | {c[k]} | {w[k]} |\n")
    fo.write("\n## Added\n\n| file | lang | words | url |\n|---|---|---:|---|\n")
    for fn, u, l, n in added: fo.write(f"| {fn} | {l} | {n} | {u} |\n")
    fo.write("\n## Skipped (already present)\n\n" + "\n".join(f"- {fn} = {u}" for fn, u in skipped) + "\n")
print(f"added {len(added)}, skipped {len(skipped)}; eligible now:", dict(c))
