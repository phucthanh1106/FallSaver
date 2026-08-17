import React, { useState } from 'react';
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import supabase from '../config/supabaseClient.js';

export default function SignUpScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();

    const handleSignUp = async () => {
        if (!email.trim() || !password || !confirmPassword) {
            setError('Complete all fields.');
            return;
        }

        if (password.length < 6) {
            setError('Password must contain at least 6 characters.');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        setIsLoading(true);
        setError('');
        const { data, error: signUpError } = await supabase.auth.signUp({ email: email.trim(), password });
        setIsLoading(false);

        if (signUpError) {
            setError(signUpError.message);
            return;
        }

        if (data.session) {
            router.replace('/');
            return;
        }

        Alert.alert('Check your email', 'Open the confirmation link, then return to Fall Saver and sign in.');
        router.replace('/loginScreen');
    };

    return (
        <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
                <Ionicons name="chevron-back" size={28} color="#1C1C1E" />
            </TouchableOpacity>

            <View style={styles.content}>
                <Text style={styles.title}>Create your account</Text>
                <Text style={styles.subtitle}>Save your household camera setup and access it again later.</Text>

                <Text style={styles.label}>Email</Text>
                <TextInput value={email} onChangeText={value => { setEmail(value); setError(''); }} style={styles.input} placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" autoCorrect={false} textContentType="emailAddress" />

                <Text style={styles.label}>Password</Text>
                <View style={styles.passwordWrapper}>
                    <TextInput value={password} onChangeText={value => { setPassword(value); setError(''); }} style={styles.passwordInput} placeholder="At least 6 characters" secureTextEntry={!showPassword} autoCapitalize="none" autoCorrect={false} textContentType="newPassword" />
                    <TouchableOpacity style={styles.eyeButton} onPress={() => setShowPassword(!showPassword)}>
                        <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={22} color="#6E6E73" />
                    </TouchableOpacity>
                </View>

                <Text style={styles.label}>Confirm password</Text>
                <TextInput value={confirmPassword} onChangeText={value => { setConfirmPassword(value); setError(''); }} style={styles.input} placeholder="Enter your password again" secureTextEntry={!showPassword} autoCapitalize="none" autoCorrect={false} textContentType="newPassword" />

                {error ? <Text style={styles.errorText}>{error}</Text> : null}

                <TouchableOpacity style={[styles.primaryButton, isLoading && styles.disabledButton]} onPress={handleSignUp} disabled={isLoading}>
                    {isLoading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.primaryButtonText}>Create account</Text>}
                </TouchableOpacity>

                <View style={styles.footerRow}>
                    <Text style={styles.footerText}>Already have an account?</Text>
                    <TouchableOpacity onPress={() => router.replace('/loginScreen')}>
                        <Text style={styles.footerLink}>Sign in</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#F8F9FB', paddingTop: 56 },
    backButton: { marginLeft: 20, width: 44, height: 44, justifyContent: 'center' },
    content: { flex: 1, justifyContent: 'center', paddingHorizontal: 26, paddingBottom: 48 },
    title: { fontSize: 30, fontWeight: '800', color: '#1C1C1E', marginBottom: 8 },
    subtitle: { color: '#6E6E73', fontSize: 15, lineHeight: 22, marginBottom: 28 },
    label: { color: '#3A3A3C', fontSize: 14, fontWeight: '700', marginBottom: 9 },
    input: { height: 54, borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF', paddingHorizontal: 16, fontSize: 16, color: '#1C1C1E', marginBottom: 18 },
    passwordWrapper: { height: 54, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF', marginBottom: 18 },
    passwordInput: { flex: 1, height: '100%', paddingHorizontal: 16, fontSize: 16, color: '#1C1C1E' },
    eyeButton: { width: 50, height: '100%', alignItems: 'center', justifyContent: 'center' },
    errorText: { color: '#FF3B30', fontSize: 13 },
    primaryButton: { height: 56, borderRadius: 16, backgroundColor: '#007AFF', alignItems: 'center', justifyContent: 'center', marginTop: 22 },
    disabledButton: { opacity: 0.65 },
    primaryButtonText: { color: '#FFF', fontSize: 17, fontWeight: '700' },
    footerRow: { flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: 22 },
    footerText: { color: '#6E6E73', fontSize: 14 },
    footerLink: { color: '#007AFF', fontSize: 14, fontWeight: '700' },
});
