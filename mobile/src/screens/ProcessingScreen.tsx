import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, Animated, Easing,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';
import { authenticateWithFace, registerWithFace } from '../services/biometricAgent';
import { useAuthStore } from '../store/authStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Processing'>;

const LOGIN_STEPS = [
  { label: 'Validating image quality…', duration: 1200 },
  { label: 'Running liveness detection…', duration: 2500 },
  { label: 'Verifying your identity…', duration: 1500 },
  { label: 'Issuing secure token…', duration: 800 },
];

const REGISTER_STEPS = [
  { label: 'Validating image quality…', duration: 1200 },
  { label: 'Running liveness detection…', duration: 2500 },
  { label: 'Enrolling face template…', duration: 1500 },
  { label: 'Issuing secure token…', duration: 800 },
];

export default function ProcessingScreen({ navigation, route }: Props) {
  const { username, imageBase64, mode } = route.params;
  const setToken = useAuthStore((s) => s.setToken);
  const [stepIdx, setStepIdx] = useState(0);

  const spinAnim = useRef(new Animated.Value(0)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;

  const STEPS = mode === 'register' ? REGISTER_STEPS : LOGIN_STEPS;
  const isRegistration = mode === 'register';

  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(spinAnim, {
        toValue: 1, duration: 1200,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    loop.start();

    Animated.timing(progressAnim, {
      toValue: 90, duration: 5500,
      easing: Easing.out(Easing.quad),
      useNativeDriver: false,
    }).start();

    let elapsed = 0;
    const timers: ReturnType<typeof setTimeout>[] = [];
    STEPS.forEach((step, i) => {
      const t = setTimeout(() => setStepIdx(i), elapsed);
      timers.push(t);
      elapsed += step.duration;
    });

    const apiCall = isRegistration
      ? registerWithFace(username, imageBase64)
      : authenticateWithFace(username, imageBase64);

    apiCall
      .then(async (result) => {
        loop.stop();
        timers.forEach(clearTimeout);

        if (result.status === 'authentication_success') {
          Animated.timing(progressAnim, {
            toValue: 100, duration: 400,
            useNativeDriver: false,
          }).start();
          if (isRegistration) {
            // Registration: show success screen → user then logs in to verify full flow
            setTimeout(() => navigation.replace('AuthResult', {
              success: true,
              username,
              mode,
            }), 500);
          } else {
            await setToken(result.access_token, username);
            setTimeout(() => navigation.replace('Dashboard'), 500);
          }
        } else {
          navigation.replace('AuthResult', {
            success: false,
            reason: (result as any).reason,
            username,
            mode,
          });
        }
      })
      .catch((e) => {
        loop.stop();
        timers.forEach(clearTimeout);
        navigation.replace('AuthResult', {
          success: false,
          reason: e.message ?? 'Connection error. Please try again.',
          username,
          mode,
        });
      });

    return () => {
      loop.stop();
      timers.forEach(clearTimeout);
    };
  }, []);

  const spin = spinAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });

  return (
    <View style={styles.root}>
      <View style={styles.spinnerWrap}>
        <Animated.View style={[styles.spinnerRing, { transform: [{ rotate: spin }] }]} />
        <View style={styles.spinnerFace}>
          <Text style={{ fontSize: 36 }}>{isRegistration ? '✋' : '👤'}</Text>
        </View>
      </View>

      <Text style={styles.title}>
        {isRegistration ? 'Registering Face' : 'Verifying Identity'}
      </Text>
      <Text style={styles.subtitle}>{STEPS[stepIdx]?.label ?? 'Almost done…'}</Text>

      <View style={styles.progressTrack}>
        <Animated.View
          style={[
            styles.progressFill,
            {
              width: progressAnim.interpolate({
                inputRange: [0, 100],
                outputRange: ['0%', '100%'],
              }),
            },
          ]}
        />
      </View>

      <Text style={styles.hint}>Keep your face still and well-lit</Text>

      <View style={styles.dotsRow}>
        {STEPS.map((_, i) => (
          <View key={i} style={[styles.dot, i <= stepIdx && styles.dotActive]} />
        ))}
      </View>

      <Text style={styles.secNote}>
        {isRegistration
          ? '🔒  ISO 24745 Cancelable Biometrics · MAS Compliant'
          : '🔒  Secured by ISO 30107-3 PAD Level 2 · MAS Compliant'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1, backgroundColor: Colors.cameraBg,
    alignItems: 'center', justifyContent: 'center', gap: 20,
  },
  spinnerWrap: {
    width: 120, height: 120,
    alignItems: 'center', justifyContent: 'center',
    marginBottom: 8,
  },
  spinnerRing: {
    position: 'absolute',
    width: 120, height: 120, borderRadius: 60,
    borderWidth: 3,
    borderColor: Colors.scGreen,
    borderTopColor: 'transparent',
  },
  spinnerFace: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: 'rgba(0,134,90,0.15)',
    alignItems: 'center', justifyContent: 'center',
  },
  title: { color: Colors.scWhite, fontSize: 22, fontWeight: '700' },
  subtitle: { color: Colors.scGreen, fontSize: 14, fontWeight: '500' },
  progressTrack: {
    width: 220, height: 4, backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 2, overflow: 'hidden',
  },
  progressFill: { height: '100%', backgroundColor: Colors.scGreen, borderRadius: 2 },
  hint: { color: 'rgba(255,255,255,0.4)', fontSize: 12 },
  dotsRow: { flexDirection: 'row', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.2)' },
  dotActive: { backgroundColor: Colors.scGreen },
  secNote: { color: 'rgba(255,255,255,0.3)', fontSize: 11, marginTop: 8 },
});
