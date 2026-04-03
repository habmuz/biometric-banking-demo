import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  SafeAreaView, Animated, Easing, KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';
import { checkIsRegistered } from '../services/biometricAgent';

type Props = NativeStackScreenProps<RootStackParamList, 'SignUp'>;

export default function SignUpScreen({ navigation }: Props) {
  const [username, setUsername] = useState('');
  const [checking, setChecking] = useState(false);

  const pulseAnim = useRef(new Animated.Value(1)).current;
  const pulseOpacity = useRef(new Animated.Value(0.6)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.parallel([
        Animated.timing(pulseAnim, {
          toValue: 1.35, duration: 1800,
          easing: Easing.out(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseOpacity, {
          toValue: 0, duration: 1800,
          easing: Easing.out(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, []);

  const handleRegister = async () => {
    const trimmed = username.trim();
    if (!trimmed) {
      Alert.alert('Username required', 'Please enter a username to create your account.');
      return;
    }
    if (trimmed.length < 3) {
      Alert.alert('Username too short', 'Username must be at least 3 characters.');
      return;
    }

    setChecking(true);
    try {
      const alreadyRegistered = await checkIsRegistered(trimmed);
      if (alreadyRegistered) {
        Alert.alert(
          'Already Registered',
          `'${trimmed}' already has a biometric account. Please use Face Login instead.`,
          [
            { text: 'Go to Login', onPress: () => navigation.replace('Login') },
            { text: 'Try Another Username', style: 'cancel' },
          ],
        );
        return;
      }
    } catch {
      // If check fails, proceed anyway — the agent will catch it
    } finally {
      setChecking(false);
    }

    navigation.navigate('Capture', { username: trimmed, mode: 'register' });
  };

  return (
    <SafeAreaView style={styles.root}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.backText}>‹ Back</Text>
          </TouchableOpacity>
          <View style={styles.logoRow}>
            <View style={styles.logoMark}>
              <Text style={{ fontSize: 14, fontWeight: '800', color: Colors.scGreen }}>AHB</Text>
            </View>
            <View>
              <Text style={styles.logoText}>Al Habibi Bank</Text>
              <Text style={styles.logoSub}>SINGAPORE</Text>
            </View>
          </View>
          <Text style={styles.headerTitle}>Create Account</Text>
          <Text style={styles.headerSub}>Register with facial biometrics</Text>
        </View>

        {/* Form */}
        <View style={styles.body}>
          {/* Steps indicator */}
          <View style={styles.stepsRow}>
            {['Choose Username', 'Scan Face', 'Done'].map((label, i) => (
              <View key={i} style={styles.stepItem}>
                <View style={[styles.stepDot, i === 0 && styles.stepDotActive]}>
                  <Text style={[styles.stepNum, i === 0 && styles.stepNumActive]}>{i + 1}</Text>
                </View>
                <Text style={[styles.stepLabel, i === 0 && styles.stepLabelActive]}>{label}</Text>
              </View>
            ))}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>USERNAME</Text>
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholder="Choose a username"
              placeholderTextColor={Colors.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              autoFocus
              returnKeyType="done"
              onSubmitEditing={handleRegister}
            />
            <Text style={styles.inputHint}>
              Minimum 3 characters · Letters, numbers, underscores
            </Text>
          </View>

          {/* Info card */}
          <View style={styles.infoCard}>
            <Text style={styles.infoTitle}>How it works</Text>
            <View style={styles.infoSteps}>
              <Text style={styles.infoStep}>1. Enter your desired username above</Text>
              <Text style={styles.infoStep}>2. Your camera will open — position your face in the oval</Text>
              <Text style={styles.infoStep}>3. Our AI checks liveness and enrolls your face</Text>
              <Text style={styles.infoStep}>4. You're ready to log in with your face anytime</Text>
            </View>
          </View>

          {/* Register button with face pulse */}
          <View style={styles.faceRegisterWrap}>
            <View style={styles.pulseContainer}>
              <Animated.View
                style={[
                  styles.pulseRing,
                  { transform: [{ scale: pulseAnim }], opacity: pulseOpacity },
                ]}
              />
              <TouchableOpacity
                style={[styles.btnFaceRegister, checking && styles.btnDisabled]}
                onPress={handleRegister}
                disabled={checking}
              >
                <Text style={{ fontSize: 32 }}>👤</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.faceRegisterLabel}>
              {checking ? 'Checking…' : 'Tap to Register with Face'}
            </Text>
          </View>

          <View style={styles.securityBadge}>
            <Text style={{ fontSize: 14 }}>🔒</Text>
            <Text style={styles.securityText}>
              ISO 24745 Cancelable Biometrics · ISO 30107-3 PAD Level 2 · MAS Licensed
            </Text>
          </View>

          <TouchableOpacity style={styles.loginLink} onPress={() => navigation.replace('Login')}>
            <Text style={styles.loginLinkText}>Already registered? Sign In</Text>
          </TouchableOpacity>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Al Habibi Bank (Singapore) Pte. Ltd. is licensed by MAS.{'\n'}
            Your deposits are protected up to S$75,000 by SDIC.
          </Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.scWhite },
  header: {
    backgroundColor: Colors.scGreen,
    paddingHorizontal: 28,
    paddingTop: 20,
    paddingBottom: 32,
    gap: 6,
  },
  backBtn: { marginBottom: 12 },
  backText: { color: 'rgba(255,255,255,0.8)', fontSize: 14, fontWeight: '500' },
  logoRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 16 },
  logoMark: {
    width: 36, height: 36, backgroundColor: Colors.scWhite,
    borderRadius: 8, alignItems: 'center', justifyContent: 'center',
  },
  logoText: { color: Colors.scWhite, fontSize: 15, fontWeight: '700', letterSpacing: 0.5 },
  logoSub: { color: 'rgba(255,255,255,0.7)', fontSize: 10, letterSpacing: 0.8 },
  headerTitle: { color: Colors.scWhite, fontSize: 26, fontWeight: '700' },
  headerSub: { color: 'rgba(255,255,255,0.7)', fontSize: 14 },

  body: { flex: 1, paddingHorizontal: 24, paddingTop: 28, gap: 20 },

  stepsRow: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 8 },
  stepItem: { alignItems: 'center', gap: 6, flex: 1 },
  stepDot: {
    width: 28, height: 28, borderRadius: 14,
    backgroundColor: Colors.border,
    alignItems: 'center', justifyContent: 'center',
  },
  stepDotActive: { backgroundColor: Colors.scGreen },
  stepNum: { fontSize: 12, fontWeight: '700', color: Colors.textMuted },
  stepNumActive: { color: Colors.scWhite },
  stepLabel: { fontSize: 10, color: Colors.textMuted, textAlign: 'center' },
  stepLabelActive: { color: Colors.scGreen, fontWeight: '600' },

  inputGroup: { gap: 6 },
  label: {
    fontSize: 12, fontWeight: '600', color: Colors.textSecondary,
    letterSpacing: 0.5, textTransform: 'uppercase',
  },
  input: {
    height: 52, borderWidth: 1.5, borderColor: Colors.border,
    borderRadius: 14, paddingHorizontal: 16,
    fontSize: 15, color: Colors.textPrimary, backgroundColor: Colors.scWhite,
  },
  inputHint: { fontSize: 11, color: Colors.textMuted },

  infoCard: {
    backgroundColor: Colors.scGreenLight, borderRadius: 12,
    padding: 16, gap: 10,
  },
  infoTitle: { fontSize: 13, fontWeight: '700', color: Colors.scGreenDark },
  infoSteps: { gap: 6 },
  infoStep: { fontSize: 12, color: Colors.scGreenDark, lineHeight: 18 },

  faceRegisterWrap: { alignItems: 'center', gap: 12, paddingVertical: 8 },
  pulseContainer: { width: 80, height: 80, alignItems: 'center', justifyContent: 'center' },
  pulseRing: {
    position: 'absolute',
    width: 80, height: 80, borderRadius: 20,
    borderWidth: 2.5, borderColor: Colors.scGreen,
  },
  btnFaceRegister: {
    width: 80, height: 80, backgroundColor: Colors.scGreen,
    borderRadius: 20, alignItems: 'center', justifyContent: 'center',
  },
  btnDisabled: { opacity: 0.5 },
  faceRegisterLabel: { fontSize: 14, fontWeight: '600', color: Colors.scGreen },

  securityBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    padding: 12, backgroundColor: Colors.scGreenLight, borderRadius: 8,
  },
  securityText: { fontSize: 11, color: Colors.scGreenDark, fontWeight: '500', flex: 1 },

  loginLink: { alignItems: 'center' },
  loginLinkText: { fontSize: 13, color: Colors.textSecondary },

  footer: { paddingHorizontal: 24, paddingBottom: 24, alignItems: 'center' },
  footerText: { fontSize: 11, color: Colors.textMuted, textAlign: 'center', lineHeight: 16 },
});
