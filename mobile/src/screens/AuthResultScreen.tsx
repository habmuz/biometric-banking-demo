import React, { useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Animated, Easing,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';

type Props = NativeStackScreenProps<RootStackParamList, 'AuthResult'>;

export default function AuthResultScreen({ navigation, route }: Props) {
  const { success, reason, username, mode } = route.params;

  const scaleAnim = useRef(new Animated.Value(0.5)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true, tension: 80, friction: 6 }),
      Animated.timing(opacityAnim, { toValue: 1, duration: 300, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <View style={styles.root}>
      <Animated.View style={[styles.iconWrap, { transform: [{ scale: scaleAnim }], opacity: opacityAnim }]}>
        <View style={[styles.iconCircle, success ? styles.iconSuccess : styles.iconFail]}>
          <Text style={{ fontSize: 40 }}>{success ? '✓' : '✕'}</Text>
        </View>
      </Animated.View>

      <Text style={styles.title}>
        {success
          ? (mode === 'register' ? 'Registration Successful' : 'Identity Verified')
          : (mode === 'register' ? 'Registration Failed' : 'Verification Failed')}
      </Text>
      <Text style={styles.subtitle}>
        {success
          ? (mode === 'register'
              ? 'Your face has been enrolled. You can now log in with biometrics.'
              : 'Your biometric authentication was successful.')
          : reason ?? 'Please try again or use your password.'}
      </Text>

      {!success && (
        <View style={styles.reasonCard}>
          <Text style={styles.reasonLabel}>REASON</Text>
          <Text style={styles.reasonText}>{reason}</Text>
        </View>
      )}

      <View style={styles.actions}>
        {!success && (
          <TouchableOpacity
            style={styles.btnPrimary}
            onPress={() => navigation.replace('Capture', { username, mode: mode ?? 'login' })}
          >
            <Text style={styles.btnPrimaryText}>Try Again</Text>
          </TouchableOpacity>
        )}
        {success && mode === 'register' ? (
          <TouchableOpacity
            style={styles.btnPrimary}
            onPress={() => navigation.replace('Login')}
          >
            <Text style={styles.btnPrimaryText}>Sign In with Your Face</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={success ? styles.btnPrimary : styles.btnGhost}
            onPress={() => navigation.replace('Login')}
          >
            <Text style={success ? styles.btnPrimaryText : styles.btnGhostText}>
              {success ? 'Back to Login' : 'Use Password Instead'}
            </Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1, backgroundColor: Colors.scBg,
    alignItems: 'center', justifyContent: 'center',
    paddingHorizontal: 32, gap: 20,
  },
  iconWrap: { marginBottom: 8 },
  iconCircle: {
    width: 100, height: 100, borderRadius: 50,
    alignItems: 'center', justifyContent: 'center',
  },
  iconSuccess: { backgroundColor: Colors.scGreenLight },
  iconFail: { backgroundColor: '#FDECEA' },
  title: { color: Colors.textPrimary, fontSize: 24, fontWeight: '700', textAlign: 'center' },
  subtitle: { color: Colors.textSecondary, fontSize: 14, textAlign: 'center', lineHeight: 22 },
  reasonCard: {
    width: '100%', backgroundColor: Colors.scWhite,
    borderRadius: 14, padding: 16, gap: 6,
    borderLeftWidth: 4, borderLeftColor: Colors.scRed,
  },
  reasonLabel: { fontSize: 10, fontWeight: '700', color: Colors.scRed, letterSpacing: 1 },
  reasonText: { fontSize: 13, color: Colors.textSecondary, lineHeight: 20 },
  actions: { width: '100%', gap: 12, marginTop: 8 },
  btnPrimary: {
    height: 52, backgroundColor: Colors.scGreen,
    borderRadius: 14, alignItems: 'center', justifyContent: 'center',
  },
  btnPrimaryText: { color: Colors.scWhite, fontSize: 15, fontWeight: '600' },
  btnGhost: { height: 48, alignItems: 'center', justifyContent: 'center' },
  btnGhostText: { color: Colors.textSecondary, fontSize: 14 },
});
