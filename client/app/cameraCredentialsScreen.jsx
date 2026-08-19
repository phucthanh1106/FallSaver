import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { setCameraConnection } from '../config/cameraConnection.js';
import supabase from "../config/supabaseClient.js";
import * as SecureStore from 'expo-secure-store';

export default function CameraCredentialsScreen() {
    const { ipv4 } = useLocalSearchParams();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const router = useRouter();

    const handleConnect = async () => {
        if (!username.trim() || !password) {
            setError('Enter both the username and password.');
            return;
        }

        // Get tge user in this session
        const { data: { user }, error: userError } = await supabase.auth.getUser();

        if (userError || !user) {
            setError('You must sign in before connecting cameras.');
            return;
        }

        const { data: connection, error: connectionError } = await supabase
            .from('camera_connections')
            .upsert({
                user_id: user.id,
                ipv4,
                username: username.trim(),
            }, { onConflict: 'user_id, ipv4' })
            .select('id')
            .single();
        


        if (connectionError || !connection) {
            console.warn('Failed to save camera connection:', connectionError);
            setError(connectionError?.message || 'Failed to save camera connection.');
            return;
        }

        await SecureStore.setItemAsync(`camera-password-${user.id}-${connection.id}`, password);

        setCameraConnection({
            connectionId: connection.id,
            ipv4,
            username: username.trim(),
            password,
        });

        router.dismissAll();
    };

    return (
        <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
                <Ionicons name="chevron-back" size={28} color="#1C1C1E" />
            </TouchableOpacity>

            <View style={styles.content}>
                <View style={styles.iconCircle}>
                    <Ionicons name="lock-closed-outline" size={32} color="#007AFF" />
                </View>
                <Text style={styles.title}>RTSP authentication</Text>
                <Text style={styles.subtitle}>Enter the login for the cameras at {ipv4}.</Text>

                <Text style={styles.label}>Username</Text>
                <TextInput value={username} onChangeText={value => { setUsername(value); setError(''); }} style={styles.input} placeholder="Camera username" autoCapitalize="none" autoCorrect={false} />

                <Text style={styles.label}>Password</Text>
                <View style={styles.passwordWrapper}>
                    <TextInput value={password} onChangeText={value => { setPassword(value); setError(''); }} style={styles.passwordInput} placeholder="Camera password" secureTextEntry={!showPassword} autoCapitalize="none" autoCorrect={false} />
                    <TouchableOpacity style={styles.eyeButton} onPress={() => setShowPassword(!showPassword)}>
                        <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={22} color="#6E6E73" />
                    </TouchableOpacity>
                </View>
                {error ? <Text style={styles.errorText}>{error}</Text> : null}

                <Text style={styles.securityNote}>Your login stays in memory while the app connects and is not placed in the navigation URL.</Text>

                <TouchableOpacity style={styles.connectButton} onPress={handleConnect}>
                    <Ionicons name="scan-outline" size={21} color="#FFF" />
                    <Text style={styles.connectText}>Connect and scan</Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#F8F9FB', paddingTop: 56 },
    backButton: { marginLeft: 20, width: 44, height: 44, justifyContent: 'center' },
    content: { flex: 1, paddingHorizontal: 24, paddingTop: 32 },
    iconCircle: { width: 64, height: 64, borderRadius: 32, backgroundColor: '#EAF4FF', justifyContent: 'center', alignItems: 'center', marginBottom: 22 },
    title: { fontSize: 28, fontWeight: '800', color: '#1C1C1E', marginBottom: 10 },
    subtitle: { fontSize: 15, lineHeight: 22, color: '#6E6E73', marginBottom: 32 },
    label: { fontSize: 14, fontWeight: '700', color: '#3A3A3C', marginBottom: 10 },
    input: { height: 54, borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF', paddingHorizontal: 16, fontSize: 16, color: '#1C1C1E', marginBottom: 20 },
    passwordWrapper: { height: 54, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF' },
    passwordInput: { flex: 1, height: '100%', paddingHorizontal: 16, fontSize: 16, color: '#1C1C1E' },
    eyeButton: { width: 50, height: '100%', justifyContent: 'center', alignItems: 'center' },
    errorText: { color: '#FF3B30', fontSize: 13, marginTop: 8 },
    securityNote: { fontSize: 13, lineHeight: 19, color: '#8E8E93', marginTop: 18, marginBottom: 30 },
    connectButton: { height: 56, borderRadius: 16, backgroundColor: '#007AFF', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
    connectText: { color: '#FFF', fontSize: 17, fontWeight: '700' },
});
