import json, re, csv
import pandas as pd

LANGUAGES = ['english', 'hinglish']
LABELS = {4: 'Correct', 3: 'Partial', 2: 'Wrong', 1: 'Refused', 0: 'Hallucinated'}
SCHOOLS = ['hanafi', 'shafi', 'maliki', 'hanbali']
# common Hindi/Urdu function words; used to check whether a reply to a
# Hinglish prompt was itself written in Hinglish
HINGLISH_WORDS = {'hai', 'hain', 'ke', 'ki', 'ka', 'mein', 'nahi', 'kya', 'liye', 'se', 'aur', 'hota', 'jata'}

# ── LOAD FILES ──────────────────────────────────────────────────────────
with open('ground_truth.json') as f:
    ground_truth = {g['id']: g for g in json.load(f)['ground_truth']}
with open('results/scores.json') as f:
    scores = json.load(f)


def is_hinglish(text):
    words = re.findall(r'[a-z]+', text.lower())
    return sum(w in HINGLISH_WORDS for w in words) / max(len(words), 1) > 0.08


def is_incoherent(note):
    """Incoherent / looping outputs, as flagged in the reviewer notes."""
    return bool(re.search(r'incoherent|degenerat|repetition', note, re.I))


def is_misread(note):
    return bool(re.search(r'misunderst|misreads|different question|off-topic', note, re.I))


scored = []
for lang in LANGUAGES:
    with open(f'results/raw_responses_{lang}.json') as f:
        responses = json.load(f)['results']
    for r in responses:
        gt = ground_truth[r['id']]
        score, note = scores[lang][r['id']]
        resp = r['model_response']
        scored.append({
            'id': r['id'],
            'language': lang,
            'category': r['category'],
            'question': r['question'],
            'model_response': resp,
            'reference_ruling': gt['ruling'],
            'reference_answer': gt['correct_answer'],
            'reference_school': gt['school'],
            'sources': gt['sources'],
            'score': score,
            'score_label': LABELS[score],
            'notes': note,
            'mentions_hanafi': 'hanafi' in resp.lower(),
            'mentions_any_school': any(s in resp.lower() for s in SCHOOLS),
            'reply_in_hinglish': is_hinglish(resp),
            'incoherent_output': is_incoherent(note),
            'misread_question': is_misread(note),
            'fabricated_evidence': bool(re.search(r'fabricated|non-existent|invents a legal term', note, re.I)),
            'response_words': len(resp.split()),
        })

with open('results/scored_results.json', 'w') as f:
    json.dump({'scored': scored}, f, indent=2, ensure_ascii=False)
for lang in LANGUAGES:
    with open(f'results/scored_results_{lang}.json', 'w') as f:
        json.dump({'scored': [s for s in scored if s['language'] == lang]}, f, indent=2, ensure_ascii=False)

# Side-by-side sheet for review
with open('results/review_sheet.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id', 'category', 'question_english', 'reference_ruling',
                'english_score', 'english_notes', 'hinglish_score', 'hinglish_notes'])
    by = {(s['id'], s['language']): s for s in scored}
    for qid in sorted(ground_truth):
        e, h = by[(qid, 'english')], by[(qid, 'hinglish')]
        w.writerow([qid, e['category'], e['question'], e['reference_ruling'],
                    e['score'], e['notes'], h['score'], h['notes']])

# ── SUMMARY STATS ───────────────────────────────────────────────────────
df = pd.DataFrame(scored)
df['correct'] = df['score'] >= 3          # correct or partially correct
hanafi_ids = [g for g in ground_truth if 'hanafi' in ground_truth[g]['question'].lower()]


def summarize(d):
    cat = d.groupby('category').agg(mean_score=('score', 'mean'),
                                    acceptable_pct=('correct', lambda x: x.mean() * 100))
    h = d[d['id'].isin(hanafi_ids)]
    return {
        'mean_score': round(d['score'].mean(), 2),
        'acceptable_pct_score_ge_3': round(d['correct'].mean() * 100, 1),
        'fully_correct_pct_score_4': round((d['score'] == 4).mean() * 100, 1),
        'wrong_or_hallucinated_pct': round((d['score'] <= 2).mean() * 100, 1),
        'score_distribution': {f'{k} {v}': int((d['score'] == k).sum()) for k, v in LABELS.items()},
        'by_category': cat.round(2).to_dict('index'),
        'weakest_category': cat['mean_score'].idxmin(),
        'hanafi_questions': {
            'n': len(h),
            'mean_score': round(float(h['score'].mean()), 2),
            'fully_correct': int((h['score'] == 4).sum()),
        },
        'responses_naming_a_school': int(d['mentions_any_school'].sum()),
        'incoherent_outputs': int(d['incoherent_output'].sum()),
        'misread_question': int(d['misread_question'].sum()),
        'fabricated_evidence': int(d['fabricated_evidence'].sum()),
        'mean_response_words': round(d['response_words'].mean(), 1),
    }


summary = {lang: summarize(df[df['language'] == lang]) for lang in LANGUAGES}
summary['hinglish']['replies_written_in_hinglish'] = int(df[(df['language'] == 'hinglish')]['reply_in_hinglish'].sum())
wide = df.pivot(index='id', columns='language', values='score')
summary['language_gap'] = {
    'mean_score_drop': round(wide['english'].mean() - wide['hinglish'].mean(), 2),
    'hinglish_lower': int((wide['hinglish'] < wide['english']).sum()),
    'hinglish_higher': int((wide['hinglish'] > wide['english']).sum()),
    'same': int((wide['hinglish'] == wide['english']).sum()),
    'correct_in_english_but_hallucinated_in_hinglish': wide[(wide['english'] >= 3) & (wide['hinglish'] == 0)].index.tolist(),
}
with open('results/summary.json', 'w') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

for lang in LANGUAGES:
    s = summary[lang]
    print(f'\n===== {lang.upper()} =====')
    print(f"Mean score: {s['mean_score']} / 4")
    print(f"Acceptable (score >= 3): {s['acceptable_pct_score_ge_3']}%")
    print(f"Fully correct (score = 4): {s['fully_correct_pct_score_4']}%")
    print(f"Wrong or hallucinated (score <= 2): {s['wrong_or_hallucinated_pct']}%")
    print('Score distribution:', s['score_distribution'])
    print('By category:', json.dumps(s['by_category'], indent=2))
    print('Hanafi questions:', s['hanafi_questions'])
    print('Incoherent outputs:', s['incoherent_outputs'], '| Misread question:', s['misread_question'],
          '| Fabricated evidence:', s['fabricated_evidence'])
    print('Responses naming a school:', s['responses_naming_a_school'])
print('\nHinglish replies actually written in Hinglish:', summary['hinglish']['replies_written_in_hinglish'], '/ 50')
print('Language gap:', json.dumps(summary['language_gap'], indent=2))


# ── MITIGATION CONDITIONS ───────────────────────────────────────────────
# A = baseline (above), B = guided prompt, C = grounded (BM25 retrieval)
with open('results/solutions/scores_solutions.json') as f:
    sol_scores = json.load(f)


def script_of(text):
    if re.search(r'[ऀ-ॿ]', text):
        return 'devanagari'
    if re.search(r'[؀-ۿ]', text):
        return 'arabic/urdu'
    return 'latin'


rows = []
for s in scored:
    rows.append({'condition': 'A_baseline', 'language': s['language'], 'id': s['id'],
                 'category': s['category'], 'score': s['score'], 'notes': s['notes'],
                 'script': script_of(s['model_response']), 'retrieval_hit': None,
                 'reply_in_hinglish': s['reply_in_hinglish']})
for cond, key in [('B_guided', 'guided'), ('C_grounded', 'grounded')]:
    for lang in LANGUAGES:
        with open(f'results/solutions/raw_{key}_{lang}.json') as f:
            for r in json.load(f)['results']:
                score, note = sol_scores[f'{key}_{lang}'][r['id']]
                rows.append({'condition': cond, 'language': lang, 'id': r['id'],
                             'category': r['category'], 'score': score, 'notes': note,
                             'script': script_of(r['model_response']),
                             'retrieval_hit': r['retrieval_hit'],
                             'reply_in_hinglish': is_hinglish(r['model_response'])})
cdf = pd.DataFrame(rows)
cdf.to_csv('results/solutions/all_conditions_scores.csv', index=False)

conditions = {}
for (cond, lang), d in cdf.groupby(['condition', 'language']):
    conditions.setdefault(cond, {})[lang] = {
        'mean_score': round(float(d['score'].mean()), 2),
        'fully_correct': int((d['score'] == 4).sum()),
        'acceptable_score_ge_3': int((d['score'] >= 3).sum()),
        'wrong_or_hallucinated': int((d['score'] <= 2).sum()),
        'hallucinated': int((d['score'] == 0).sum()),
        'fabricated_evidence': int(d['notes'].str.contains('fabricated|invented scholar|non-existent scholar|invented attribution|invented muftis', case=False).sum()),
        'non_latin_script_replies': int((d['script'] != 'latin').sum()),
        'retrieval_hits': int(d['retrieval_hit'].sum()) if d['retrieval_hit'].notna().any() else None,
        'by_category': d.groupby('category')['score'].mean().round(2).to_dict(),
    }
summary['conditions'] = conditions
with open('results/summary.json', 'w') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print('\n===== MITIGATION =====')
for cond in conditions:
    for lang in LANGUAGES:
        c = conditions[cond][lang]
        print(f"{cond:11s} {lang:8s} mean {c['mean_score']:.2f} | correct {c['fully_correct']:2d} | "
              f"acceptable {c['acceptable_score_ge_3']:2d} | hallucinated {c['hallucinated']:2d} | "
              f"non-Latin {c['non_latin_script_replies']:2d} | retrieval {c['retrieval_hits']}")
