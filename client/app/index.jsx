import React, { useEffect, useState } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  FlatList, 
  Image,
  TouchableOpacity, 
  Dimensions,
  ActivityIndicator 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import supabase from "../config/supabaseClient.js";

const { width } = Dimensions.get('window');

export default function HomeScreen() {
    const [discoveredCameras, setDiscoveredCameras] = useState([]);
    const [isScanning, setIsScanning] = useState(false);
    const router = useRouter();

    // !!!!! THIS WILL DELETE ALL ROWS IN A TABLE
    const handleDeleteAll = async (category) => {
        const { data, error } = await supabase
            .from(category)
            .delete()
            .neq('id', 0)
        
        if (error) {
            console.log(error);
        }
        
        if (data) {
            console.log(data);
        }
    }

    /// Add new cameras to the database
    const handleAddCam = async (category, item) => {
        const { data, error } = await supabase
            .from(category)
            .insert([{ index: item.index, frame: item.frame }])

        if (error) {
            console.log(error);
        } 

        if (data) {
            console.log(data);
        }
    }

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

    const fetchDiscoveredCameras = async () => {
        setIsScanning(true);
        // handleDeleteAll("cameras");
        try {
            const response = await fetch('http://127.0.0.1:8000/api/cameras/scan');
            const data = await response.json();
            setDiscoveredCameras(data);
            // data.forEach(item => handleAddCam("cameras", item))
        } catch (err) {
            console.warn('Failed to scan cameras', err);
            setDiscoveredCameras([]);
        } finally {
            setIsScanning(false);
        }
    };

    useEffect(() => {
        fetchDiscoveredCameras();
    }, []);

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
                        <Text style={styles.discoveryText}>{item.name || `Camera ${item.id}`}</Text>
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
                <TouchableOpacity style={styles.profileBtn}>
                    <View style={styles.profileCircle}>
                        <Ionicons name="person-circle-outline" size={32} color="#1A1A1A" />
                    </View>
                </TouchableOpacity>
            </View>

            {/* Discovery Section */}
            <View style={styles.discoverySection}>
                <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>Available Cameras</Text>
                    <TouchableOpacity onPress={fetchDiscoveredCameras} disabled={isScanning}>
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
                        renderItem={renderCamPreview}
                        keyExtractor={item => item.index.toString()}
                        contentContainerStyle={styles.discoveryList}
                        numColumns={2} // Vertical grid like original, but for discovery
                        columnWrapperStyle={styles.row}
                    />
                ) : (
                    <View style={styles.emptyDiscovery}>
                        <Text style={styles.emptyText}>No cameras detected</Text>
                    </View>
                )}
            </View>
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
    discoveryList: { 
        paddingHorizontal: 20,
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
        fontWeight: '500' 
    },
});