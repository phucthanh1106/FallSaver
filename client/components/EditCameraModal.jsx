import { 
  Modal, 
  View, 
  Text, 
  FlatList, 
  Image,
  TouchableOpacity, 
  StyleSheet, 
  ActivityIndicator 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import supabase from "../config/supabaseClient.js";


export default function EditCameraModal({ visible, onClose }) {
    const [discoveredCameras, setDiscoveredCameras] = useState(null)
    const [isScanning, setIsScanning] = useState(false);

    const fetchDiscoveredCameras = async () => {
        setIsScanning(true);
        try {
            const response = await fetch('http://127.0.0.1:8000/api/cameras/scan');
            const data = await response.json();
            setDiscoveredCameras(data);
            console.log(data);
        } catch (err) {
            console.warn('Failed to scan cameras', err);
            setDiscoveredCameras([]);
        } finally {
            setIsScanning(false);
        }
    };

    // Scan for cameras right away when the modal is mounted
    useEffect(() => {
        if (visible) {
            fetchDiscoveredCameras();
        }
    }, [visible]); // Only runs when the 'visible' prop changes (modal opens)


    // Handle refresh button to rescan available cameras
    const handleRefresh = async () => { 
        await fetchDiscoveredCameras();
    };

    // Handle refresh button to rescan available cameras
    const handleAddCamera = async (item) => { 
        const { data, error } = await supabase
            .from('cameras')
            .insert()
    };

    const handleDelete = (id) => { /* Your Supabase Delete Logic */ };
    const handleUpdate = (id) => { /* Your Supabase Update Logic */ };

    // Renders the new cameras found on the network/USB
    const renderDiscoveryItem = ({ item }) => {
        const previewUri = item.frame
            ? `data:image/jpeg;base64,${item.frame}`
            : null;
        
        return (
            <TouchableOpacity 
                style={styles.discoveryCard} 
                onPress={() => handleAddCamera(item)}
            >
                <View style={styles.imageWrapper}>
                    {previewUri ? (
                        <Image
                            source={{ uri: previewUri }}
                            style={styles.previewImage}
                            resizeMode="cover"
                        />
                    ) : (
                        <View style={styles.previewPlaceholder}>
                            <Text style={styles.previewPlaceholderText}>
                                No preview
                            </Text>
                        </View>
                    )}
                </View>

                <View style={styles.cardContent}>
                    <View style={styles.discoveryInfo}>
                        <Ionicons name="add-circle" size={20} color="#007AFF" />
                        <Text style={styles.discoveryText}>{item.name || `Camera ${item.id}`}</Text>
                    </View>
                    <Text style={styles.discoverySubtext}>{item.resolution || item.uri || 'Local camera'}</Text>
                </View>
            </TouchableOpacity>
        );
    };


    return (
        <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
            <View style={styles.modalContainer}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.title}>Camera Manager</Text>
                    <TouchableOpacity onPress={onClose}>
                        <Text style={styles.doneBtn}>Done</Text>
                    </TouchableOpacity>
                </View>

                {/* 1. DISCOVERY SECTION (Scanner) */}
                <View style={styles.discoverySection}>
                    <View style={styles.sectionHeader}>
                        <Text style={styles.sectionTitle}>Available Cameras</Text>
                        <TouchableOpacity onPress={handleRefresh} disabled={isScanning}>
                            {isScanning ? (
                                <ActivityIndicator size="small" color="#007AFF" />
                            ) : (
                                <Ionicons name="refresh" size={20} color="#007AFF" />
                            )}
                        </TouchableOpacity>
                    </View>

                    {discoveredCameras && discoveredCameras.length > 0 ? (
                        <FlatList
                            data={discoveredCameras}
                            renderItem={renderDiscoveryItem}
                            keyExtractor={item => item.id.toString()}
                            contentContainerStyle={styles.discoveryList}
                            scrollEnabled={true}
                        />
                    ) : (
                        <View style={styles.emptyDiscovery}>
                            <Text style={styles.emptyText}>No new cameras detected</Text>
                        </View>
                    )}
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    modalContainer: { flex: 1, backgroundColor: '#F8F9FB' },
    header: { 
        flexDirection: 'row', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 16,
        backgroundColor: '#FFF',
        borderBottomWidth: 1,
        borderBottomColor: '#F2F2F7',
    },
    title: { fontSize: 19, fontWeight: '700', color: '#1C1C1E' },
    doneBtn: { color: '#007AFF', fontWeight: '600', fontSize: 17 },
    
    discoverySection: {
        backgroundColor: '#FFF',
        paddingTop: 24,
        paddingBottom: 24,
        borderBottomWidth: 1,
        borderBottomColor: '#F2F2F7',
        flex: 1,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        marginBottom: 16,
    },
    sectionTitle: { 
        fontSize: 13, 
        fontWeight: '700', 
        color: '#8E8E93', 
        letterSpacing: 0.5 
    },
    discoveryList: { 
        paddingHorizontal: 15,
        paddingBottom: 8, // Room for shadow
    },
    discoveryCard: {
        backgroundColor: '#FFF',
        borderRadius: 18,
        marginHorizontal: 6,
        width: '100%',
        marginBottom: 20, 
        // Soft Shadow
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.08,
        shadowRadius: 8,
        elevation: 3,
        borderWidth: 1,
        borderColor: '#F2F2F7',
    },
    imageWrapper: {
        width: '100%',
        height: 124,
        borderTopLeftRadius: 18,
        borderTopRightRadius: 18,
        overflow: 'hidden',
        backgroundColor: '#F2F2F7',
    },
    previewImage: {
        width: '100%',
        height: '100%',
    },
    previewPlaceholder: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
    },
    previewPlaceholderText: {
        color: '#8E8E93',
        fontSize: 11,
        fontWeight: '500',
    },
    newBadge: {
        position: 'absolute',
        top: 8,
        left: 8,
        backgroundColor: '#007AFF',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    newBadgeText: {
        color: '#FFF',
        fontSize: 10,
        fontWeight: '800',
    },
    cardContent: {
        padding: 14,
    },
    discoveryInfo: { 
        flexDirection: 'row', 
        justifyContent: 'space-between',
        alignItems: 'center', 
        marginBottom: 2 
    },
    discoveryText: { 
        fontSize: 15, 
        fontWeight: '700', 
        color: '#1C1C1E',
        flex: 1,
        marginRight: 4
    },
    discoverySubtext: { 
        fontSize: 12, 
        color: '#8E8E93', 
        fontWeight: '500' 
    },
    emptyDiscovery: { 
        paddingHorizontal: 20, 
        paddingVertical: 20,
        alignItems: 'center'
    },
    emptyText: { 
        color: '#C7C7CC', 
        fontSize: 14, 
        fontWeight: '500' 
    },
});