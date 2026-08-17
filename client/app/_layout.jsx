import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Stack, useRouter, useSegments } from 'expo-router';
import supabase from '../config/supabaseClient.js';

export default function Layout() {
  const [session, setSession] = useState(undefined);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: currentSession } }) => {
      setSession(currentSession);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      setSession(currentSession);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (session === undefined) {
      return;
    }

    const isAuthScreen = segments[0] === 'loginScreen' || segments[0] === 'signUpScreen';
    if (!session && !isAuthScreen) {
      router.replace('/loginScreen');
    } else if (session && isAuthScreen) {
      router.replace('/');
    }
  }, [session, segments, router]);

  if (session === undefined) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="loginScreen" options={{ headerShown: false }} />
      <Stack.Screen name="signUpScreen" options={{ headerShown: false }} />
      <Stack.Screen name="cameraFeedScreen" options={{ headerShown: false }} />
      <Stack.Screen name="cameraAddressScreen" options={{ headerShown: false }} />
      <Stack.Screen name="cameraCredentialsScreen" options={{ headerShown: false }} />
    </Stack>
  );
}

const styles = StyleSheet.create({
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#F8F9FB' },
});
