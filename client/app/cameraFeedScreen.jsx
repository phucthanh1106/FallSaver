import React, { useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { WebView } from 'react-native-webview';
import { authenticatedFetch } from '../config/authenticatedFetch.js';
import API_URL from '../config/api.js';
import supabase from '../config/supabaseClient.js';


const { width } = Dimensions.get('window');

export default function CameraFeedScreen() {
  const router = useRouter();
  const { camera_id, connection_id, camera_name } = useLocalSearchParams();
  const [streamSource, setStreamSource] = useState(null);
  const [feedError, setFeedError] = useState('');
  const streamUrl = `${API_URL}/api/cameras/feed/${connection_id}/${camera_id}`;

  useEffect(() => {
    let isMounted = true;

    const loadAuthenticatedStream = async () => {
      const { data: { session }, error } = await supabase.auth.getSession();

      if (!isMounted) {
        return;
      }

      if (error || !session) {
        setFeedError('You must sign in to view this camera.');
        return;
      }

      setStreamSource({
        uri: streamUrl,
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
    };

    loadAuthenticatedStream();

    return () => {
      isMounted = false;
    };
  }, [streamUrl]);

  const handleBack = async () => {
    console.log("Stopping camera stream...");
    
    // Clear the WebView content
    setStreamSource({ html: '<!DOCTYPE html><html><body style="background-color: #000;"></body></html>' });

    // Call server to stop the camera
    try {
      const response = await authenticatedFetch(`${API_URL}/api/cameras/stop/${camera_id}`, {
        method: 'POST',
      });
      console.log("Camera stop response:", response.status);
    } catch (error) {
      console.log("Error stopping camera:", error.message);
    }

    // Navigate back
    setTimeout(() => {
      if (router.canGoBack()) {
        router.back();
      } else {
        router.replace('/');
      }
    }, 300);
  };


  return (
    <View style={styles.container}>
      {/* Live Feed with WebView */}
      <View style={styles.feedContainer}>
        {feedError ? (
          <Text style={styles.feedError}>{feedError}</Text>
        ) : streamSource ? (
          <WebView
            source={streamSource}
            style={styles.webview}
            javaScriptEnabled={true}
            scalesPageToFit={true}
            onError={() => {
              setFeedError('Could not load the camera feed.');
            }}
            onHttpError={({ nativeEvent }) => {
              setFeedError(`Camera feed request failed with status ${nativeEvent.statusCode}.`);
            }}
            pointerEvents="none"
          />
        ) : null}
      </View>

      {/* Header - Absolutely positioned on top */}
      <View style={styles.headerOverlay} pointerEvents="box-none">
        <TouchableOpacity 
          onPress={handleBack}
          style={styles.backButton}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="chevron-back" size={28} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{camera_name}</Text>
        <View style={{ width: 28 }} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    position: 'relative',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#1C1C1E',
    borderBottomWidth: 1,
    borderBottomColor: '#3A3A3C',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFF',
  },
  headerOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 50,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    zIndex: 1000,
  },
  feedContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#bebbbb',
  },
  webview: {
    flex: 1,
    width: width,
  },
  feedError: {
    color: '#FFF',
    fontSize: 15,
    paddingHorizontal: 24,
    textAlign: 'center',
  },
  controlsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 20,
    backgroundColor: '#c0c0c7',
    borderTopWidth: 1,
    borderTopColor: '#3A3A3C',
  },
  controlButton: {
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFF',
    fontSize: 12,
    marginTop: 8,
    fontWeight: '500',
  },
});
