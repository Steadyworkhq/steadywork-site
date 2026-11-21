# Publishing the website

This folder is steadyworkhq.com. GitHub Pages serves it from the `main` branch.

## What is here

What each file and folder is, and which ones may be edited here: `CLAUDE.md` "Folder map". GitHub
Pages publishes the markdown files too, so they hold nothing private.

## Pushing to main publishes

A push to `main`, or a commit to `main` on github.com, is live in about a minute. Nothing else stands
between a change and the public, so push only on the owner's go, after the checks below. The owner's
go is their word in this session, or the approval or standing instruction a steadywork-app
`seo-workbench` round records in its `STATUS.md` (that folder's `CLAUDE.md` rule 10).

## Publishing a change

1. Start from the live version: in this folder run `git fetch origin`, then `git status`. If it says
   "behind", run `git pull` before changing anything.
2. Make the change in a hand-made page. For a guide, follow steadywork-app
   `docs/site-guides/README.md` instead.
3. If what a page says changed, set its `<lastmod>` in `sitemap.xml` to today's date (YYYY-MM-DD).
   Leave it alone for a link, a colour or a typo. Then run
   `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('sitemap.xml'); print('sitemap ok')"`.
   You should see `sitemap ok`.
4. If you changed a price, plan, credit amount, team size, top-up rule or the Terms date: in
   steadywork-app run `node tools/check_prices.js`. Fix every `problem:` line that names
   steadywork-site. Their home is `src/config.js` there, so a figure that really changed is changed
   there first.
5. In steadywork-app run
   `python3 seo-workbench/tools/check_site.py seo-workbench/rounds/<newest round>`. It checks every
   link, image and page title, and that every guide is in the sitemap. It must end `problem_items 0`.
6. Run `git diff --stat`. It should list only the files you meant to change.
7. On the owner's go: commit, then push to `main` (`git push origin HEAD:main` if you worked
   on another branch).
8. About a minute later, open the changed page on steadyworkhq.com and refresh it. After a round of
   guides, also run, in steadywork-app,
   `python3 seo-workbench/tools/check_site.py --live seo-workbench/rounds/<that round>`. It must end
   `problem_items 0`.

## Small fixes on github.com

The owner can fix wording in a hand-made page on github.com: open the file, press the pencil icon,
commit to `main`. It goes live at once and skips the checks above, so keep it to small wording
fixes, and still set the page's `<lastmod>` when what it says changed. Never edit `guides/` this way.

## Set-up, done once

Done when the site first went up (the `CNAME` file was added on 2026-08-04). Kept here in case it
ever needs redoing:

- GitHub, the repository's **Settings**, **Pages**: deploy from a branch, `main`, folder `/ (root)`;
  custom domain `steadyworkhq.com`; **Enforce HTTPS** ticked.
- Squarespace DNS for steadyworkhq.com: four A records for `@` (185.199.108.153, 185.199.109.153,
  185.199.110.153, 185.199.111.153) and a CNAME for `www` pointing to the GitHub Pages address.
  The app's own record (`app`) is separate: steadywork-app `WHEN-YOU-RETURN.md` section 6.

Not recorded: whether steadyworkhq.com was also verified under the GitHub account's **Settings**,
**Pages**, **Verified domains**.
