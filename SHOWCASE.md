# Showcase Playbook — "Tell the Tale" Bounty + Social Strategy

**Bounty:** Top 50 showcases → Claude Max 5x 1-month vouchers  
**Bonus:** Top entries featured on Kunal Kushwaha's YouTube (870K+ subscribers)  
**Deadline:** Submit before hackathon closes (May 31, 2026)

---

## Part 1: Discord Showcase (#how-i-coral)

### What Judges Want to See

The `#how-i-coral` channel is where Coral's team and community will browse submissions. You're competing against ~50-100 showcases for a top-50 spot. Most will be low-effort. Here's how to stand out.

### Showcase Structure (Post Template)

```
🪸 devsecops-coral — Cross-Stack Security Correlation Agent

One SQL query across your entire DevSecOps stack.

🔍 What it does:
Correlates vulnerabilities (OSV), code changes (GitHub), application 
errors (Sentry), security tickets (Jira), and infrastructure alerts 
(Grafana) — in a single Coral SQL query.

⚓ Best Use of Coral:
• 5 sources (4 bundled + 1 custom OSV source spec)
• Cross-source JOINs to answer: "Are we vulnerable, and who shipped it?"
• Search function for OSV vulnerability lookup
• Rich CLI with severity-colored output

🔧 Custom Source: OSV (Open Source Vulnerabilities)
Built a Coral source spec for Google's OSV database — the first 
open-source vulnerability intelligence source for Coral. No auth 
needed, works out of the box.

🧑‍💻 Background:
8+ years building multi-vendor security integrations (CrowdStrike, 
SentinelOne, Defender, QRadar). This project solves a real problem 
I've lived with: cross-platform security signal correlation.

📸 Screenshots: [attached below]
📝 Blog: [Medium link]
🔗 Repo: https://github.com/SamChawla/devsecops-coral

Built solo by @sumit_sd | PyData Indore organizer
```

### Screenshots to Attach (Capture During Days 4-6)

Prepare these screenshots/GIFs while building:

| # | Screenshot | What It Shows | When to Capture |
|---|---|---|---|
| 1 | `scan` command output | Full security posture table with severity colors | Day 4 |
| 2 | `correlate` command output | Vulnerability-error correlation with 🔴/🟡/🟢 signals | Day 4 |
| 3 | `timeline` command output | Unified cross-source event timeline | Day 4 |
| 4 | `ask` natural language query | Agent translating English → SQL → formatted result | Day 4 |
| 5 | Cross-source JOIN query | Raw Coral SQL showing 4-5 source JOIN | Day 2 |
| 6 | `coral source test osv` passing | Proof the custom source spec works | Day 2 |
| 7 | Architecture diagram | Clean visual of the system components | Day 5 |

### GIF Recording (High Impact)

A 15-20 second GIF of the CLI in action is worth more than 5 static screenshots.

```bash
# Install terminalizer for GIF recording
npm install -g terminalizer

# Record a session
terminalizer record demo --skip-sharing

# In the session, run:
devsecops-coral scan --ecosystem PyPI --packages django,flask,requests
# Wait for output, then:
devsecops-coral correlate --since 7d
# Wait for output, then Ctrl+D

# Render to GIF
terminalizer render demo --output demo.gif

# Alternative: use asciinema (lighter weight)
asciinema rec demo.cast
# ... run commands ...
# Convert to GIF with agg:
agg demo.cast demo.gif
```

---

## Part 2: LinkedIn Post

### Post Template

```
🪸 Built a security intelligence agent in 7 days — 
and it replaces 30 minutes of manual work with one SQL query.

For the Pirates of the Coral-bean hackathon by @WeMakeDevs and @Coral,
I built devsecops-coral: an AI agent that correlates security signals 
across your entire DevSecOps stack.

The problem I've lived with for years:

When a vulnerability is discovered, you check 5 different dashboards — 
OSV for CVEs, GitHub for deploys, Sentry for errors, Jira for tickets, 
Grafana for infrastructure. You manually piece together the story. 
Senior engineers do it in 20 minutes. Junior engineers miss connections 
entirely.

The solution:

One Coral SQL query that JOINs all 5 sources. No ETL, no warehouse, 
no glue code. Everything runs locally.

What I built:
→ CLI tool with 4 commands: scan, correlate, timeline, ask
→ Custom OSV source spec (open-source vulnerability database as SQL)
→ AI agent that translates "Are we vulnerable?" into cross-source SQL
→ Rich terminal output with severity-colored tables

Built solo. Python + Coral + Claude API.

I also contributed the OSV source spec back to the Coral community — 
because every security team should be able to query vulnerability 
data as SQL.

📝 Blog: [Medium link]
🔗 Repo: [GitHub link]

#hackathon #devsecops #security #python #coral #opensource 
#wemakedevs #cybersecurity #ai #agents

@withcoral @WeMakeDevs
```

### LinkedIn Post Rules

- Tag **@withcoral** (Coral's LinkedIn company page) and **@WeMakeDevs**
- Include 1 screenshot or the demo GIF (LinkedIn supports GIFs up to 200MB)
- Post between 8-10 AM IST on a weekday for maximum visibility
- Do NOT tag employer or clients
- Use relevant hashtags: #hackathon #devsecops #python #coral #opensource
- Engage with comments within the first hour (algorithm boost)

---

## Part 3: X (Twitter) Post

### Tweet Template

```
🪸 Built a security intelligence agent for the @withcoral hackathon

One SQL query that JOINs:
• OSV (vulnerability database) — custom source I built
• GitHub (deploys)
• Sentry (errors)
• Jira (security tickets)
• Grafana (infrastructure)

Result: 30 min of manual cross-referencing → one query.

Built solo in 7 days. Python + Coral + Claude API.

📝 Blog: [link]
🔗 Repo: [link]

@WeMakeDevs #PiratesOfTheCoralBean
```

### X Post Rules

- Tag **@withcoral** and **@WeMakeDevs**
- Include the demo GIF or a screenshot (visual content gets 2x engagement)
- Keep under 280 characters if no media, or use a thread for the full story
- Post the same day as the Discord showcase for maximum momentum

---

## Part 4: Medium Blog Post (Captain's Log Bounty)

This earns a SEPARATE bounty (Keychron keyboard) AND supports the Tell the Tale showcase.

### Blog Post Outline

**Title:** "I Built a Cross-Stack Security Correlator with Coral + Claude — Here's How"

**Subtitle:** "From 5 vendor APIs and 30 minutes of manual work to one SQL query"

**Sections:**

1. **The Problem** (300 words)
   - Personal story: years of building multi-vendor security integrations
   - The daily pain: checking 5 dashboards after every vulnerability report
   - Why existing tools (SOAR, SIEM, custom scripts) don't solve this cleanly

2. **Why Coral** (200 words)
   - What Coral is (one-liner explanation)
   - Why it's different: SQL across any API, no ETL, runs locally
   - The "aha moment": realizing cross-source JOINs replace weeks of glue code

3. **Architecture** (300 words + diagram)
   - System diagram (CLI → Agent → Coral → Sources)
   - Why these 5 sources (OSV, GitHub, Sentry, Jira, Grafana)
   - Search functions vs tables in Coral

4. **Building the OSV Source Spec** (400 words + code)
   - Why OSV needed a custom source (not bundled)
   - Walking through the YAML: tables, functions, columns
   - The lint → add → test → query cycle
   - Show the test passing with real CVE data

5. **The Killer Query** (300 words + code)
   - Show the cross-source JOIN SQL
   - Walk through what each JOIN adds
   - Show the CLI output with severity colors

6. **What I Learned** (200 words)
   - Coral's DataFusion SQL engine (what works, what surprised me)
   - Source spec authoring tips for others
   - Where I'd take this project next

7. **Try It Yourself** (100 words)
   - Link to repo with quickstart
   - Link to Coral installation

**Total:** ~1,800 words + code blocks + screenshots

### Blog Post Rules

- Publish on Medium (your account)
- Include code blocks that are REPRODUCIBLE — someone should be able to follow along
- Include at least 3 screenshots
- End with links to the repo and Coral
- Cross-post the link to Discord #how-i-coral and LinkedIn

---

## Part 5: Demo Video (For Submission)

### Video Structure (3-5 minutes)

| Timestamp | Content | Duration |
|---|---|---|
| 0:00 | Intro: "I'm Sumit, Tech Lead Python, 8+ years in security integrations" | 20s |
| 0:20 | The Problem: "When a vulnerability is found, I check 5 dashboards..." | 40s |
| 1:00 | Live Demo: `devsecops-coral scan` | 45s |
| 1:45 | Live Demo: `devsecops-coral correlate --since 7d` | 45s |
| 2:30 | Show the SQL: "Here's what Coral actually does under the hood" | 30s |
| 3:00 | Custom OSV Source: "I built this source spec for the community" | 30s |
| 3:30 | Agent Demo: `devsecops-coral ask "Are there untracked vulnerabilities?"` | 30s |
| 4:00 | Wrap: "One query, 5 sources, zero glue code. Built in 7 days." | 20s |

### Recording Setup

- Screen recording: OBS (you already have it)
- Terminal: Use a clean profile with large font (16pt+)
- Resolution: 1920x1080 minimum
- No face-cam needed (optional)
- Clean desktop: no work tabs, no notifications, no VPN indicator
- Upload to YouTube (unlisted or public) and link in submission

---

## Timeline: When to Capture What

| Day | Capture | For |
|---|---|---|
| Day 1 | Screenshot: All 5 sources connected (`coral source list`) | Blog, Discord |
| Day 2 | Screenshot: First cross-source JOIN result | Blog, Discord |
| Day 2 | Screenshot: `coral source test osv` passing | Blog, Discord |
| Day 4 | GIF: Full CLI demo (scan → correlate → timeline) | Discord, LinkedIn, X |
| Day 4 | Screenshots: All 4 commands with colored output | Discord, Blog |
| Day 5 | Architecture diagram | README, Blog, Discord |
| Day 6 | Record demo video (3-5 min) | Submission |
| Day 6 | Write and publish Medium blog post | Captain's Log bounty |
| Day 6 | Post to Discord #how-i-coral | Tell the Tale bounty |
| Day 6 | Post to LinkedIn tagging @withcoral + @WeMakeDevs | Tell the Tale bounty |
| Day 6 | Post to X tagging @withcoral + @WeMakeDevs | Tell the Tale bounty |

---

## Checklist: Before Posting Anywhere

- [ ] No employer/client names visible anywhere
- [ ] No real credentials in screenshots or code blocks
- [ ] No work-related browser tabs visible in screenshots
- [ ] GIF/video shows only the demo repo, not any work repos
- [ ] Blog post is reproducible (someone can actually follow it)
- [ ] All links work (repo, blog, Coral docs)
- [ ] Tagged @withcoral and @WeMakeDevs on all social posts
- [ ] Demo uses real data (not placeholder text)
