# AGENTS.md — documentation/

Context for the generated VitePress documentation site. See the root
`AGENTS.md` for the model itself.

## Commands

```bash
npm install          # first time
npm run dev          # local dev server
npm run build        # static build to .vitepress/dist
npm run preview      # serve the build
python scripts/build_llms.py   # refresh llms-full.txt and public/llms*.txt
```

## Structure

| Path | Purpose |
|---|---|
| `index.md` | landing page: quick start, architecture, doc map |
| `01-getting-started/` | overview, container contract, config, local dev |
| `02-architecture/` | pipeline, series handling, forecast, card validation |
| `03-template/` | build-your-own-model guide |
| `onboarding/` | contributor, staff, executive, PM guides |
| `_how-to-update.md` | maintainer manual for regenerating the docs |
| `scripts/build_llms.py` | regenerates `llms-full.txt` and the public LLM copies |
| `catalogue.json` | machine-readable structure (sections + prompts) |
| `llms.txt` | wiki-relative LLM index |
| `llms-full.txt` | all pages inlined in `<doc>` blocks |
| `.vitepress/` | config, theme, styles, public assets |

## Content conventions

- Frontmatter: `title` and `description` on every content page (the landing page included).
- Citations: `[path:line](https://github.com/The-EPISERVE-Consortium/model__prediction__generic__null-model/blob/main/path#Lline)`.
- Every Mermaid diagram is followed by `<!-- Sources: path:line, ... -->`.
- Mermaid: dark fills `#2d333b`, borders `#6d5dfc`, text `#e6edf3`; use `<br>`,
  not `<br/>`; `autonumber` in every `sequenceDiagram`.
- Tables over prose for APIs, config and component summaries; include a Source
  column.
- End every content page (except the landing page) with **Related Pages** and **References**.

## Boundaries

- ✅ Always: keep `llms.txt` and `llms-full.txt` in sync with new pages; test
  `npm run build` after theme changes.
- ⚠️ Ask first: deleting pages, changing the sidebar structure, editing
  `.vitepress/theme/index.ts`.
- 🚫 Never: put secrets or credentials in examples; use light-mode-only Mermaid
  colors; remove the `<!-- Sources -->` blocks.

## Documentation entry points

- `llms.txt` (repo root) and `documentation/llms.txt`
- `documentation/llms-full.txt`
