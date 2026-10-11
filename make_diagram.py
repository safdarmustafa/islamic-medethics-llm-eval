"""Draws the methodology diagram (figures/methodology.png)."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PAPER, INK, INK2, RULE = '#faf8f3', '#1d1b18', '#5b5750', '#cfc9bd'
EN, HI, RED = '#33529c', '#c47a1e', '#9e3a2c'
plt.rcParams.update({'font.family': 'Avenir Next', 'figure.facecolor': PAPER})

fig = plt.figure(figsize=(13, 6.2))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 130); ax.set_ylim(0, 62); ax.axis('off')
ax.set_facecolor(PAPER)


def box(x, y, w, h, head, body, edge=RULE, fill='white', head_color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.2',
                                fc=fill, ec=edge, lw=1.4))
    ax.text(x + 1.8, y + h - 2.4, head, fontsize=11.5, weight='demibold', color=head_color, va='top')
    ax.text(x + 1.8, y + h - 5.8, body, fontsize=9.5, color=INK2, va='top', linespacing=1.45)


def arrow(x1, y1, x2, y2, color=INK2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=13,
                                 color=color, lw=1.3, shrinkA=0, shrinkB=0))


ax.text(2, 59, 'How the evaluation works', fontsize=16, family='Charter', weight='bold', color=INK, va='top')


# 1 questions
box(2, 24, 24, 22, '1  Questions',
    '50 questions written\nfrom real patient cases\n5 categories × 10\n7 ask for the Hanafi view')
# languages
box(2, 6, 11.5, 13, 'English', '50 prompts', edge=EN, head_color=EN)
box(14.5, 6, 11.5, 13, 'Hinglish', '50 prompts', edge=HI, head_color=HI)
arrow(14, 24, 14, 19.4)

# 2 model
box(29, 24, 26, 22, '2  Model',
    'Qwen2.5-3B-Instruct\n4-bit, Apple MLX\ntemperature 0.1\nzero-shot')
arrow(26.2, 12.5, 30, 24, INK2)

# 3 conditions
box(58, 38.5, 27, 8, '3A  Baseline', 'original prompt')
box(58, 29.25, 27, 8, '3B  Guided prompt', 'language, school, uncertainty')
box(58, 20, 27, 8, '3C  Grounded', 'guided + 2 retrieved references')
for y in (42.5, 33.25, 24):
    arrow(55.2, 35, 57.8, y)

# references (feeds C and scoring)
box(58, 2, 27, 14, 'Verified references',
    'OIC Fiqh Academy, MWL Fiqh Council,\nDeoband, Hanafi muftis, islamqa.info\nruling + key points + sources')
arrow(71.5, 16.2, 71.5, 19.8, EN)
ax.text(72.6, 17.4, 'BM25 retrieval', fontsize=8.5, color=EN)

# 4 responses
box(88, 24, 19, 22, '4  Responses',
    '3 conditions\n× 2 languages\n× 50 questions\n= 300 answers')
for y in (42.5, 33.25, 24):
    arrow(85.2, y, 87.8, 35)

# 5 scoring
box(110, 24, 18, 22, '5  Scoring',
    '0–4 rubric, with a\nnote for every answer\n4 correct · 3 partial\n2 wrong · 1 refused\n0 hallucinated')
arrow(107.2, 35, 109.8, 35)
ax.plot([85.2, 119], [9, 9], color=EN, lw=1.3); arrow(119, 9, 119, 23.8, EN)
ax.text(96, 10.2, 'reference answer for each question', fontsize=8.5, color=EN)

# analysis strip
box(88, 50, 40, 9, '6  Analysis', 'by category, language, school and failure type', fill=PAPER)
arrow(119, 46.2, 119, 49.8)

fig.savefig('figures/methodology.png', dpi=220)
print('saved figures/methodology.png')
