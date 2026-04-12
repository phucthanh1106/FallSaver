import React, { useEffect, useState } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  FlatList, 
  TouchableOpacity, 
  Dimensions 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import EditCameraModal from './EditCameraModal.jsx';
import supabase from "../config/supabaseClient.js";

const { width } = Dimensions.get('window');
const COLUMN_WIDTH = (width - 60) / 2; // Perfect spacing for a 2-column grid

export default function HomeScreen() {
    const [cameras, setCameras] = useState(null);
    const [isEditing, setIsEditing] = useState(false); // Toggle for the FAB
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [fetchError, setFetchError] = useState(null);

    useEffect(() => {
        const fetchCameras = async () => {
            // Select everything from table "cameras"
            const { data, error } = await supabase.from('cameras').select();
            if (error) {
                setFetchError("Could not fetch cameras");
                setCameras([]);
            } 
            if (data) {
                setCameras(data);
                setFetchError(null);
            }
        };
        fetchCameras();
    }, []); 

    // Open the modal that scans new cameras to be added to the list
    const handleOpenAddCamera = async () => {
        setIsModalVisible(true);
    };

    const handleFabPress = () => { 
        setIsEditing(!isEditing);
    };

    const displayData = cameras ? [...cameras, { id: 'ADD_BUTTON' }] : [];
    const renderCameraCard = ({ item }) => {
        // RENDER THE "BIG PLUS" CARD
        if (item.id === 'ADD_BUTTON') {
            return (
                <TouchableOpacity 
                    style={[styles.cameraCard, styles.addCard]} 
                    onPress={(handleOpenAddCamera)}
                >
                    {/* Inner Wrapper to center the button in the middle of the card */}
                    <View style={styles.addCardContent}>
                        <View style={styles.shadowCircle}>
                            <View style={styles.blackCircle}>
                                <Ionicons name="add" size={36} color="black" />
                            </View>
                        </View>
                    </View>
                </TouchableOpacity>
            );
        }

        // RENDER THE NORMAL CAMERA CARD
        return (
            <TouchableOpacity 
                style={[styles.cameraCard, isEditing && styles.editingCard]}
                onLongPress={() => setIsEditing(true)}
            >
                {isEditing && (
                    <TouchableOpacity 
                        style={styles.deleteBadge} 
                        onPress={() => handleDeleteCamera(item.id)}
                    >
                        <Ionicons name="close" size={16} color="white" />
                    </TouchableOpacity>
                )}

                <View style={styles.cardHeader}>
                    <View style={[styles.iconCircle, { backgroundColor: item.status === 'Active' ? '#E8F5E9' : '#F5F5F5' }]}>
                        <Ionicons 
                            name="videocam" 
                            size={22} 
                            color={item.status === 'Active' ? "#4CAF50" : "#8E8E93"} 
                        />
                    </View>

                </View>

                <View style={styles.cardFooter}>
                    <Text style={styles.cameraName} numberOfLines={1}>{item.location}</Text>
                    <View style={styles.statusRow}>
                        <View style={[styles.statusDot, { backgroundColor: item.status === 'Active' ? '#4CAF50' : '#9E9E9E' }]} />
                        <Text style={styles.statusText}>{item.status}</Text>
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
                    <Ionicons name="person-circle-outline" size={32} color="#1A1A1A" />
                </TouchableOpacity>
            </View>

            {/* Grid List */}
            <FlatList
                data={displayData}
                renderItem={renderCameraCard}
                keyExtractor={item => item.id.toString()}
                numColumns={2}
                columnWrapperStyle={styles.row}
                contentContainerStyle={styles.listPadding}
                ListEmptyComponent={<Text style={styles.emptyText}>No cameras added yet.</Text>}
            />

            {/* The Morphing Pro FAB */}
            <TouchableOpacity 
                style={[styles.fab, isEditing ? styles.fabDone : styles.fabAdd]} 
                onPress={handleFabPress}
            >
                <Ionicons 
                    name={isEditing ? "checkmark-sharp" : "create-outline"} 
                    size={32} 
                    color="white" 
                />
            </TouchableOpacity>

            <EditCameraModal 
                visible={isModalVisible} 
                onClose={() => setIsModalVisible(false)} 
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F8F9FB', // Modern light grey
    },
    topBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        paddingHorizontal: 25,
        paddingTop: 60,
        paddingBottom: 20,
        backgroundColor: '#FFF',
    },
    welcomeText: {
        fontSize: 14,
        color: '#8E8E93',
        fontWeight: '500',
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: '800',
        color: '#1A1A1A',
    },
    listPadding: {
        paddingHorizontal: 20,
        paddingTop: 20,
    },
    row: {
        justifyContent: 'space-between',
    },
    cameraCard: {
        width: COLUMN_WIDTH,
        backgroundColor: '#FFF',
        borderRadius: 24,
        padding: 16,
        marginBottom: 20,
        height: 160,
        justifyContent: 'space-between',
        position: 'relative',
        // High-end soft shadow
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.05,
        shadowRadius: 10,
        elevation: 2,
    },
    deleteBadge: {
        position: 'absolute',
        top: -10,      // Pulls it above the card top
        right: -10,    // Pulls it past the card right
        backgroundColor: '#FF3B30', // System Red
        width: 28,
        height: 28,
        borderRadius: 14,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 3,
        borderColor: '#F8F9FB', // Match this to your background color for a "cutout" look
        zIndex: 10,     // Ensures it stays on top of the card
        elevation: 5,   // Shadow for Android
    },
    miniEditBtn: {
        backgroundColor: '#007AFF',
        width: 24,
        height: 24,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    editingCard: {
        borderWidth: 2,
        borderColor: '#007AFF',
        backgroundColor: '#F0F7FF',
    },
    addCard: {
        width: COLUMN_WIDTH,
        height: 160,
        backgroundColor: '#FFF',
        borderRadius: 24,
        marginBottom: 20,
        borderStyle: 'dashed',
        borderWidth: 1.5,
        borderColor: '#D1D1D6',
        justifyContent: 'center',
        alignItems: 'center',
    },
    addCardContent: {
        alignItems: 'center',
        justifyContent: 'center',
    },
    shadowCircle: {
        // This creates the soft gray shadow "halo"
        shadowColor: 'rgb(222, 224, 226)',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.05,
        shadowRadius: 8,
        elevation: 10, // Shadow for Android
        marginBottom: 12,
    },
    blackCircle: {
        width: 60,
        height: 60,
        borderRadius: 30,
        backgroundColor: '#dddada', // Bold Solid Black
        justifyContent: 'center',
        alignItems: 'center',
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    iconCircle: {
        width: 44,
        height: 44,
        borderRadius: 22,
        justifyContent: 'center',
        alignItems: 'center',
    },
    miniEditBtn: {
        backgroundColor: '#007AFF',
        width: 24,
        height: 24,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    cardFooter: {
        gap: 4,
    },
    cameraName: {
        fontSize: 16,
        fontWeight: '700',
        color: '#1C1C1E',
    },
    statusRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    statusDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        marginRight: 6,
    },
    statusText: {
        fontSize: 12,
        fontWeight: '600',
        color: '#8E8E93',
        textTransform: 'uppercase',
    },
    fab: {
        position: 'absolute',
        right: 25,
        bottom: 40,
        width: 64,
        height: 64,
        borderRadius: 24, // Squircle shape
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#007AFF',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.3,
        shadowRadius: 12,
        elevation: 10,
    },
    fabAdd: { backgroundColor: '#1A1A1A' },
    fabDone: { backgroundColor: '#4CAF50' },
    emptyText: { textAlign: 'center', color: '#8E8E93', marginTop: 100 },
});