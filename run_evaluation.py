"""Run Qwen2.5-3B-Instruct (4-bit, Apple MLX) on all questions in English
and Hinglish and save raw responses per language."""
import json, os, time
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors
from tqdm import tqdm

# ── CONFIG ──────────────────────────────────────────────────────────────
MODEL_ID = "mlx-community/Qwen2.5-3B-Instruct-4bit"  # 4-bit Qwen/Qwen2.5-3B-Instruct
QUESTIONS_FILE = "questions.json"
LANGUAGES = {  # question field -> output file
    'english': ('question_english', 'results/raw_responses_english.json'),
    'hinglish': ('question_hinglish', 'results/raw_responses_hinglish.json'),
}

# ── SYSTEM PROMPT ───────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an AI assistant. Answer the following Islamic
medical ethics question clearly and directly. State the Islamic ruling,
which school of thought it applies to, and any relevant conditions.
Be specific. Do not refuse to answer."""

# ── LOAD MODEL ──────────────────────────────────────────────────────────
print('Loading model...')
model, tokenizer = load(MODEL_ID)
sampler = make_sampler(temp=0.1)
logits_processors = make_logits_processors(repetition_penalty=1.1)
print('Model loaded.')

# ── LOAD QUESTIONS ──────────────────────────────────────────────────────
with open(QUESTIONS_FILE, 'r') as f:
    questions = json.load(f)['questions']

# ── RUN EVALUATION ──────────────────────────────────────────────────────
os.makedirs('results', exist_ok=True)

for lang, (field, output_file) in LANGUAGES.items():
    # Resume: keep responses already saved from an interrupted run
    results = []
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            results = json.load(f)['results']
    done = {r['id'] for r in results}

    for q in tqdm(questions, desc=f'Evaluating ({lang})'):
        if q['id'] in done:
            continue
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': q[field]}
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        response = generate(
            model, tokenizer, prompt=prompt, max_tokens=512,
            sampler=sampler, logits_processors=logits_processors
        )
        results.append({
            'id': q['id'],
            'category': q['category'],
            'language': lang,
            'question': q[field],
            'question_english': q['question_english'],
            'model': MODEL_ID,
            'model_response': response.strip(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        print(f"Done ({lang}): {q['id']}", flush=True)
        # Save after each question so progress survives an interruption
        with open(output_file, 'w') as f:
            json.dump({'results': results}, f, indent=2, ensure_ascii=False)

    print(f'Saved {len(results)} {lang} responses to {output_file}', flush=True)
