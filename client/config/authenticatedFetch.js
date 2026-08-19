import supabase from './supabaseClient.js';

export async function authenticatedFetch(url, options = {}, timeoutMs = 15000) {
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    throw new Error('You must sign in first.');
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${session.access_token}`,
      },
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}
