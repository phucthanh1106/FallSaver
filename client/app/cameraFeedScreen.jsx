import React, { useState } from 'react';
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

const { width, height } = Dimensions.get('window');

export default function CameraFeedScreen() {
  const router = useRouter();
  const { cameraIndex, cameraName } = useLocalSearchParams();
  const [isLoading, setIsLoading] = useState(true);

  const streamUrl = `http://127.0.0.1:8000/api/cameras/feed/${cameraIndex}`;

  const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {
          margin: 0;
          padding: 0;
          background-color: #000;
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100vh;
        }
        img {
          max-width: 100%;
          max-height: 100%;
          object-fit: contain;
        }
      </style>
    </head>
    <body>
      <img src="${streamUrl}" />
    </body>
    </html>
  `;

  return (
    <View style={styles.container}>
      {/* Header */}
      {/* <View style={styles.header}>
        <TouchableOpacity onPress={() => {
          console.log("going back");
          if (router.canGoBack()) {
            router.back();
          } else {
            router.replace('/');
          }
        }}>
          <Ionicons name="chevron-back" size={20} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{cameraName}</Text>
        <View style={{ width: 28 }} />
      </View> */}

      {/* Live Feed with WebView */}
      <View style={styles.feedContainer}>
        <WebView
          source={{ html: htmlContent }}
          style={styles.webview}
          javaScriptEnabled={true}
          scalesPageToFit={true}
          onLoadEnd={() => setIsLoading(false)}
          pointerEvents="none"
        />
      </View>

        {/* Header - Absolutely positioned on top */}
      <View style={styles.headerOverlay} pointerEvents="box-none">
        <TouchableOpacity 
          onPress={() => {
            console.log("going back");

            if (router.canGoBack()) {
              router.back();
            } else {
              router.replace('/'); // fallback
            }
          }}
          style={styles.backButton}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="chevron-back" size={28} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{cameraName}</Text>
        <View style={{ width: 28 }} />
      </View>

      {/* Controls */}
      {/* <View style={styles.controlsContainer}>
        <TouchableOpacity style={styles.controlButton}>
          <Ionicons name="camera" size={24} color="#FFF" />
          <Text style={styles.buttonText}>Screenshot</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.controlButton}>
          <Ionicons name="recording" size={24} color="#FF3B30" />
          <Text style={styles.buttonText}>Record</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.controlButton}>
          <Ionicons name="settings" size={24} color="#FFF" />
          <Text style={styles.buttonText}>Settings</Text>
        </TouchableOpacity>
      </View> */}
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