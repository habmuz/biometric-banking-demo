import React, { useRef, useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';

type Props = NativeStackScreenProps<RootStackParamList, 'Capture'>;

export default function CaptureScreen({ navigation, route }: Props) {
  const { username, mode } = route.params;
  const [permission, requestPermission] = useCameraPermissions();
  const [capturing, setCapturing] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  const handleCapture = useCallback(async () => {
    if (!cameraRef.current || capturing) return;
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.85,
        exif: false,
      });
      if (!photo?.base64) throw new Error('No image data captured.');
      navigation.replace('Processing', { username, imageBase64: photo.base64, mode });
    } catch (e: any) {
      Alert.alert('Capture failed', e.message ?? 'Please try again.');
      setCapturing(false);
    }
  }, [capturing, username, navigation]);

  if (!permission) return <View style={styles.root} />;

  if (!permission.granted) {
    return (
      <SafeAreaView style={[styles.root, { justifyContent: 'center', alignItems: 'center', gap: 20 }]}>
        <Text style={styles.permText}>Camera access is required for biometric login.</Text>
        <TouchableOpacity style={styles.btnAllow} onPress={requestPermission}>
          <Text style={styles.btnAllowText}>Allow Camera</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={{ color: Colors.textMuted, fontSize: 14 }}>Go back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <View style={styles.root}>
      {/* Camera feed — full screen */}
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="front"
      />

      {/* Dark overlay except oval */}
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        {/* Top bar */}
        <View style={styles.topBar}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <Text style={{ color: Colors.scWhite, fontSize: 18 }}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.topTitle}>{mode === 'register' ? 'Face Registration' : 'Face Verification'}</Text>
          <View style={styles.helpBtn}>
            <Text style={{ color: Colors.scWhite, fontSize: 13, fontWeight: '700' }}>?</Text>
          </View>
        </View>

        {/* Instruction */}
        <Text style={styles.instruction}>
          Position your face within the oval.{'\n'}Keep still in good lighting.
        </Text>

        {/* Oval viewfinder */}
        <View style={styles.ovalContainer}>
          <View style={styles.ovalOuter}>
            {/* Corner brackets — SC green */}
            <View style={[styles.corner, styles.cornerTL]} />
            <View style={[styles.corner, styles.cornerTR]} />
            <View style={[styles.corner, styles.cornerBL]} />
            <View style={[styles.corner, styles.cornerBR]} />
          </View>
        </View>
      </View>

      {/* Bottom controls — NOT inside pointerEvents none */}
      <View style={styles.bottomBar}>
        <Text style={styles.bottomHint}>Ensure your face is well-lit and centered</Text>
        <TouchableOpacity
          style={[styles.captureBtn, capturing && styles.captureBtnActive]}
          onPress={handleCapture}
          disabled={capturing}
        >
          <View style={styles.captureBtnInner} />
        </TouchableOpacity>
        <Text style={styles.bottomSub}>Tap to capture</Text>
      </View>
    </View>
  );
}

const OVAL_W = 240;
const OVAL_H = 300;
const CORNER = 24;
const THICK = 3;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.cameraBg },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 56,
    paddingBottom: 16,
  },
  backBtn: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center', justifyContent: 'center',
  },
  topTitle: { color: Colors.scWhite, fontSize: 16, fontWeight: '600' },
  helpBtn: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center', justifyContent: 'center',
  },
  instruction: {
    color: 'rgba(255,255,255,0.65)',
    fontSize: 13, textAlign: 'center',
    paddingHorizontal: 32, lineHeight: 20, marginBottom: 20,
  },
  ovalContainer: { alignItems: 'center', justifyContent: 'center', flex: 1 },
  ovalOuter: {
    width: OVAL_W, height: OVAL_H,
    borderRadius: OVAL_W / 2,
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.25)',
    position: 'relative',
  },
  corner: {
    position: 'absolute', width: CORNER, height: CORNER,
    borderColor: Colors.scGreen, borderWidth: THICK,
  },
  cornerTL: { top: -THICK / 2, left: -THICK / 2, borderBottomWidth: 0, borderRightWidth: 0, borderTopLeftRadius: 8 },
  cornerTR: { top: -THICK / 2, right: -THICK / 2, borderBottomWidth: 0, borderLeftWidth: 0, borderTopRightRadius: 8 },
  cornerBL: { bottom: -THICK / 2, left: -THICK / 2, borderTopWidth: 0, borderRightWidth: 0, borderBottomLeftRadius: 8 },
  cornerBR: { bottom: -THICK / 2, right: -THICK / 2, borderTopWidth: 0, borderLeftWidth: 0, borderBottomRightRadius: 8 },
  bottomBar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    paddingBottom: 48, alignItems: 'center', gap: 12,
  },
  bottomHint: { color: 'rgba(255,255,255,0.5)', fontSize: 12 },
  captureBtn: {
    width: 72, height: 72, borderRadius: 36,
    borderWidth: 3, borderColor: Colors.scWhite,
    alignItems: 'center', justifyContent: 'center',
  },
  captureBtnActive: { borderColor: Colors.scGreen },
  captureBtnInner: {
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: Colors.scGreen,
  },
  bottomSub: { color: 'rgba(255,255,255,0.4)', fontSize: 11 },
  permText: { color: Colors.scWhite, fontSize: 15, textAlign: 'center', paddingHorizontal: 32 },
  btnAllow: {
    paddingHorizontal: 32, paddingVertical: 14,
    backgroundColor: Colors.scGreen, borderRadius: 14,
  },
  btnAllowText: { color: Colors.scWhite, fontSize: 15, fontWeight: '600' },
});
