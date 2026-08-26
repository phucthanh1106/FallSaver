// Load the backend URL from Expo's environment variables.
const API_URL = process.env.EXPO_PUBLIC_API_URL;

if (!API_URL) {
    throw new Error('EXPO_PUBLIC_API_URL is missing');
}

// Remove a trailing slash so API paths can safely start with one.
export default API_URL.replace(/\/$/, '');
