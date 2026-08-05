# Deploying steadyworkhq.com — GitHub Pages + Squarespace domain

Total time: ~20 minutes of clicking, then up to a day of waiting on DNS. Total cost: $0 beyond the domain.

## What's in this folder

- `index.html` — the main Steadywork site
- `home-services.html` — the missed-call campaign page (send HVAC/plumbing/electrical prospects here)
- `CNAME` — one-line file telling GitHub Pages your custom domain; don't delete it

## Before you deploy: two find-and-replaces

Open both HTML files in any text editor and replace:

1. `[CALENDLY-LINK]` → your Calendly booking URL (make a free Calendly account, create a "15-minute intro call" event, copy the link, e.g. `https://calendly.com/yourname/15min`). It appears 3 times in index.html and once in home-services.html.
2. `[CITY]`, `[EMAIL]`, `[PHONE]` → your real details (footer of both files, About/headshot placeholder text too when you have a photo).

## Step 1 — Put the files on GitHub

1. Sign in at github.com → **New repository**.
2. Name it `steadywork-site`, set it **Public**, click **Create repository**.
3. On the empty-repo page click **"uploading an existing file"**, drag in `index.html`, `home-services.html`, and `CNAME`, then **Commit changes**.

## Step 2 — Turn on GitHub Pages

1. In the repo: **Settings → Pages** (left sidebar).
2. Under "Build and deployment": Source = **Deploy from a branch**, Branch = **main**, folder = **/ (root)**. Save.
3. In a minute or two the page shows a live URL like `https://yourusername.github.io/steadywork-site/` — check that the site loads there.

## Step 3 — Connect the domain

1. Still in **Settings → Pages**, under "Custom domain", enter `steadyworkhq.com` and Save. (GitHub reads the CNAME file too — this just confirms it.)
2. At **Squarespace → Domains → steadyworkhq.com → DNS settings**, delete any existing default A/CNAME records for `@` and `www`, then add:

   | Type | Host | Value |
   |---|---|---|
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | CNAME | www | `yourusername.github.io` |

3. Wait for DNS to propagate (minutes to a few hours, occasionally a day).
4. Back in GitHub **Settings → Pages**, once the domain check turns green, tick **"Enforce HTTPS"** (the free certificate can take up to an hour to issue — if the box is greyed out, wait and refresh).
5. Recommended: in your GitHub **account** settings → Pages → "Verified domains", verify steadyworkhq.com (it walks you through adding one TXT record at Squarespace). Prevents anyone hijacking the domain on Pages if the repo ever moves.

## Editing the site later

Edit a file directly on github.com (open the file → pencil icon → commit) or ask me — I have the source saved in the project, can make any change, and hand you back the updated file to upload. Every commit redeploys automatically in ~1 minute.

## Checks after launch

- `https://steadyworkhq.com` and `https://www.steadyworkhq.com` both load with a padlock
- The calculator sliders work on your phone
- Every "Book a call" button opens your Calendly
- Search "site:steadyworkhq.com" on Google after a week; if nothing appears, add the site to Google Search Console (free) and submit it
