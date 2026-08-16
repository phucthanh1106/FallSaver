import { Stack } from 'expo-router';

export default function Layout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="cameraFeedScreen" options={{ headerShown: false }} />
      <Stack.Screen name="cameraAddressScreen" options={{ headerShown: false }} />
      <Stack.Screen name="cameraCredentialsScreen" options={{ headerShown: false }} />
    </Stack>
  );
}
