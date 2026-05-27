# Teams App — Sideloading Instructions

## Prerequisites

1. A Microsoft 365 tenant with Teams admin rights (or "upload custom apps" permission enabled)
2. The Entra ID app registration `c4bd759d-f585-431b-b604-9ab2933d5a58` must have the Teams SSO redirect URI configured
3. Icon files (`color.png` 192x192, `outline.png` 32x32) in this directory

## Create Icons

Generate two PNG icons before sideloading. Recommended approach:

```powershell
# Using ImageMagick (install first: choco install imagemagick)
magick -size 192x192 xc:#1a2a44 -fill "#EDB059" -font Arial -pointsize 100 -gravity center -annotate 0 "AI" color.png
magick -size 32x32 xc:transparent -fill "#EDB059" -font Arial -pointsize 20 -gravity center -annotate 0 "AI" outline.png
```

Or use any image editor to create a 192x192 icon (`color.png`) and a 32x32 transparent icon (`outline.png`).

## Sideload the App

1. Open Microsoft Teams
2. Go to **Apps** (left sidebar) → **Manage your apps** → **Upload an app**
3. If "Upload an app" is not visible, enable it:
   - Teams Admin Center → Teams apps → Setup policies → Global → Upload custom apps = On
4. Select `manifest.json` from this directory
5. The app appears as a personal tab in the left sidebar

## Enable SSO (Optional)

For single sign-on so users see their own data:

1. In Azure Portal → Entra ID → App registrations → `aiagent2-graph-app-dev`
2. Under **Expose an API**, add the scope `access_as_user`
3. Under **Authentication**, add redirect URI for Teams: `https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect`
4. Set `ENABLE_TEAMS_SSO=true` in the orchestrator environment variables
5. Redeploy the orchestrator

Without SSO, the app uses demo data for all users. With SSO, each user's OneDrive and Outlook are accessed via their own identity.
