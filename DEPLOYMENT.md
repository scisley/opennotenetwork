# Deployment Guide for OpenNoteNetwork

This guide covers deploying the OpenNoteNetwork MVP with the backend on Fly.io and frontend on Vercel.

## Architecture Overview

- **Backend (FastAPI)**: Deployed on Fly.io at `https://opennotenetwork-api.fly.dev`
- **Frontend (Next.js)**: Deployed on Vercel at `https://opennotenetwork.com` (or `https://opennotenetwork.vercel.app`)
- **Database**: PostgreSQL on Neon (already configured)

## Prerequisites

1. Install Fly CLI: `brew install flyctl` (Mac) or see [fly.io/docs/hands-on/install-flyctl](https://fly.io/docs/hands-on/install-flyctl)
2. Install Vercel CLI: `npm i -g vercel`
3. Have accounts on:
   - [Fly.io](https://fly.io)
   - [Vercel](https://vercel.com)
   - Domain registrar (optional - Vercel provides a free `.vercel.app` domain)

## Step 1: Deploy Backend to Fly.io

### 1.1 Pre-deployment Checks

```bash
cd api

# Test the build locally first
npm run build

# Fix any TypeScript errors before proceeding
```

### 1.2 Login and Create App

```bash
# Login to Fly (opens browser)
flyctl auth login

# Create the app (one-time setup)
flyctl apps create opennotenetwork-api
```

### 1.3 Set Environment Variables

We've created a helper script to make this easier:

```bash
# This script reads from .env.local and uploads to Fly.io
bash deploy-secrets.sh
```

Or manually set them:

```bash
# The script above does this automatically, but here's what it does:
cat .env.local | grep -v '^#\|^$\|ALLOWED_' | \
    sed 's/ENVIRONMENT=development/ENVIRONMENT=production/' | \
    sed 's/PRODUCTION=false/PRODUCTION=true/' | \
    sed 's/"//g' | \
    flyctl secrets import
```

### 1.4 Deploy to Fly.io

```bash
# Deploy
flyctl deploy

# Note: You may see a warning about "not listening on expected address"
# This can be safely ignored if the health check passes
```

### 1.5 Verify Deployment

```bash
# Check app status
flyctl status

# View logs
flyctl logs

# Test health endpoint
curl https://opennotenetwork-api.fly.dev/health
# Should return: {"status":"healthy","version":"1.0.0"}

# Test API endpoint
curl "https://opennotenetwork-api.fly.dev/api/public/posts?limit=1"
```

## Step 2: Deploy Frontend to Vercel

### 2.1 Pre-deployment Fixes

Before deploying, ensure your code handles Next.js requirements:

```typescript
// For pages using useSearchParams(), wrap in Suspense:
import { Suspense } from "react";

function PageContent() {
  const searchParams = useSearchParams();
  // ... rest of component
}

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PageContent />
    </Suspense>
  );
}
```

### 2.2 Test Build Locally

```bash
cd web

# Test the build locally to catch errors
npm run build

# Fix any TypeScript errors before proceeding
# Common issues:
# - Missing 'any' type annotations
# - useSearchParams needs Suspense boundary
```

### 2.3 Login and Create Project

```bash
# Login to Vercel (opens browser)
vercel login

# Link to project (one-time setup)
vercel link

# When prompted:
# - Set up and deploy? Yes
# - Select scope: Your account
# - Link to existing project? No
# - Project name: opennotenetwork
# - Directory with code: ./
# - Want to modify settings? No
```

### 2.4 Set Environment Variables

```bash
# Add environment variables via CLI
echo "https://opennotenetwork-api.fly.dev" | vercel env add NEXT_PUBLIC_API_URL production
echo "pk_test_..." | vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY production
echo "sk_test_..." | vercel env add CLERK_SECRET_KEY production

# List environment variables to verify
vercel env ls
```

**Important**: Do NOT set environment variables in `vercel.json` - use the CLI or dashboard instead.

### 2.5 Deploy to Vercel

```bash
# Deploy to production
vercel --prod

# Force rebuild if environment variables were changed
vercel --prod --force
```

### 2.6 Your Frontend URLs

After deployment, you'll have:

- **Stable URL**: `https://opennotenetwork.vercel.app` (always works)
- **Preview URLs**: `https://opennotenetwork-[hash].vercel.app` (for each deployment)
- **Custom Domain**: `https://opennotenetwork.com` (after DNS setup)

## Step 3: Configure Custom Domain (Optional)

### 3.1 Frontend Domain Setup

**In Vercel:**

```bash
vercel domains add opennotenetwork.com
```

**In your domain registrar (e.g., Namecheap):**

| Type         | Host | Value                | TTL       |
| ------------ | ---- | -------------------- | --------- |
| A Record     | @    | 76.76.21.21          | Automatic |
| CNAME Record | www  | cname.vercel-dns.com | Automatic |

### 3.2 Backend Domain (Optional)

For now, using `https://opennotenetwork-api.fly.dev` is perfectly fine. If you want a custom domain later:

```bash
flyctl certs add api.opennotenetwork.com
# Then add the provided IPs to your DNS
```

### 3.3 Update CORS After Domain Setup

Once your domain is working, update the backend CORS:

```python
# In api/app/config.py
allowed_origins: List[str] = [
    "https://opennotenetwork.com",
    "https://www.opennotenetwork.com",
    "https://opennotenetwork.vercel.app",  # Keep Vercel URL
    "http://localhost:3000",  # For local dev
]
```

Then redeploy:

```bash
cd api && flyctl deploy
```

## Common Issues and Solutions

### Backend Updates

```bash
cd api

# Make changes, then:
flyctl deploy

# View logs if needed
flyctl logs
```

### Frontend Updates

```bash
cd web

# Make changes, test locally:
npm run build

# Deploy:
vercel --prod

# Or connect GitHub for automatic deploys on push
```

### Update Environment Variables

**Fly.io:**

```bash
# Update a single secret
flyctl secrets set KEY="value"

# Or use the deploy-secrets.sh script for bulk updates
bash deploy-secrets.sh
```

**Vercel:**

```bash
# Remove old value
vercel env rm VARIABLE_NAME production

# Add new value
echo "new-value" | vercel env add VARIABLE_NAME production

# Redeploy to use new values
vercel --prod --force
```

## Monitoring

### Backend Monitoring

```bash
# View logs
flyctl logs

# SSH into container
flyctl ssh console

# Check status
flyctl status

# View dashboard
flyctl dashboard
```

### Frontend Monitoring

- Vercel Dashboard: https://vercel.com/dashboard
- Function Logs: Available in dashboard
- Analytics: Built into Vercel dashboard

## Rollback Procedures

### Backend Rollback

```bash
# List releases
flyctl releases

# Rollback to specific version
flyctl releases rollback v[NUMBER]
```

### Frontend Rollback

Via Vercel Dashboard:

1. Go to Deployments tab
2. Find previous working deployment
3. Click "..." → "Promote to Production"

## Security Checklist

- ✅ Environment variables set via secure methods (not in code)
- ✅ CORS configured for specific domains
- ✅ TrustedHostMiddleware disabled (Fly.io proxy handles this)
- ✅ HTTPS enforced on both frontend and backend
- ✅ Database URL properly formatted for async operations
- ✅ API keys and secrets not exposed in logs

## Quick Reference

```bash
# Deploy backend
cd api && flyctl deploy

# Deploy frontend
cd web && vercel --prod

# Check backend logs
flyctl logs

# Check backend health
curl https://opennotenetwork-api.fly.dev/health

# Update backend secrets
cd api && bash deploy-secrets.sh

# Update frontend env vars
vercel env add VARIABLE_NAME production

# Force frontend rebuild
vercel --prod --force
```

## Troubleshooting Checklist

If something isn't working:

1. **Backend not responding?**

   - Check logs: `flyctl logs`
   - Verify secrets: `flyctl secrets list`
   - Test health: `curl https://opennotenetwork-api.fly.dev/health`

2. **Frontend showing errors?**

   - Check browser console for CORS errors
   - Verify env vars: `vercel env ls`
   - Check build logs in Vercel dashboard

3. **Database issues?**

   - Check DATABASE_URL format (needs `postgresql+asyncpg://` for async)
   - Verify Neon is not suspended (free tier auto-suspends)

4. **CORS errors?**
   - Update allowed_origins in `api/app/config.py`
   - Redeploy backend: `flyctl deploy`

---

**Pro Tips:**

- Always test builds locally before deploying
- Use stable Vercel URL (`projectname.vercel.app`) during development
- Keep `localhost` in CORS for easy local development
- The deploy-secrets.sh script saves time and reduces errors
- Fly.io's default domain works great - custom domain is optional
