"""Draws the README figures from results/scored_results.json into figures/."""
import json
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import pandas as pd

# palette
PAPER = '#faf8f3'
INK, INK2, INK3, RULE = '#1d1b18', '#5b5750', '#8a857c', '#e3dfd6'
EN, HI = '#33529c', '#c47a1e'                       # English indigo, Hinglish ochre
# score 0..4: hallucinated, refused, wrong, partial, correct
SCORE = ['#9e3a2c', '#d9d4c9', '#e2ad9f', '#b3c0e2', '#33529c']
WHITE_TEXT = {0, 4}
LABELS = {4: 'Correct', 3: 'Partial', 2: 'Wrong', 1: 'Refused', 0: 'Hallucinated'}
CATS = {'Fasting_Medication': 'Fasting & medication',
        'Surgery_Procedures': 'Surgery & procedures',
        'Blood_Organ_Donation': 'Blood & organ donation',
        'End_of_Life': 'End-of-life care',
        'Controversial_Ethics': 'Controversial ethics'}

plt.rcParams.update({
    'font.family': 'Avenir Next', 'font.size': 11, 'text.color': INK,
    'axes.edgecolor': RULE, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.facecolor': PAPER, 'figure.facecolor': PAPER, 'savefig.facecolor': PAPER,
    'axes.spines.top': False, 'axes.spines.right': False,
})


def title(fig, text, sub):
    fig.text(0.02, 0.965, text, fontsize=15, family='Charter', weight='bold', color=INK, va='top')
    fig.text(0.02, 0.885, sub, fontsize=10.5, color=INK2, va='top')


def save(fig, name):
    fig.savefig(f'figures/{name}.png', dpi=220)
    plt.close(fig)


df = pd.DataFrame(json.load(open('results/scored_results.json'))['scored'])

# 1. Score distribution: one 100% bar per language
fig, ax = plt.subplots(figsize=(10, 3.3))
fig.subplots_adjust(left=0.11, right=0.98, top=0.66, bottom=0.2)
title(fig, 'Score distribution', 'Share of 50 responses per language, scored 0–4 against verified reference answers')
order = [0, 1, 2, 3, 4]
for row, lang, name in [(1, 'english', 'English'), (0, 'hinglish', 'Hinglish')]:
    left = 0
    for s in order:
        n = int(((df.language == lang) & (df.score == s)).sum())
        if n == 0:
            continue
        ax.barh(row, n - 0.12, left=left, height=0.62, color=SCORE[s])
        if n >= 3:
            ax.text(left + (n - 0.12) / 2, row, str(n), ha='center', va='center', fontsize=10.5,
                    color='white' if s in WHITE_TEXT else INK, weight='demibold')
        left += n
ax.set_yticks([1, 0], ['English', 'Hinglish'], fontsize=11.5, color=INK)
ax.set_xlim(0, 50); ax.set_xticks([0, 10, 20, 30, 40, 50])
ax.tick_params(length=0); ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
ax.set_xlabel('Responses', fontsize=10)
handles = [plt.Rectangle((0, 0), 1, 1, color=SCORE[s]) for s in order if s != 1]
ax.legend(handles, [f'{s}  {LABELS[s]}' for s in order if s != 1], ncol=4, frameon=False,
          loc='lower left', bbox_to_anchor=(-0.01, 1.0), fontsize=10, handlelength=1.2, columnspacing=1.6)
save(fig, 'score_distribution')

# 2. Category means: dumbbell, English -> Hinglish
g = df.groupby(['category', 'language'])['score'].mean().unstack()
cats = list(CATS)[::-1]
fig, ax = plt.subplots(figsize=(10, 4.4))
fig.subplots_adjust(left=0.22, right=0.97, top=0.76, bottom=0.14)
title(fig, 'Mean score by category', 'Every category drops when the same question is asked in Hinglish')
for i, c in enumerate(cats):
    e, h = g.loc[c, 'english'], g.loc[c, 'hinglish']
    ax.plot([h, e], [i, i], color=RULE, lw=5, solid_capstyle='round', zorder=1)
    ax.scatter([e], [i], s=130, color=EN, zorder=3, edgecolor=PAPER, linewidth=2)
    ax.scatter([h], [i], s=130, color=HI, zorder=3, edgecolor=PAPER, linewidth=2)
    ax.text(e + 0.09, i, f'{e:.1f}', va='center', fontsize=10, color=INK2)
    ax.text(h - 0.09, i, f'{h:.1f}', va='center', ha='right', fontsize=10, color=INK2)
ax.set_yticks(range(len(cats)), [CATS[c] for c in cats], fontsize=11, color=INK)
ax.set_xlim(0, 4); ax.set_xticks(range(5))
ax.xaxis.grid(True, color=RULE, lw=0.8); ax.set_axisbelow(True)
ax.tick_params(length=0); ax.spines['left'].set_visible(False)
ax.set_xlabel('Mean score (0 = hallucinated, 4 = correct)', fontsize=10)
ax.scatter([], [], s=90, color=EN, label='English'); ax.scatter([], [], s=90, color=HI, label='Hinglish')
ax.legend(frameon=False, ncol=2, loc='lower left', bbox_to_anchor=(-0.01, 1.0), fontsize=10)
save(fig, 'score_by_category')

# 3. Every question, both languages
piv = df.pivot(index='language', columns='id', values='score').loc[['english', 'hinglish']]
fig, ax = plt.subplots(figsize=(13, 2.9))
fig.subplots_adjust(left=0.075, right=0.995, top=0.6, bottom=0.2)
title(fig, 'Every question, both languages', 'Each cell is one response; the number is its score')
ax.imshow(piv.values, cmap=ListedColormap(SCORE), norm=BoundaryNorm(np.arange(-0.5, 5.5), 5), aspect='auto')
ax.set_xticks(np.arange(-0.5, 50, 1), minor=True); ax.set_yticks([-0.5, 0.5, 1.5], minor=True)
ax.grid(which='minor', color=PAPER, lw=2.2); ax.tick_params(which='both', length=0)
for (r, c), v in np.ndenumerate(piv.values):
    ax.text(c, r, str(v), ha='center', va='center', fontsize=8,
            color='white' if v in WHITE_TEXT else INK)
ax.set_yticks([0, 1], ['English', 'Hinglish'], fontsize=10.5, color=INK)
ax.set_xticks(range(50), [q[1:] for q in piv.columns], fontsize=7, color=INK3)
for i in range(1, 5):
    ax.axvline(i * 10 - 0.5, color=PAPER, lw=7)
for i, c in enumerate(CATS):
    ax.text(i * 10 + 4.5, -0.78, CATS[c], ha='center', fontsize=9.5, color=INK2)
for s in ax.spines.values():
    s.set_visible(False)
save(fig, 'score_per_question')

# 4. How Hinglish answers fail (each failing response counted once)
hi_df = df[(df.language == 'hinglish') & (df.score <= 2)]
inc = hi_df.incoherent_output
mis = hi_df.misread_question & ~inc
rest = ~inc & ~mis
types = {
    'Wrong ruling': int((rest & (hi_df.score == 2)).sum()),
    'Invented ruling with no basis': int((rest & (hi_df.score == 0)).sum()),
    'Misread the question': int(mis.sum()),
    'Incoherent or looping text': int(inc.sum()),
}
assert sum(types.values()) == len(hi_df)
fig, ax = plt.subplots(figsize=(10, 3.4))
fig.subplots_adjust(left=0.27, right=0.95, top=0.72, bottom=0.17)
title(fig, f'How the {len(hi_df)} failing Hinglish answers fail',
      'Responses scored 0 or 2, grouped by failure type')
names, vals = list(types), list(types.values())
bars = ax.barh(names, vals, color=HI, height=0.56)
for b, v in zip(bars, vals):
    ax.text(v + 0.2, b.get_y() + b.get_height() / 2, str(v), va='center', fontsize=10.5, color=INK2)
ax.tick_params(axis="y", labelsize=11, labelcolor=INK)
ax.xaxis.grid(True, color=RULE, lw=0.8); ax.set_axisbelow(True)
ax.tick_params(length=0); ax.spines['left'].set_visible(False)
ax.set_xlabel('Responses', fontsize=10)
save(fig, 'hinglish_failure_types')
print('saved 4 figures')

# 5. Three conditions side by side
cdf = pd.read_csv('results/solutions/all_conditions_scores.csv')
COND = [('A_baseline', 'A  Baseline'), ('B_guided', 'B  Guided prompt'), ('C_grounded', 'C  Grounded')]
fig, ax = plt.subplots(figsize=(10, 5.2))
fig.subplots_adjust(left=0.25, right=0.88, top=0.74, bottom=0.12)
title(fig, 'What helps, and what does not',
      'Score distribution for 50 questions under each condition. Mean score on the right.')
y, ticks, labels = 0, [], []
for cond, cname in COND[::-1]:
    for lang, lname in [('hinglish', 'Hinglish'), ('english', 'English')]:
        d = cdf[(cdf.condition == cond) & (cdf.language == lang)]
        left = 0
        for s in [0, 1, 2, 3, 4]:
            n = int((d.score == s).sum())
            if n == 0:
                continue
            ax.barh(y, n - 0.12, left=left, height=0.72, color=SCORE[s])
            if n >= 3:
                ax.text(left + (n - 0.12) / 2, y, str(n), ha='center', va='center', fontsize=9.5,
                        color='white' if s in WHITE_TEXT else INK, weight='demibold')
            left += n
        ax.text(51.2, y, f'{d.score.mean():.2f}', va='center', fontsize=11, weight='demibold',
                color=EN if lang == 'english' else HI)
        ticks.append(y); labels.append(lname)
        y += 1
    ax.text(-15.5, y - 1.5, cname, va='center', ha='left', fontsize=11, weight='demibold', color=INK)
    y += 0.6
ax.set_yticks(ticks, labels, fontsize=10, color=INK2)
ax.set_xlim(0, 50); ax.set_xticks([0, 10, 20, 30, 40, 50])
ax.tick_params(length=0); ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
ax.set_xlabel('Responses', fontsize=10)
ax.text(51.2, y - 0.3, 'mean', fontsize=9, color=INK3)
handles = [plt.Rectangle((0, 0), 1, 1, color=SCORE[s]) for s in [0, 2, 3, 4]]
ax.legend(handles, [f'{s}  {LABELS[s]}' for s in [0, 2, 3, 4]], ncol=4, frameon=False,
          loc='lower left', bbox_to_anchor=(-0.01, 1.0), fontsize=10, handlelength=1.2, columnspacing=1.6)
save(fig, 'conditions_comparison')
print('saved conditions_comparison')
