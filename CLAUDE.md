# Steadywork website

This repository is the public marketing site, steadyworkhq.com. GitHub Pages serves it from the
`main` branch. You work with the owner, who is not technical, works alone and reads these files, so
write in plain words and keep files short.

steadywork-app is the app's repository, next to this one. Some of this site is made or decided there.

## Folder map

| Path | What it is | Edit here? |
|---|---|---|
| `index.html`, `bookkeepers.html`, `terms.html`, `privacy.html`, `accessibility.html` | Hand-made pages | Yes |
| `home-services.html` | Retired: sends visitors to the home page | No need |
| `guides/` | Guide pages, generated in steadywork-app | Never |
| `sitemap.xml` | Hand-made pages' entries kept by hand; guide entries generated | Hand-made entries only |
| `brand/` | Logo files and the colours (`brand/README.md`) | Yes |
| `CNAME`, `robots.txt` | The domain for GitHub Pages; where search engines find the sitemap | Rarely. Never delete `CNAME` |
| `DEPLOY.md` | How to publish a change | Yes |

## Rules that always apply

1. **`guides/` is generated.** Every file in it, and the guide entries in `sitemap.xml`, are
   written by steadywork-app `docs/site-guides/guides.py`. Never edit them here: the next run
   overwrites the edit. To change a guide, follow steadywork-app `docs/site-guides/README.md`
   "How to change a guide".
2. **A push to `main` publishes.** GitHub Pages puts it live in about a minute. Push only on the
   owner's go: their word in this session, or the approval or standing instruction a steadywork-app
   `seo-workbench` round records in its `STATUS.md` (that folder's `CLAUDE.md` rule 10).
3. **Start from the live version.** Run `git fetch origin` before any change and work from
   `origin/main`, never from an old local copy.
4. **Facts have their home in steadywork-app.** Plan names, prices, credits, team size, top-up rules
   and the Terms date live in its `src/config.js`. Copy them from there, never from memory, and when
   one really changes, change it there first.
5. **This repository is public, and GitHub Pages publishes its markdown files too** (this one
   included). Never put secrets, customer details or private notes in any file here. Never type two
   opening curly brackets in a row, or an opening curly bracket followed by a percent sign, in any
   file: GitHub Pages reads them as template code, and one mistake stops the whole site publishing.
6. **Check before you push:** follow `DEPLOY.md` "Publishing a change". Its last check must end
   `problem_items 0`.

## Where to go

| To do this | Go to |
|---|---|
| Change wording on a page | That `.html` file. If what it says changed, set its `<lastmod>` in `sitemap.xml` to today. |
| Change or add a guide | steadywork-app `docs/site-guides/README.md` "How to change a guide". Never `guides/`. |
| Change a price, plan, credit amount, team size or top-up rule | steadywork-app `docs/checklists/change-a-price.md`. It lists every copy, here and in the guides. |
| Change the Terms date | `termsVersion` in steadywork-app `src/config.js` is the home; the "Last updated" line in `terms.html` must match it. |
| Change colours or the logo | `brand/README.md`. It lists every copy, here and in the guide generator. |
| Add a hand-made page | Copy the head and footer of an existing top-level page; add a `<url>` entry in `sitemap.xml`; to link it in the footer, change the footer in every top-level page and in `shell()` in `guides.py`, then rerun `guides.py`. |
| Change the app's address | steadywork-app `docs/checklists/change-app-address.md`. |
| Publish | `DEPLOY.md` "Publishing a change". |
