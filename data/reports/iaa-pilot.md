# IAA pilot — causal-hypothesis plausibility

Reliability pilot for gap G1 (see docs/plans/research-grade.md). The
authoritative measure is the human round (materials in eval/iaa/); these
LLM annotators are a **reliability probe, not ground truth** (docs/annotation-guidelines.md).

- Items (curated causal hypotheses): **134**
- Annotator 1: **curator** (confidence binarised at >= 0.66 -> yes).
- Annotators 2-4: independent local model families (qwen3:14b, phi4:latest, gemma3:27b) via ollama.

## Q1 plausibility — yes-rate per annotator

| annotator | yes | rated | yes-rate |
|-----------|-----|-------|----------|
| curator | 126 | 134 | 94% |
| qwen3:14b | 131 | 134 | 98% |
| phi4:latest | 127 | 134 | 95% |
| gemma3:27b | 133 | 134 | 99% |

## Q1 plausibility — pairwise Cohen's kappa

| annotator A | annotator B | Cohen kappa | % agree | n |
|-------------|-------------|-------------|---------|---|
| curator | qwen3:14b | 0.154 | 93% | 134 |
| curator | phi4:latest | 0.082 | 90% | 134 |
| curator | gemma3:27b | 0.212 | 95% | 134 |
| qwen3:14b | phi4:latest | 0.174 | 94% | 134 |
| qwen3:14b | gemma3:27b | 0.494 | 99% | 134 |
| phi4:latest | gemma3:27b | 0.240 | 96% | 134 |

**Majority-LLM vs curator:** Cohen kappa = 0.212 (n=134).

## Krippendorff's alpha (all annotators)

- Q1 plausibility (nominal): **alpha = 0.183**
- Q2 evidence tier (ordinal, LLMs only): **alpha = 0.099**

## Reading these numbers honestly

- A high yes-rate across annotators is expected: the curated set is, by
  construction, hand-picked for defensible triggers. The pilot tests whether
  independent readers *agree the curation is defensible*, not detection skill.
- Curator-vs-LLM kappa is the informative figure; LLM-vs-LLM agreement can be
  inflated by shared model biases (cf. the IETF-survey experience where LLM
  quality scores reached only kappa_w ~ 0.13).
- Low kappa with high percent-agreement is the classic prevalence paradox
  (almost everything is 'yes'); we therefore report both, plus alpha.
- The human round (>= 2 raters on the stratified eval/iaa/human-sheet.csv) is
  the measure of record; this pilot only sizes the instrument and surfaces
  the hard cases (items where annotators disagree are the ones worth human
  review).

## Items with annotator disagreement (priority for the human round)

- `hyp-arbeit-protestant`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-backfisch-literatur`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-banause-bildung`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-etappe-wwi`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-gay-stonewall`: curator=yes, qwen3:14b=no, phi4:latest=yes, gemma3:27b=yes
- `hyp-gutmensch-politics`: curator=yes, qwen3:14b=yes, phi4:latest=no, gemma3:27b=yes
- `hyp-kavalier-hofkultur`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-klimakleber-lg`: curator=yes, qwen3:14b=yes, phi4:latest=no, gemma3:27b=yes
- `hyp-maus-macintosh`: curator=yes, qwen3:14b=yes, phi4:latest=no, gemma3:27b=yes
- `hyp-nicotine-tobacco`: curator=yes, qwen3:14b=yes, phi4:latest=no, gemma3:27b=yes
- `hyp-shrapnel-shell`: curator=yes, qwen3:14b=no, phi4:latest=yes, gemma3:27b=yes
- `hyp-spam-usenet`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-toll-youth`: curator=no, qwen3:14b=yes, phi4:latest=yes, gemma3:27b=yes
- `hyp-turkey-trade`: curator=yes, qwen3:14b=yes, phi4:latest=no, gemma3:27b=yes
- `hyp-yahoo-gulliver`: curator=yes, qwen3:14b=yes, phi4:latest=no, gemma3:27b=yes

_15 of 134 items had any disagreement._