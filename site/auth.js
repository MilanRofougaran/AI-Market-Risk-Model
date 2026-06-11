// ============================================================================
//  auth.js — shared Supabase connection + login helpers for all pages
//  The publishable key is SAFE to ship in the browser (that's its purpose).
//  Row Level Security on the database is what actually protects user data.
// ============================================================================
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

export const SUPABASE_URL = "https://dvumbokdimvagyuovhxk.supabase.co";
const SUPABASE_KEY = "sb_publishable_dS-IeIaFNhgaEK7Pzfvznw_anrc688K";

export const sb = createClient(SUPABASE_URL, SUPABASE_KEY);

// who's logged in right now? (null if nobody)
export async function currentUser() {
  const { data } = await sb.auth.getUser();
  return data?.user ?? null;
}

// use at the top of pages that require login — bounces guests to the login page
export async function requireAuth(redirectTo = "login.html") {
  const user = await currentUser();
  if (!user) { window.location.href = redirectTo; return null; }
  return user;
}

export async function signOut(toPage = "login.html") {
  await sb.auth.signOut();
  window.location.href = toPage;
}
