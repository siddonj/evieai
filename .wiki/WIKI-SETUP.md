# Azure DevOps Wiki Setup

> Instructions for setting up this wiki in Azure DevOps

## What's in This Wiki

The `/.wiki/` folder contains complete documentation for EvieAI formatted for Azure DevOps wiki.

**Pages included:**
- `/.wiki/Home.md` — Navigation hub and quick links
- `/.wiki/Getting-Started.md` — 5-minute quick start
- `/.wiki/Features.md` — Complete feature list and capabilities
- `/.wiki/Architecture.md` — System design and component breakdown
- `/.wiki/Deployment-Configuration.md` — Environment variables and multi-client setup
- `/.wiki/Deployment-Checklist.md` — Step-by-step deployment guide
- `/.wiki/Infrastructure.md` — Terraform and IaC management
- `/.wiki/Operations.md` — Daily operations, monitoring, alerting
- `/.wiki/Service-Restart.md` — Admin dashboard and API restart procedures
- `/.wiki/Troubleshooting.md` — Common issues and fixes
- `/.wiki/Disaster-Recovery.md` — Emergency procedures and recovery
- `/.wiki/API-Reference.md` — REST API endpoints and examples

---

## Publishing to Azure DevOps Wiki

### Option 1: Using Azure DevOps Portal (Easiest)

**Step 1: Create Wiki in DevOps**
1. Azure DevOps project → Wiki
2. Click "Publish Code as Wiki"
3. Select repo: `evieai`
4. Select branch: `main`
5. Select folder: `/.wiki`
6. Click "Publish"

**Step 2: Done!**
- Wiki automatically syncs with `/.wiki/` folder
- Changes in Git automatically update wiki
- Wiki updates automatically reflected in Git

### Option 2: Manual Upload (If not using Git)

1. Azure DevOps project → Wiki
2. Click "Create project wiki"
3. For each markdown file in `.wiki/`:
   - Copy file name (e.g., `Home.md`)
   - Copy content
   - Create page in wiki with same name
   - Paste content
   - Save

---

## Wiki Navigation

### Home Page
Users land on [[Home]] which provides:
- Quick navigation by role (new users, operators, deployers, developers)
- Links to all documentation pages
- Key capabilities overview
- Common questions with answers

### Role-Based Learning Paths

**For New Users (10 minutes):**
1. [[Getting-Started]] — Run local development version
2. [[Features]] — See what's possible
3. [[Architecture]] — Understand high-level design

**For Deployers (1.5 hours):**
1. [[Deployment-Configuration]] — Set environment variables
2. [[Deployment-Checklist]] — Follow step-by-step guide
3. [[Troubleshooting]] — Fix deployment issues

**For Operators (2 hours):**
1. [[Operations]] — Learn daily procedures
2. [[Service-Restart]] — Understand restart functionality
3. [[Monitoring & Alerting]] — Set up alerts
4. [[Disaster-Recovery]] — Know emergency procedures

**For Developers (2+ hours):**
1. [[Architecture]] — Understand system design
2. [[API-Reference]] — Learn REST endpoints
3. [[Infrastructure]] — Understand Terraform
4. [[Troubleshooting]] — Debug issues

---

## Using WikiLinks in Azure DevOps

Azure DevOps wiki uses `[[Page-Name]]` syntax for internal links:

```markdown
# Example

See [[Getting-Started]] for quick start instructions.

For troubleshooting, check [[Troubleshooting]].

Deploy using [[Deployment-Checklist]].
```

**Important:** Use exact page names (case-sensitive):
- ✅ `[[Getting-Started]]` — Correct
- ❌ `[[getting-started]]` — Wrong (case)
- ❌ `[[Getting Started]]` — Wrong (spaces)

---

## Updating Wiki Pages

### Option 1: Edit in Azure DevOps UI (Easiest)

1. Wiki → select page
2. Click "Edit" (pencil icon)
3. Make changes in editor
4. Click "Save"
5. Changes auto-sync to `/.wiki/` folder in Git

### Option 2: Edit in Git & Push

1. Edit `/.wiki/Page-Name.md` locally
2. Commit: `git commit -m "Update documentation"`
3. Push: `git push`
4. Changes appear in Azure DevOps wiki within 30 seconds

---

## Adding New Pages

### In Azure DevOps UI

1. Wiki → Click "+" (New page)
2. Enter page name (e.g., "Multi-Region-Setup")
3. Add content
4. Save
5. Page appears in wiki + new file created in `/.wiki/` folder

### In Git

1. Create new file: `/.wiki/New-Page-Name.md`
2. Add markdown content
3. Commit: `git commit -m "Add New-Page-Name documentation"`
4. Push: `git push`
5. Page appears in Azure DevOps wiki

**Note:** File name must match wiki page name exactly (case-sensitive).

---

## Best Practices

### Naming Pages
- ✅ Use hyphens for spaces: `Multi-Client-Setup`
- ✅ Capitalize first word: `Getting-Started`
- ✅ Keep names short: `API-Reference` not `API-Reference-for-REST-Endpoints`

### Writing Content
- Start with one-sentence summary at top
- Use headings to organize sections
- Include code examples with languages specified
- Add troubleshooting sections for common issues
- Link to other pages using `[[Page-Name]]`

### Updating Structure
- Keep `Home.md` as entry point
- Update navigation links when adding pages
- Remove broken wiki links
- Keep table of contents in Home.md current

---

## Syncing with Repository

The wiki is stored in Git, so it's version controlled:

```bash
# View wiki changes
cd /.wiki/
git log --oneline

# See what changed in Home.md
git diff HEAD~1 Home.md

# Revert to previous version
git checkout HEAD~1 -- Home.md
git commit -m "Revert Home.md to previous version"
git push
```

---

## Troubleshooting Wiki

### Wiki Pages Don't Appear
- [ ] Check `/.wiki/` folder exists in Git
- [ ] Files have `.md` extension
- [ ] File names match wiki page names exactly (case-sensitive)
- [ ] Run `git push` to sync changes
- [ ] Wait 30 seconds for DevOps to pick up changes

### WikiLinks Return 404
- [ ] Check page exists: `ls /.wiki/`
- [ ] Check exact spelling: `[[Page-Name]]` (case-sensitive)
- [ ] Remove spaces: `[[Getting-Started]]` not `[[Getting Started]]`

### Can't Edit Wiki
- [ ] Ensure you have Contribute permission on repo
- [ ] Check branch is not protected or frozen
- [ ] Try editing in Git instead of UI

### Images Not Showing
- [ ] Upload images to `/.wiki/` folder
- [ ] Link with: `![Alt text](Image-Name.png)`
- [ ] Use relative paths only

---

## Wiki Archive

All documentation is also stored in:
- `docs/` folder (markdown format)
- `README.md` (quick start)
- `ARCHITECTURE.md` (system design)

These are kept in sync with the wiki.

---

## Support

For wiki issues:
- **Azure DevOps Help:** https://docs.microsoft.com/en-us/azure/devops/project/wiki/
- **Markdown Guide:** https://docs.microsoft.com/en-us/azure/devops/project/wiki/markdown-guidance
- **Contact:** DevOps team or platform lead

---

## Next Steps

1. **Publish to Azure DevOps:** Follow "Publishing to Azure DevOps Wiki" above
2. **Share with team:** Send link to Home page
3. **Gather feedback:** Monitor wiki usage, update based on questions
4. **Keep current:** Update docs when features change

**Wiki Home Page:** `{your-devops-project}/wiki/Home`

---

**Created:** May 29, 2026  
**Version:** 1.5  
**Status:** Ready for DevOps Publication
