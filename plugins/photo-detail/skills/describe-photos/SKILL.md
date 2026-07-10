---
description: Generate searchable sidecar .md descriptions for a batch of high-resolution photos via tiled full-detail analysis — verbatim label transcriptions, component inventory, condition notes.
---

# Describe Photos (sidecar descriptions via agent fan-out)

Creates a sibling `<photo-name>.md` next to each photo. Pay the vision cost
once; afterwards photo contents are greppable and no session re-spends image
reads to answer "which photo shows X?" or "what did that label say?".

Scope: $ARGUMENTS (may name a directory, an asset/date filter, or explicit
files). If no scope is given, resolve the photo location in this order:
1. the project CLAUDE.md's photo/attachments convention,
2. an obvious photo directory in the repo (e.g. `**/attachments/photos/`),
3. ask the user.
Default set: every photo in scope that has no sidecar `.md` yet.

> Tiled analysis is the validated method (see the A/B test in this plugin's
> README): a plain downscaled Read hallucinates label text and cannot detect
> blur. Do not substitute single-Read descriptions to save tokens.

## Roles & models

- **Workers** — one subagent per photo, `subagent_type: general-purpose`,
  `model: sonnet`. Bounded task: tile, look, transcribe, describe. Workers
  NEVER guess component identity — they describe physically and flag.
- **Orchestrator** — the main session (do not spawn a separate orchestrator).
  Resolves flagged uncertainties with targeted crops, cross-checks against the
  project's reference docs, and updates doc cross-references.

## Orchestrator procedure

1. **List unprocessed photos** in scope:

   ```bash
   for f in <photo-dir>/*.jpg <photo-dir>/*.png; do
     [ -e "${f%.*}.md" ] || echo "$f"
   done
   ```

2. **Fan out workers** — up to ~8 in parallel per message, `run_in_background`
   default is fine. Give each worker the prompt template below with the
   placeholders substituted (including the literal expanded value of
   `${CLAUDE_PLUGIN_ROOT}` — workers do not inherit this plugin's variables).
   Workers write their own sidecar file (distinct paths, no write conflicts)
   and return only a compact summary + flags.

3. **Review returns.** For each flagged uncertain ID or partially-legible
   transcription worth resolving, verify it yourself with one targeted crop:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/split-photo.py" <photo> --crop l,t,r,b --out <scratchpad>/verify
   ```

   **Always re-verify load-bearing strings** (part numbers, model codes,
   capacities) with your own crop before propagating them into project docs —
   workers occasionally produce confident misreads, especially of stylized
   lettering. Cross-check component identifications against the project's
   reference docs (specs, inventories, locator guides) where they exist.
   Edit the sidecar where the worker was wrong or you resolved a flag; leave
   honestly-unresolvable items in **Open Questions**.

4. **Update project docs**: if the photos feed a survey/spec/inventory doc,
   update its status/links. Aggregate all sidecar **Open Questions** into a
   re-shoot list for the user.

5. **Report**: photos processed, notable findings (part numbers, tags,
   condition issues), uncertainties resolved vs. remaining, re-shoot list.
   Leave everything unstaged for per-repo review.

## Worker prompt template

> Substitute `{PHOTO}` (absolute or repo-relative path), `{REPO}` (project
> root), `{SPLIT_SCRIPT}` (the expanded absolute path of
> `${CLAUDE_PLUGIN_ROOT}/split-photo.py`), and `{CONTEXT}` (one or two
> sentences: what the photos are of, plus any known equipment/model context
> that helps orient — never enough to make workers guess identities).

```
You are generating a sidecar description for one photo in a documentation
project at {REPO}.

Photo: {PHOTO}
Context: {CONTEXT}

Procedure:
1. Read the photo for an overview.
2. If the filename contains "-blurry" or the image is too soft to resolve
   detail, skip tiling — write a short sidecar from the overview alone and
   note the quality limitation.
3. Otherwise split it into full-detail tiles. Parallel workers SHARE the
   scratchpad, so you MUST use a tile directory unique to your photo (its
   filename stem):
     python3 {SPLIT_SCRIPT} {PHOTO} --out <your-scratchpad>/tiles-<photo-stem>
   For sources ≥ ~20 MP use a two-pass: survey tiles at `--target 3000`
   first, then full-resolution `--crop` passes on every information-dense
   region (labels, plates, stamps) until all physically legible text is read.
   Read EVERY survey tile. The grid map printed by the script gives each
   tile's position (r1c1 = top-left). Tiles overlap ~15%; dedupe objects that
   appear in two tiles. When done, delete ONLY your own tiles-<photo-stem>
   directory by its exact path — never the shared parent and never a glob —
   or you will destroy concurrent workers' tiles mid-run.
4. Write the sidecar to the photo's path with .md substituted for the image
   extension. IMPORTANT: replace the .jpg/.png extension entirely —
   .../photos/foo.jpg -> .../photos/foo.md (NOT foo.jpg.md). Use the template
   below.

Hard rules:
- Transcribe ALL legible text VERBATIM — labels, stickers, stamps, cast-in
  marks, handwritten tags — with its location in the frame. List partially
  legible text with best reading and unclear characters marked like "P/N 8?52".
  List visible-but-illegible text explicitly (what/where, why unreadable).
- NEVER guess a component's identity. If you are not certain, describe it
  physically ("black pump body low on left side, two ~1.25 in hoses entering")
  and add it to "Uncertain IDs".
- Give frame positions (upper-left, center, lower-right...) so a future
  reader can find things with a targeted crop.
- Take the date from the filename if it follows YYYY-MM-DD naming, else from
  file metadata.

Sidecar template:
---
photo: <filename with extension>
date: <YYYY-MM-DD>
subject: <one line>
quality: sharp | soft | blurry
---

# <Short title>

## Overview
<2-4 sentences: vantage point, what the frame covers>

## Components Visible
<bulleted: component (or physical description if uncertain) — frame position — notes>

## Transcribed Text
<verbatim items with locations; then partially-legible; then illegible-but-present>

## Condition Observations
<corrosion, wear, damage, missing fasteners, fluid residue, routing concerns>

## Uncertain IDs
<items you could not identify with confidence — physical description + position>

## Open Questions
<what a re-shoot or closer crop would resolve>

Your final message (this is data for the orchestrator, not prose): sidecar
path written, 2-3 line content summary, then bullet lists of Uncertain IDs
and Open Questions (empty lists if none).
```

> If the project's existing sidecars carry extra frontmatter (e.g. an
> `asset:` field), match that project's template instead — check a neighboring
> sidecar before fanning out.

## Cost note

Measured on 50 MP sources: ~112k tokens and ~4–5 min per photo (two-pass),
vs ~44k for a single-Read description — 2.5× cost for transcriptions that are
actually trustworthy. Full tiling is ~8 image reads per 8.8 MP photo, ~12 at
12.5 MP, 40+ at 50 MP full-res (hence the two-pass rule above).
