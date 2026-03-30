import { createClient } from '@supabase/supabase-js'
import 'react-native-url-polyfill/auto';
import * as SecureStore from 'expo-secure-store';

// 1. Define the adapter to bridge Expo and Supabase
const ExpoSecureStoreAdapter = {
  getItem: (key) => {
    return SecureStore.getItemAsync(key);
  },
  setItem: (key, value) => {
    return SecureStore.setItemAsync(key, value);
  },
  removeItem: (key) => {
    return SecureStore.deleteItemAsync(key);
  },
};

// Expo will only "leak" environment variables to your frontend code if they start with EXPO_PUBLIC_.
const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY

// Don't export instantly, do it on the last line since export instantly might create race condition
// the way JavaScript handles the "Export/Import" chain can sometimes cause index.js to try and read the variable before the file has finished "setting" it.
const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: ExpoSecureStoreAdapter,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
})

export default supabase

