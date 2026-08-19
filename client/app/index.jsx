import React, { useCallback, useEffect, useState } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  FlatList, 
  Image,
  TouchableOpacity, 
  Dimensions,
  ActivityIndicator,
  Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { getCameraConnection, clearCameraConnection } from '../config/cameraConnection.js';
import supabase from "../config/supabaseClient.js";
import { authenticatedFetch } from '../config/authenticatedFetch.js';
import EditCameraModal from '../components/EditCameraModal.jsx';
import * as SecureStore from 'expo-secure-store';

const { width } = Dimensions.get('window');

export default function HomeScreen() {
    const [discoveredCameras, setDiscoveredCameras] = useState([]);
    const [isScanning, setIsScanning] = useState(false);
    const [isEditModalVisible, setIsEditModalVisible] = useState(false);
    const router = useRouter();

    // Load saved previews. Only scan live cameras when shouldRefreshFrames is true.
    const fetchSavedCameras = useCallback(async (shouldRefreshFrames = false) => {
        setIsScanning(true);

        try {
            // Load the last saved previews directly from Supabase.
            const { data: savedCameras, error: savedError } = await supabase
                .from('cameras')
                .select('id, index, name, frame, connection_id')
                .order('index');

            if (savedError) {
                throw savedError;
            }

            const cameras = savedCameras || [];
            setDiscoveredCameras(savedCameras);

            // Login stops here. Manual refresh continues below.
            if (!shouldRefreshFrames || cameras.length === 0) {
                return cameras;
            }

            const { data: { user }, error: userError } = await supabase.auth.getUser();

            if (userError || !user) {
                throw new Error('You must sign in before refreshing cameras.');
            }

            const connectionIds = [...new Set(cameras.map(camera => camera.connection_id).filter(Boolean))];

            const scanResults = await Promise.all(connectionIds.map(async connectionId => {
                const password = await SecureStore.getItemAsync(`camera-password-${user.id}-${connectionId}`);

                try {
                    const response = await authenticatedFetch('http://127.0.0.1:8000/api/cameras/scan/saved', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ connection_id: connectionId, password: password || null}),
                    }, 60000);

                    if (!response.ok) {
                        return [];
                    }

                    return await response.json();
                } catch (scanError) {
                    console.warn(`Could not refresh connection ${connectionId}:`, scanError);
                    return [];
                }
            }));

            const scannedCameras = scanResults.flat();

            if (scannedCameras.length === 0) {
                Alert.alert('Cameras offline', 'Showing the last saved previews.');
                return cameras;
            }

            // Save the fresh frames.
            try {
                await Promise.all(scannedCameras.map(async camera => {
                    const { error } = await supabase
                        .from('cameras')
                        .update({ frame: camera.frame })
                        .eq('id', camera.id)
                        .eq('user_id', user.id);

                    if (error) {
                        throw error;
                    }
                }));
            } catch (saveError) {
                console.warn('Fresh frames could not be saved:', saveError);
            }

            // Keep old previews for connections that failed.
            const scannedCamerasById = new Map(scannedCameras.map(camera => [camera.id, camera]));

            const camerasToDisplay = cameras.map(camera => {
                return scannedCamerasById.get(camera.id) || camera;
            });
            
            setDiscoveredCameras(camerasToDisplay);
            return camerasToDisplay;
        } catch (error) {
            console.warn('Failed to load cameras:', error);

            if (shouldRefreshFrames) {
                Alert.alert('Cameras offline', 'Showing the last saved previews.');
            } else {
                setDiscoveredCameras([]);
            }

            return [];
        } finally {
            setIsScanning(false);
        }
    }, []);

    // This is for the refresh button in home screen
    const fetchDiscoveredCameras = useCallback(async () => {
        const connection = getCameraConnection();
        
        setIsScanning(true);
        try {
            if (!connection) {
                await fetchSavedCameras(true);
                return;
            }

            const response = await authenticatedFetch('http://127.0.0.1:8000/api/cameras/scan', connection ? {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(connection),
            } : {}, 60000);

            if (!response.ok) {
                throw new Error(`Camera scan failed with status ${response.status}`);
            }

            const data = await response.json();

            if (data.length === 0) {
                Alert.alert('Cameras offline', 'Showing the last saved previews.');
                await fetchSavedCameras();
                return;
            }

            setDiscoveredCameras(data);

            if (data.length > 0) {
                try {
                    await handleAddCameras(data);
                } catch (saveError) {
                    console.warn('Cameras were detected but could not be saved:', saveError);
                }
            }
        } catch (err) {
            console.warn('Failed to scan cameras', err);
            Alert.alert('Cameras offline', 'Showing the last saved previews.');
            await fetchSavedCameras();
        } finally {
            setIsScanning(false);
        }
    }, [fetchSavedCameras]);

    // This runs when the home screen first mounted and when references in fetchSavedCameras change
    useEffect(() => {
        fetchSavedCameras();
    }, [fetchSavedCameras]);

    // -----------------------------------Basic funtions for the home screen-----------------------------------
    const handleSignOut = () => {
        Alert.alert('Sign out', 'Do you want to sign out of Fall Saver?', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Sign out', style: 'destructive', onPress: async () => {
                clearCameraConnection();
                await supabase.auth.signOut();
            }}
        ]);
    };

    // Add newly discovered cameras to the database
    const handleAddCameras = async (cameras) => {

        const { data: { user }, error: userError } = await supabase.auth.getUser();

        if (userError || !user) {
            throw new Error('You must sign in before saving cameras.');
        }

        const connection = getCameraConnection();

        if (!connection?.connectionId) {
            throw new Error('No camera connection is selected.');
        }

        const cameraRows = cameras.map(camera => ({
            user_id: user.id,
            index: camera.index,
            frame: camera.frame,
            connection_id: connection.connectionId,
        }));

        const { error } = await supabase
            .from('cameras')
            .upsert(cameraRows, { onConflict: 'user_id,connection_id,index' });

        if (error) {
            throw error;
        }
    };

    // When click on a preview of a camera, navigate the user to a page that displays that camera live
    const handleGoToLiveFeed = async (item) => {
        router.push({
            // router.push('cameraFeed') // sometimes works, but safer to use:
            pathname: '/cameraFeedScreen',
            params: {
                cameraIndex: item.index,
                cameraName: item.name,
            },
        })
        console.log("router push working properly")
    }

    // Deleting a camera
    const handleCameraDeleted = (deletedCamera) => {
        setDiscoveredCameras(currentCameras => currentCameras.filter(camera => camera.id !== deletedCamera.id));
    };

    // Updating a camera
    const handleCameraUpdated = (updatedCamera) => {
        setDiscoveredCameras(currentCameras => currentCameras.map(camera => camera.id === updatedCamera.id ? { ...camera, name: updatedCamera.name } : camera));
    };

    const renderCamPreview = ({ item }) => {
        const previewUri = item.frame
            ? `data:image/jpeg;base64,${item.frame}`
            : null;
        
        return (
            <TouchableOpacity 
                style={styles.discoveryCard} 
                onPress={() => handleGoToLiveFeed(item)}
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
                        <Text style={styles.discoveryText}>{item.name || `Camera ${item.index}`}</Text>
                    </View>
                </View>
            </TouchableOpacity>
        );
    };

    return (
        <View style={styles.container}>
            {/* Header Area */}
            <View style={styles.topBar}>
                <View>
                    <Text style={styles.welcomeText}>Welcome Home,</Text>
                    <Text style={styles.headerTitle}>Fall Saver</Text>
                </View>
                <TouchableOpacity style={styles.profileBtn} onPress={handleSignOut}>
                    <View style={styles.profileCircle}>
                        <Ionicons name="person-circle-outline" size={32} color="#1A1A1A" />
                    </View>
                </TouchableOpacity>
            </View>

            {/* Discovery Section */}
            <View style={styles.discoverySection}>
                <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>Available Cameras</Text>
                    <View style={styles.sectionActions}>
                        <TouchableOpacity onPress={() => router.push('/cameraAddressScreen')} disabled={isScanning}>
                            <Ionicons name="add-circle-outline" size={22} color="#007AFF" />
                        </TouchableOpacity>
                        <TouchableOpacity onPress={fetchDiscoveredCameras} disabled={isScanning}>
                            {isScanning ? (
                                <ActivityIndicator size="small" color="#007AFF" />
                            ) : (
                                <Ionicons name="refresh" size={20} color="#007AFF" />
                            )}
                        </TouchableOpacity>
                    </View>
                </View>

                {discoveredCameras && discoveredCameras.length > 0 ? (
                    <FlatList
                        data={discoveredCameras}
                        renderItem={renderCamPreview}
                        keyExtractor={item => item.index.toString()}
                        contentContainerStyle={styles.discoveryList}
                        numColumns={2} // Vertical grid like original, but for discovery
                        columnWrapperStyle={styles.row}
                    />
                ) : (
                    <View style={styles.emptyDiscovery}>
                        <Text style={styles.emptyText}>No cameras detected</Text>
                        <TouchableOpacity style={styles.connectButton} onPress={() => router.push('/cameraAddressScreen')}>
                            <Ionicons name="add" size={20} color="#FFF" />
                            <Text style={styles.connectButtonText}>Connect cameras</Text>
                        </TouchableOpacity>
                    </View>
                )}
            </View>

            <TouchableOpacity style={styles.editButton} onPress={() => setIsEditModalVisible(true)} accessibilityLabel="Manage saved cameras">
                <Ionicons name="pencil" size={24} color="#FFF" />
            </TouchableOpacity>

            <EditCameraModal visible={isEditModalVisible} onClose={() => setIsEditModalVisible(false)} onCameraDeleted={handleCameraDeleted} onCameraUpdated={handleCameraUpdated} />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F8F9FB',
    },
    topBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        paddingHorizontal: 25,
        paddingTop: 60,
        paddingBottom: 20,
        backgroundColor: '#32b4e3', // lighter blue banner
        borderBottomWidth: 1,
        borderBottomColor: '#B7D4FF',
    },
    welcomeText: {
        fontSize: 14,
        color: '#1D477D', // darker blue text
        fontWeight: '500',
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: '800',
        color: '#d3dae3', // strong contrast against blue
    },
    profileBtn: {
        justifyContent: 'center',
        alignItems: 'center',
    },
    profileCircle: {
        width: 42,
        height: 42,
        borderRadius: 26,
        backgroundColor: '#ffffff',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#0A3D7E',
        shadowOpacity: 0.08,
        shadowOffset: { width: 0, height: 3 },
        shadowRadius: 6,
        elevation: 2,
    },
    discoverySection: {
        flex: 1,
        backgroundColor: '#FFF',
        paddingTop: 24,
        paddingBottom: 24,
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
        letterSpacing: 0.5,
        textTransform: 'uppercase'
    },
    sectionActions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
    },
    discoveryList: { 
        paddingHorizontal: 20,
        paddingBottom: 90,
    },
    row: {
        justifyContent: 'space-between',
        marginBottom: 20,
    },
    discoveryCard: {
        backgroundColor: '#FFF',
        borderRadius: 18,
        width: (width - 60) / 2, // Match original column width
        marginBottom: 20, 
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
    cardContent: {
        padding: 14,
    },
    discoveryInfo: { 
        flexDirection: 'row', 
        alignItems: 'center', 
        marginBottom: 2 
    },
    discoveryText: { 
        fontSize: 15, 
        fontWeight: '700', 
        color: '#1C1C1E',
        flex: 1,
        marginLeft: 6
    },
    discoverySubtext: { 
        fontSize: 12, 
        color: '#8E8E93', 
        fontWeight: '500',
        marginLeft: 26
    },
    emptyDiscovery: { 
        paddingHorizontal: 20, 
        paddingVertical: 20,
        alignItems: 'center'
    },
    emptyText: { 
        color: '#C7C7CC', 
        fontSize: 14, 
        fontWeight: '500',
        marginBottom: 18,
    },
    connectButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: '#007AFF',
        paddingHorizontal: 18,
        height: 46,
        borderRadius: 14,
    },
    connectButtonText: {
        color: '#FFF',
        fontSize: 15,
        fontWeight: '700',
    },
    editButton: {
        position: 'absolute',
        right: 22,
        bottom: 28,
        width: 58,
        height: 58,
        borderRadius: 29,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#007AFF',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.2,
        shadowRadius: 7,
        elevation: 6,
    },
});
