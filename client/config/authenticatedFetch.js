import supabase from './supabaseClient.js';

export async function authenticatedFetch(url, options = {}) {
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    throw new Error('You must sign in first.');
  }

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${session.access_token}`,
    },
  });
}