import React from 'react';
import { 
  Modal, 
  View, 
  Text, 
  FlatList, 
  TouchableOpacity, 
  StyleSheet, 
  ActivityIndicator 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function EditCameraModal({ 
    visible, 
    onClose, 
    cameras, 
    unlinkedHardware, // Logic: The list from FastAPI /scan
    isScanning        // Logic: Loading state for the scan
}) {

    // LOGIC TO BE WRITTEN BY YOU:
    const handleRefresh = () => { /* Logic to trigger FastAPI /scan again */ };
    const handleAddHardware = (hw) => { /* Logic to save new hardware to Supabase */ };
    const handleDelete = (id) => { /* Your Supabase Delete Logic */ };
    const handleUpdate = (id) => { /* Your Supabase Update Logic */ };

    // Renders the new hardware found on the network/USB
    const renderDiscoveryItem = ({ item }) => (
        <TouchableOpacity 
            style={styles.discoveryCard} 
            onPress={() => handleAddHardware(item)}
        >
            <View style={styles.discoveryInfo}>
                <Ionicons name="add-circle" size={20} color="#007AFF" />
                <Text style={styles.discoveryText}>{item.name}</Text>
            </View>
            <Text style={styles.discoverySubtext}>{item.resolution}</Text>
        </TouchableOpacity>
    );

    // Renders existing cameras saved in Supabase
    const renderEditItem = ({ item }) => (
        <View style={styles.editRow}>
            <View style={styles.itemInfo}>
                <Text style={styles.itemText}>{item.location}</Text>
                <Text style={styles.subText}>{item.name} (Index: {item.hardware_index})</Text>
            </View>
            <View style={styles.actionGroup}>
                <TouchableOpacity onPress={() => handleUpdate(item.id)}>
                    <Ionicons name="create-outline" size={22} color="#007AFF" />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => handleDelete(item.id)}>
                    <Ionicons name="trash-outline" size={22} color="#FF3B30" />
                </TouchableOpacity>
            </View>
        </View>
    );

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

                    {unlinkedHardware && unlinkedHardware.length > 0 ? (
                        <FlatList
                            data={unlinkedHardware}
                            renderItem={renderDiscoveryItem}
                            keyExtractor={item => item.id.toString()}
                            horizontal
                            showsHorizontalScrollIndicator={false}
                            contentContainerStyle={styles.discoveryList}
                        />
                    ) : (
                        <View style={styles.emptyDiscovery}>
                            <Text style={styles.emptyText}>No new cameras detected</Text>
                        </View>
                    )}
                </View>

                {/* 2. SAVED CAMERAS SECTION */}
                <View style={styles.savedSection}>
                    <Text style={[styles.sectionTitle, { marginLeft: 20, marginBottom: 10 }]}>
                        Saved Devices
                    </Text>
                    <FlatList
                        data={cameras}
                        renderItem={renderEditItem}
                        keyExtractor={item => item.id.toString()}
                    />
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    modalContainer: { flex: 1, backgroundColor: '#F2F2F7' },
    header: { 
        flexDirection: 'row', 
        justifyContent: 'space-between', 
        padding: 20, 
        backgroundColor: '#FFF',
        borderBottomWidth: 1,
        borderBottomColor: '#E5E5EA'
    },
    title: { fontSize: 20, fontWeight: 'bold' },
    doneBtn: { color: '#007AFF', fontWeight: '600', fontSize: 16 },
    
    // Discovery Styles
    discoverySection: {
        backgroundColor: '#FFF',
        paddingVertical: 20,
        marginBottom: 20,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        marginBottom: 15,
    },
    sectionTitle: { fontSize: 13, fontWeight: '600', color: '#8E8E93', textTransform: 'uppercase' },
    discoveryList: { paddingHorizontal: 15 },
    discoveryCard: {
        backgroundColor: '#F2F2F7',
        padding: 15,
        borderRadius: 12,
        marginHorizontal: 5,
        minWidth: 140,
        borderWidth: 1,
        borderColor: '#E5E5EA',
    },
    discoveryInfo: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
    discoveryText: { fontSize: 14, fontWeight: '600', marginLeft: 6 },
    discoverySubtext: { fontSize: 11, color: '#8E8E93', marginLeft: 26 },
    emptyDiscovery: { paddingHorizontal: 20, paddingBottom: 10 },
    emptyText: { color: '#C7C7CC', fontSize: 14, fontStyle: 'italic' },

    // Edit Row Styles
    savedSection: { flex: 1 },
    editRow: { 
        flexDirection: 'row', 
        padding: 20, 
        backgroundColor: '#FFF', 
        marginBottom: 1, 
        justifyContent: 'space-between',
        alignItems: 'center'
    },
    itemInfo: { flex: 1 },
    itemText: { fontSize: 16, fontWeight: '500' },
    subText: { fontSize: 12, color: '#8E8E93', marginTop: 2 },
    actionGroup: { flexDirection: 'row', width: 60, justifyContent: 'space-between' }
});