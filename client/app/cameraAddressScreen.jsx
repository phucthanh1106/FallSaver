import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { setCameraConnection } from '../config/cameraConnection.js';

function isPrivateIpv4(value) {
    const parts = value.trim().split('.').map(Number);
    if (parts.length !== 4 || parts.some(part => !Number.isInteger(part) || part < 0 || part > 255)) {
        return false;
    }

    return parts[0] === 10 || (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) || (parts[0] === 192 && parts[1] === 168);
}

export default function CameraAddressScreen() {
    const [ipv4, setIpv4] = useState('');
    const [needsAuthentication, setNeedsAuthentication] = useState(false);
    const [error, setError] = useState('');
    const router = useRouter();

    const handleContinue = () => {
        const cleanIpv4 = ipv4.trim();
        if (!isPrivateIpv4(cleanIpv4)) {
            setError('Enter a private IPv4 address, such as 192.168.1.9.');
            return;
        }

        if (needsAuthentication) {
            router.push({ pathname: '/cameraCredentialsScreen', params: { ipv4: cleanIpv4 } });
            return;
        }

        setCameraConnection({ ipv4: cleanIpv4 });
        router.dismissAll();
    };

    return (
        <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
                <Ionicons name="chevron-back" size={28} color="#1C1C1E" />
            </TouchableOpacity>

            <View style={styles.content}>
                <View style={styles.iconCircle}>
                    <Ionicons name="videocam-outline" size={34} color="#007AFF" />
                </View>
                <Text style={styles.title}>Connect your cameras</Text>
                <Text style={styles.subtitle}>Enter the private IPv4 address used by your cameras.</Text>

                <Text style={styles.label}>Private IPv4 address</Text>
                <TextInput
                    value={ipv4}
                    onChangeText={value => {
                        setIpv4(value);
                        setError('');
                    }}
                    style={[styles.input, error && styles.inputError]}
                    placeholder="192.168.1.9"
                    keyboardType="decimal-pad"
                    autoCapitalize="none"
                    autoCorrect={false}
                />
                {error ? <Text style={styles.errorText}>{error}</Text> : null}

                <Text style={styles.label}>Does the RTSP stream require authentication?</Text>
                <View style={styles.choiceRow}>
                    <TouchableOpacity style={[styles.choiceButton, !needsAuthentication && styles.choiceButtonSelected]} onPress={() => setNeedsAuthentication(false)}>
                        <Ionicons name={!needsAuthentication ? 'radio-button-on' : 'radio-button-off'} size={20} color={!needsAuthentication ? '#007AFF' : '#8E8E93'} />
                        <Text style={styles.choiceText}>No</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={[styles.choiceButton, needsAuthentication && styles.choiceButtonSelected]} onPress={() => setNeedsAuthentication(true)}>
                        <Ionicons name={needsAuthentication ? 'radio-button-on' : 'radio-button-off'} size={20} color={needsAuthentication ? '#007AFF' : '#8E8E93'} />
                        <Text style={styles.choiceText}>Yes</Text>
                    </TouchableOpacity>
                </View>

                <TouchableOpacity style={styles.continueButton} onPress={handleContinue}>
                    <Text style={styles.continueText}>Continue</Text>
                    <Ionicons name="arrow-forward" size={20} color="#FFF" />
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
    input: { height: 54, borderWidth: 1, borderColor: '#D1D1D6', borderRadius: 14, backgroundColor: '#FFF', paddingHorizontal: 16, fontSize: 17, color: '#1C1C1E', marginBottom: 8 },
    inputError: { borderColor: '#FF3B30' },
    errorText: { color: '#FF3B30', fontSize: 13, marginBottom: 18 },
    choiceRow: { flexDirection: 'row', gap: 12, marginBottom: 32 },
    choiceButton: { flex: 1, height: 54, flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 16, borderRadius: 14, borderWidth: 1, borderColor: '#D1D1D6', backgroundColor: '#FFF' },
    choiceButtonSelected: { borderColor: '#007AFF', backgroundColor: '#F0F7FF' },
    choiceText: { fontSize: 16, fontWeight: '600', color: '#1C1C1E' },
    continueButton: { height: 56, borderRadius: 16, backgroundColor: '#007AFF', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
    continueText: { color: '#FFF', fontSize: 17, fontWeight: '700' },
});
