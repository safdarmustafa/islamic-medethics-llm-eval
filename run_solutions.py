"""Runs the two mitigation conditions on all questions in both languages.

guided    a rewritten system prompt (answer in the user's language, give the
          named school's view, state disagreement, no unverified citations)
grounded  the guided prompt plus the two most relevant verified references,
          retrieved with BM25 from the reference corpus (ground_truth.json)

Output: results/solutions/raw_<condition>_<language>.json
"""
import json, math, os, re, time
from collections import Counter
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors
from tqdm import tqdm

MODEL_ID = "mlx-community/Qwen2.5-3B-Instruct-4bit"
OUT_DIR = "results/solutions"
TOP_K = 2
LANGUAGES = {'english': 'question_english', 'hinglish': 'question_hinglish'}

GUIDED_PROMPT = """You help Muslim patients and their families with questions about Islamic medical ethics.

Reply in the same language the user writes in. If the question is in Hinglish (Roman-script Hindi/Urdu mixed with English), reply in Hinglish.

Start with the ruling in one sentence, then give the conditions that matter. If the question names a school (madhhab), give that school's position. If scholars disagree, say so plainly and give the main positions.

Do not quote a hadith, verse or fatwa unless you are certain of its wording and source. If you are unsure, say so and advise the person to ask a qualified mufti."""

GROUNDED_SUFFIX = """

Base your answer on the verified references below. If they do not cover the question, say that."""


# ── retrieval ───────────────────────────────────────────────────────────
def tokens(text):
    return re.findall(r"[a-z]+", text.lower())


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [tokens(d) for d in docs]
        self.avg = sum(map(len, self.docs)) / len(self.docs)
        self.tf = [Counter(d) for d in self.docs]
        df = Counter(w for d in self.docs for w in set(d))
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query):
        q = tokens(query)
        out = []
        for tf, d in zip(self.tf, self.docs):
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out.append(s)
        return out


refs = json.load(open('ground_truth.json'))['ground_truth']
corpus = [f"{r['question']} {r['ruling']}. {r['correct_answer']}" for r in refs]
bm25 = BM25(corpus)


def retrieve(query):
    s = bm25.scores(query)
    top = sorted(range(len(s)), key=lambda i: -s[i])[:TOP_K]
    return [refs[i] for i in top]


def reference_block(docs):
    parts = []
    for i, r in enumerate(docs, 1):
        src = '; '.join(r['sources'][:2])
        parts.append(f"[{i}] {r['question']}\nRuling: {r['ruling']}\n{r['correct_answer']}\nSource: {src}")
    return "Verified references:\n\n" + "\n\n".join(parts)


# ── run ─────────────────────────────────────────────────────────────────
print('Loading model...')
model, tokenizer = load(MODEL_ID)
sampler = make_sampler(temp=0.1)
logits_processors = make_logits_processors(repetition_penalty=1.1)
questions = json.load(open('questions.json'))['questions']
os.makedirs(OUT_DIR, exist_ok=True)

for condition in ['guided', 'grounded']:
    for lang, field in LANGUAGES.items():
        path = f"{OUT_DIR}/raw_{condition}_{lang}.json"
        results = json.load(open(path))['results'] if os.path.exists(path) else []
        done = {r['id'] for r in results}
        for q in tqdm(questions, desc=f'{condition}/{lang}'):
            if q['id'] in done:
                continue
            system = GUIDED_PROMPT
            user = q[field]
            retrieved = []
            if condition == 'grounded':
                docs = retrieve(q[field])
                retrieved = [d['id'] for d in docs]
                system = GUIDED_PROMPT + GROUNDED_SUFFIX
                user = reference_block(docs) + "\n\nQuestion: " + q[field]
            messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            response = generate(model, tokenizer, prompt=prompt, max_tokens=512,
                                sampler=sampler, logits_processors=logits_processors)
            results.append({
                'id': q['id'], 'category': q['category'], 'condition': condition,
                'language': lang, 'question': q[field], 'question_english': q['question_english'],
                'retrieved_ids': retrieved, 'retrieval_hit': (q['id'] in retrieved) if retrieved else None,
                'model': MODEL_ID, 'model_response': response.strip(),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            with open(path, 'w') as f:
                json.dump({'results': results}, f, indent=2, ensure_ascii=False)
        print(f'Saved {len(results)} responses to {path}', flush=True)
