# Clerk Authentication Setup

## Quick Start

1. **Create a Clerk Application**
   - Go to https://dashboard.clerk.com
   - Create a new application
   - Choose "Email" and any OAuth providers you want (Google, GitHub, etc.)

2. **Get Your API Keys**
   - In Clerk Dashboard, go to "API Keys"
   - Copy the Publishable Key and Secret Key

3. **Set Environment Variables**
   - Copy `.env.example` to `.env.local`
   - Add your Clerk keys:
   ```
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   ```

4. **Run the Application**
   ```bash
   npm run dev
   ```

## How It Works

- **Public Pages**: All pages are public by default (posts, notes, home)
- **Protected Pages**: `/admin/*` routes require authentication
- **User Management**: Clerk handles all user creation, OAuth, passwords, etc.
- **Sign In**: Click "Sign In" button in header or go to `/sign-in`

## Admin Access

### Step 1: Configure Session Token (REQUIRED - One time setup)

1. Go to Clerk Dashboard > Sessions
2. Click "Edit" under Session Token
3. Add this to include public metadata in the token:
   ```json
   {
     "metadata": "{{user.public_metadata}}"
   }
   ```
4. Save the configuration

### Step 2: Grant Admin Role to Users

1. Go to Clerk Dashboard > Users
2. Find the user and click on them
3. Edit their Public Metadata and add:
   ```json
   {
     "role": "admin"
   }
   ```
4. Save changes
5. User must sign out and sign back in for changes to take effect

The user will now have access to `/admin` routes.

## Features Included

- ✅ Email/password authentication
- ✅ OAuth (Google, GitHub, etc.)
- ✅ Session management
- ✅ Automatic account linking (same email)
- ✅ Password reset
- ✅ Email verification
- ✅ User profile management

## No Backend Changes Needed

For now, the backend remains unchanged. When we're ready to verify JWT tokens from Clerk on the backend, we'll:
1. Use Clerk's JWKS endpoint to verify tokens
2. Sync user data on first API call
3. Check user roles from JWT claims

But for the MVP, the frontend auth is sufficient!