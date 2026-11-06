# How to update the documentation

The site in `documentation/` is a committed snapshot. It is **not** rebuilt from
the code, so a code change that alters the contract leaves the pages stale until
someone edits them.

## When this is needed

Update the docs in the same pull request when you change:

- `fdo.json`: parameters, bounds, defaults, inputs, outputs or resources;
- the container contract: file names, columns, exit codes or `--check-config`;
- error messages, axis handling or the gap policy;
- the forecast statistic, interval or clamping rule;
- module boundaries or the execution order;
- anything that moves the `file:line` citations used in the pages.

## Two ways to update

### 1. Edit by hand (recommended for small changes)

```bash
cd documentation
npm run dev          # http://localhost:5173, hot reload
# edit the affected .md files
npm run build        # must pass; dead links fail the build
```

Keep the existing conventions: frontmatter, the at-a-glance table, dark-mode
Mermaid, a `<!-- Sources: path:line -->` comment after each diagram, linked
citations, and the Related Pages / References sections.

### 2. Regenerate with Deep Wiki (large changes)

Requires `pi` and the skill package:

```bash
pi install npm:@amb007/deep-wiki
```

Then, in the repository root:

```text
/skill:deep-wiki generate
```

Important:

- The skill scaffolds into `wiki/` by default. Generate into a scratch directory
  and merge the result into `documentation/`, or tell it explicitly to update
  `documentation/` in place. Do not leave a second `wiki/` directory behind.
- Treat the output as a draft. Review every diff: the generator can rewrite
  correct prose, drop citations, or reintroduce the Mermaid 11 breakage.
- Keep `mermaid` on the 10.x line in `package.json`. Mermaid 11 fails at runtime
  with `fastdom ... does not provide an export named 'default'`, which blanks the
  whole site.
- Never auto-merge generated docs.

## Verify before committing

```bash
cd documentation
npm ci
npm run build
```

The build fails on dead internal links. Also check:

- every `blob/main/<path>#L<n>` citation points at a file that exists and a line
  that is within the file;
- every parameter in `fdo.json` still appears in
  `01-getting-started/configuration.md`;
- every Mermaid block still parses (the build does not catch this);
- the rendered pages look right in the browser.

Preview the production build:

```bash
npm run preview      # http://localhost:4173, base "/"
```

`vitepress preview` serves at `/`, even when the build used a Pages base. To test
the real subpath, serve `documentation/.vitepress/dist` under
`/model__prediction__generic__null-model/` with any static server.

## Publish

Pushing changes under `documentation/**` triggers
`.github/workflows/docs.yml`, which builds and deploys to GitHub Pages:

<https://the-episerve-consortium.github.io/model__prediction__generic__null-model/>

The workflow sets `DOCS_BASE=/<repo>/`. Local dev and a custom domain use `/`.
The built site (`documentation/.vitepress/dist/`) is not committed.

## Checklist

| Step | Command / action |
|---|---|
| Edit or regenerate the affected pages | `npm run dev` |
| Rebuild | `npm run build` |
| Check citations and parameters | manual review |
| Preview | `npm run preview` |
| Commit only sources | `git add documentation` |
| Push | `git push origin main` |
| Confirm deploy | GitHub Actions → Documentation |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Blank white page | Mermaid 11 / `fastdom` interop error | keep `mermaid@^10.9.x` |
| 404 at the Pages subpath locally | `vitepress preview` ignores `base` | serve `dist/` under the base path |
| Missing logo/favicon/`llms.txt` | assets are read from `documentation/public/` | add them there; `.vitepress/public` is a symlink |
| Dead link error in build | relative link points at a missing page | fix the link or add the page |
| Stale line numbers in citations | code moved | update the `#L<n>` values |
