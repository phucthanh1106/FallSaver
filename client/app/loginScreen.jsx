import React, { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View, Image} from 'react-native';
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router';
import supabase from '../config/supabaseClient.js';

export default function LoginScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();

    const handleLogin = async () => {
        if (!email.trim() || !password) {
            setError('Enter both your email and password.');
            return;
        }

        setIsLoading(true);
        setError('');
        const { error: loginError } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
        setIsLoading(false);

        if (loginError) {
            setError(loginError.message);
            return;
        }

        router.replace('/');
    };

    return (
        <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <View style={styles.content}>
                <View style={styles.iconCircle}>
                   <Image 
                        source={"../assets/fallsaver_icon.png"} 
                        style={styles.icon} 
                        resizeMode="contain" 
                    />
                </View>
                <Text style={styles.appName}>Fall Saver</Text>
                <Text style={styles.title}>Welcome back</Text>
                <Text style={styles.subtitle}>Sign in to view your household cameras.</Text>

                <Text style={styles.label}>Email</Text>
                <TextInput value={email} onChangeText={value => { setEmail(value); setError(''); }} style={styles.input} placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" autoCorrect={false} textContentType="emailAddress" />

                <Text style={styles.label}>Password</Text>
                <View style={styles.passwordWrapper}>
                    <TextInput value={password} onChangeText={value => { setPassword(value); setError(''); }} style={styles.passwordInput} placeholder="Your password" secureTextEntry={!showPassword} autoCapitalize="none" autoCorrect={false} textContentType="password" />
                    <TouchableOpacity style={styles.eyeButton} onPress={() => setShowPassword(!showPassword)}>
                        <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={22} color="#6E6E73" />
                    </TouchableOpacity>
                </View>

                {error ? <Text style={styles.errorText}>{error}</Text> : null}

                <TouchableOpacity style={[styles.primaryButton, isLoading && styles.disabledButton]} onPress={handleLogin} disabled={isLoading}>
                    {isLoading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.primaryButtonText}>Sign in</Text>}
                </TouchableOpacity>

                <View style={styles.footerRow}>
                    <Text style={styles.footerText}>Don't have an account?</Text>
                    <TouchableOpacity onPress={() => router.push('/signUpScreen')}>
                        <Text style={styles.footerLink}>Sign up</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#F8F9FB' },
    content: { flex: 1, justifyContent: 'center', paddingHorizontal: 26 },
    iconCircle: { width: 70, height: 70, borderRadius: 35, backgroundColor: '#EAF4FF', alignItems: 'center', justifyContent: 'center', alignSelf: 'center', marginBottom: 14 },
    icon: {width: 38, height: 38},
    appName: { textAlign: 'center', color: '#007AFF', fontSize: 16, fontWeight: '800', marginBottom: 24 },
    title: { fontSize: 30, fontWeight: '800', color: '#1C1C1E', marginBottom: 8 },
    subtitle: { color: '#6E6E73', fontSize: 15, lineHeight: 22, marginBottom: 30 },
    label: { color: '#3A3A3C', fontSize: 14, fontWeight: '700', marginBottom: 9 },
    input: { height: 54, borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF', paddingHorizontal: 16, fontSize: 16, color: '#1C1C1E', marginBottom: 20 },
    passwordWrapper: { height: 54, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF' },
    passwordInput: { flex: 1, height: '100%', paddingHorizontal: 16, fontSize: 16, color: '#1C1C1E' },
    eyeButton: { width: 50, height: '100%', alignItems: 'center', justifyContent: 'center' },
    errorText: { color: '#FF3B30', fontSize: 13, marginTop: 9 },
    primaryButton: { height: 56, borderRadius: 16, backgroundColor: '#007AFF', alignItems: 'center', justifyContent: 'center', marginTop: 24 },
    disabledButton: { opacity: 0.65 },
    primaryButtonText: { color: '#FFF', fontSize: 17, fontWeight: '700' },
    footerRow: { flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: 24 },
    footerText: { color: '#6E6E73', fontSize: 14 },
    footerLink: { color: '#007AFF', fontSize: 14, fontWeight: '700' },
});
