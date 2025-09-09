import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Define TypeScript type for our custom claims
declare global {
  interface CustomJwtSessionClaims {
    metadata?: {
      role?: string;
    };
  }
}

// Define which routes require admin access
const isAdminRoute = createRouteMatcher([
  "/admin(.*)",
  "/posts/(.*)/manage"
]);

export default clerkMiddleware(async (auth, req) => {
  // Protect admin routes
  if (isAdminRoute(req)) {
    const { userId, sessionClaims } = await auth();
    
    // Check if user is signed in
    if (!userId) {
      return NextResponse.redirect(new URL("/sign-in", req.url));
    }
    
    // Check for admin role in public metadata
    // According to Clerk docs, public metadata is available as sessionClaims.metadata
    const userRole = (sessionClaims as any)?.metadata?.role;
    
    if (userRole !== "admin") {
      // User is signed in but not an admin - redirect to home
      return NextResponse.redirect(new URL("/", req.url));
    }
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
