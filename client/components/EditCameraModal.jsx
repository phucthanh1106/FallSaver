import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Image, Modal, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import supabase from '../config/supabaseClient.js';

export default function EditCameraModal({ visible, onClose, onCameraDeleted, onCameraUpdated }) {
    const [savedCameras, setSavedCameras] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [deletingCameraId, setDeletingCameraId] = useState(null);
    const [editingCameraId, setEditingCameraId] = useState(null);
    const [cameraName, setCameraName] = useState('');
    const [isSavingName, setIsSavingName] = useState(false);

    const fetchSavedCameras = async () => {
        setIsLoading(true);

        const { data, error } = await supabase
            .from('cameras')
            .select('id, index, frame, name')
            .order('index');

        if (error) {
            console.warn('Failed to load saved cameras:', error);
            Alert.alert('Could not load cameras', error.message);
            setSavedCameras([]);
        } else {
            setSavedCameras(data || []);
        }

        setIsLoading(false);
    };

    useEffect(() => {
        if (visible) {
            fetchSavedCameras();
        }
    }, [visible]);

    const deleteCamera = async (camera) => {
        setDeletingCameraId(camera.id);

        const { data, error } = await supabase
            .from('cameras')
            .delete()
            .eq('id', camera.id)
            .select('id');

        setDeletingCameraId(null);

        if (error) {
            console.warn('Failed to delete camera:', error);
            Alert.alert('Could not delete camera', error.message);
            return;
        }

        if (!data || data.length === 0) {
            Alert.alert('Could not delete camera', 'Check that your cameras table has a DELETE RLS policy for the signed-in user.');
            return;
        }

        setSavedCameras(currentCameras => currentCameras.filter(item => item.id !== camera.id));
        onCameraDeleted?.(camera);
    };

    const confirmDelete = (camera) => {
        Alert.alert('Delete camera?', `Camera ${camera.index} will be removed from Supabase.`, [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: () => deleteCamera(camera) },
        ]);
    };

    const startEditingName = (camera) => {
        setEditingCameraId(camera.id);
        setCameraName(camera.name || `Camera ${camera.index}`);
    };

    const cancelEditingName = () => {
        setEditingCameraId(null);
        setCameraName('');
    };

    const saveCameraName = async (camera) => {
        const cleanName = cameraName.trim();

        if (!cleanName) {
            Alert.alert('Enter a camera name');
            return;
        }

        setIsSavingName(true);

        const { data, error } = await supabase
            .from('cameras')
            .update({ name: cleanName })
            .eq('id', camera.id)
            .select('id, index, frame, name')
            .single();

        setIsSavingName(false);

        if (error) {
            console.warn('Failed to update camera name:', error);
            Alert.alert('Could not update camera name', error.message);
            return;
        }

        setSavedCameras(currentCameras => currentCameras.map(item => item.id === camera.id ? data : item));
        onCameraUpdated?.(data);
        cancelEditingName();
    };

    const renderCamera = ({ item }) => {
        const previewUri = item.frame ? `data:image/jpeg;base64,${item.frame}` : null;
        const isDeleting = deletingCameraId === item.id;
        const isEditing = editingCameraId === item.id;

        return (
            <View style={styles.cameraCard}>
                <View style={styles.imageWrapper}>
                    {previewUri ? (
                        <Image source={{ uri: previewUri }} style={styles.previewImage} resizeMode="cover" />
                    ) : (
                        <View style={styles.previewPlaceholder}>
                            <Ionicons name="videocam-outline" size={28} color="#8E8E93" />
                            <Text style={styles.previewPlaceholderText}>No preview</Text>
                        </View>
                    )}
                </View>

                <View style={styles.cameraInfo}>
                    {isEditing ? (
                        <View style={styles.editNameContainer}>
                            <TextInput value={cameraName} onChangeText={setCameraName} style={styles.nameInput} placeholder="Camera name" autoFocus maxLength={50} />
                            <View style={styles.editActions}>
                                <TouchableOpacity style={styles.cancelButton} onPress={cancelEditingName} disabled={isSavingName}>
                                    <Text style={styles.cancelButtonText}>Cancel</Text>
                                </TouchableOpacity>
                                <TouchableOpacity style={styles.saveButton} onPress={() => saveCameraName(item)} disabled={isSavingName}>
                                    {isSavingName ? <ActivityIndicator size="small" color="#FFF" /> : <Text style={styles.saveButtonText}>Save</Text>}
                                </TouchableOpacity>
                            </View>
                        </View>
                    ) : (
                        <>
                            <View style={styles.cameraTitleContainer}>
                                <Text style={styles.cameraName}>{item.name || `Camera ${item.index}`}</Text>
                                <Text style={styles.cameraIndex}>Channel {item.index}</Text>
                            </View>

                            <View style={styles.cameraActions}>
                                <TouchableOpacity style={styles.renameButton} onPress={() => startEditingName(item)} accessibilityLabel={`Rename camera ${item.index}`}>
                                    <Ionicons name="pencil-outline" size={20} color="#007AFF" />
                                </TouchableOpacity>
                                <TouchableOpacity style={styles.deleteButton} onPress={() => confirmDelete(item)} disabled={isDeleting} accessibilityLabel={`Delete camera ${item.index}`}>
                                    {isDeleting ? (
                                        <ActivityIndicator size="small" color="#FF3B30" />
                                    ) : (
                                        <Ionicons name="trash-outline" size={21} color="#FF3B30" />
                                    )}
                                </TouchableOpacity>
                            </View>
                        </>
                    )}
                </View>
            </View>
        );
    };

    return (
        <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
            <View style={styles.modalContainer}>
                <View style={styles.header}>
                    <View>
                        <Text style={styles.title}>Manage Cameras</Text>
                        <Text style={styles.subtitle}>Delete cameras saved to your account</Text>
                    </View>

                    <TouchableOpacity onPress={onClose} accessibilityLabel="Close camera manager">
                        <Text style={styles.doneButton}>Done</Text>
                    </TouchableOpacity>
                </View>

                {isLoading ? (
                    <View style={styles.centerContent}>
                        <ActivityIndicator size="large" color="#007AFF" />
                    </View>
                ) : (
                    <FlatList
                        data={savedCameras}
                        renderItem={renderCamera}
                        keyExtractor={item => item.id.toString()}
                        contentContainerStyle={savedCameras.length > 0 ? styles.cameraList : styles.emptyList}
                        ListEmptyComponent={
                            <View style={styles.centerContent}>
                                <Ionicons name="videocam-off-outline" size={44} color="#C7C7CC" />
                                <Text style={styles.emptyTitle}>No saved cameras</Text>
                                <Text style={styles.emptyText}>Cameras saved to Supabase will appear here.</Text>
                            </View>
                        }
                    />
                )}
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    modalContainer: { flex: 1, backgroundColor: '#F8F9FB' },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 18, backgroundColor: '#FFF', borderBottomWidth: 1, borderBottomColor: '#E5E5EA' },
    title: { fontSize: 20, fontWeight: '700', color: '#1C1C1E' },
    subtitle: { marginTop: 3, fontSize: 13, color: '#8E8E93' },
    doneButton: { color: '#007AFF', fontWeight: '600', fontSize: 17 },
    cameraList: { padding: 20, paddingBottom: 40 },
    emptyList: { flexGrow: 1 },
    cameraCard: { marginBottom: 16, overflow: 'hidden', borderRadius: 18, borderWidth: 1, borderColor: '#E5E5EA', backgroundColor: '#FFF', shadowColor: '#000', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.07, shadowRadius: 7, elevation: 2 },
    imageWrapper: { width: '100%', height: 150, backgroundColor: '#F2F2F7' },
    previewImage: { width: '100%', height: '100%' },
    previewPlaceholder: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 6 },
    previewPlaceholderText: { color: '#8E8E93', fontSize: 13 },
    cameraInfo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16 },
    cameraTitleContainer: { flex: 1 },
    cameraName: { fontSize: 16, fontWeight: '700', color: '#1C1C1E' },
    cameraIndex: { marginTop: 3, fontSize: 12, color: '#8E8E93' },
    cameraActions: { flexDirection: 'row', gap: 10 },
    renameButton: { width: 42, height: 42, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#EAF3FF' },
    deleteButton: { width: 42, height: 42, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#FFF1F0' },
    editNameContainer: { flex: 1 },
    nameInput: { height: 46, paddingHorizontal: 13, borderWidth: 1, borderColor: '#C7C7CC', borderRadius: 12, backgroundColor: '#FFF', fontSize: 16, color: '#1C1C1E' },
    editActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 12 },
    cancelButton: { height: 40, justifyContent: 'center', paddingHorizontal: 16, borderRadius: 11, backgroundColor: '#E5E5EA' },
    cancelButtonText: { color: '#3A3A3C', fontWeight: '600' },
    saveButton: { minWidth: 72, height: 40, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, borderRadius: 11, backgroundColor: '#007AFF' },
    saveButtonText: { color: '#FFF', fontWeight: '700' },
    centerContent: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 30 },
    emptyTitle: { marginTop: 14, fontSize: 17, fontWeight: '700', color: '#1C1C1E' },
    emptyText: { marginTop: 6, textAlign: 'center', fontSize: 14, color: '#8E8E93' },
});
