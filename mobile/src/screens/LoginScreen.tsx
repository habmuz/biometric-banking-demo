import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  SafeAreaView, Animated, Easing, KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';
import { checkIsRegistered } from '../services/biometricAgent';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [checking, setChecking] = useState(false);

  // Pulse animation for face ID button
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

  const handleFaceLogin = async () => {
    if (!username.trim()) {
      Alert.alert('Username required', 'Please enter your username.');
      return;
    }
    setChecking(true);
    try {
      const registered = await checkIsRegistered(username.trim());
      if (!registered) {
        Alert.alert(
          'Not Registered',
          `No biometric account found for '${username.trim()}'. Please sign up first.`,
          [
            { text: 'Sign Up', onPress: () => navigation.navigate('SignUp') },
            { text: 'Cancel', style: 'cancel' },
          ],
        );
        return;
      }
      navigation.navigate('Capture', { username: username.trim(), mode: 'login' });
    } catch {
      Alert.alert('Error', 'Could not reach server. Please try again.');
    } finally {
      setChecking(false);
    }
  };

  const handleSignUp = () => navigation.navigate('SignUp');

  return (
    <SafeAreaView style={styles.root}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoRow}>
            <View style={styles.logoMark}>
              <Text style={{ fontSize: 14, fontWeight: '800', color: Colors.scGreen }}>AHB</Text>
            </View>
            <View>
              <Text style={styles.logoText}>Al Habibi Bank</Text>
              <Text style={styles.logoSub}>SINGAPORE</Text>
            </View>
          </View>
          <Text style={styles.headerTitle}>Welcome back</Text>
          <Text style={styles.headerSub}>Sign in with your registered face</Text>
        </View>

        {/* Form */}
        <View style={styles.body}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>USERNAME</Text>
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholder="Enter username"
              placeholderTextColor={Colors.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>PASSWORD</Text>
            <View style={styles.passwordWrap}>
              <TextInput
                style={[styles.input, { paddingRight: 44 }]}
                value={password}
                onChangeText={setPassword}
                placeholder="Enter password"
                placeholderTextColor={Colors.textMuted}
                secureTextEntry={!showPass}
              />
              <TouchableOpacity
                style={styles.eyeBtn}
                onPress={() => setShowPass((v) => !v)}
              >
                <Text style={{ fontSize: 16 }}>{showPass ? '🙈' : '👁️'}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Divider */}
          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* Login + Face ID row */}
          <View style={styles.authRow}>
            <TouchableOpacity style={styles.btnLogin}>
              <Text style={styles.btnLoginText}>Sign In</Text>
            </TouchableOpacity>

            {/* Face ID button with pulse ring */}
            <View style={styles.faceIdWrap}>
              <Animated.View
                style={[
                  styles.pulseRing,
                  { transform: [{ scale: pulseAnim }], opacity: pulseOpacity },
                ]}
              />
              <TouchableOpacity
                style={[styles.btnFaceId, checking && { opacity: 0.5 }]}
                onPress={handleFaceLogin}
                disabled={checking}
              >
                <Text style={{ fontSize: 22 }}>{checking ? '⏳' : '👤'}</Text>
              </TouchableOpacity>
              <Text style={styles.faceIdTooltip}>{checking ? 'Checking…' : 'Face Login'}</Text>
            </View>
          </View>

          {/* Links */}
          <View style={styles.linksRow}>
            <TouchableOpacity>
              <Text style={styles.link}>Forgot password?</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={handleSignUp}>
              <Text style={styles.link}>New user? Sign Up</Text>
            </TouchableOpacity>
          </View>

          {/* Security badge */}
          <View style={styles.securityBadge}>
            <Text style={{ fontSize: 14 }}>🔒</Text>
            <Text style={styles.securityText}>
              Secured by ISO 30107-3 Liveness Detection · MAS Licensed
            </Text>
          </View>
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
    paddingTop: 44,
    paddingBottom: 36,
    gap: 6,
  },
  logoRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 20 },
  logoMark: {
    width: 36, height: 36, backgroundColor: Colors.scWhite,
    borderRadius: 8, alignItems: 'center', justifyContent: 'center',
  },
  logoText: { color: Colors.scWhite, fontSize: 15, fontWeight: '700', letterSpacing: 0.5 },
  logoSub: { color: 'rgba(255,255,255,0.7)', fontSize: 10, letterSpacing: 0.8 },
  headerTitle: { color: Colors.scWhite, fontSize: 26, fontWeight: '700' },
  headerSub: { color: 'rgba(255,255,255,0.7)', fontSize: 14 },
  body: { flex: 1, paddingHorizontal: 24, paddingTop: 32, gap: 20 },
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
  passwordWrap: { position: 'relative' },
  eyeBtn: { position: 'absolute', right: 14, top: 14 },
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  dividerLine: { flex: 1, height: 1, backgroundColor: Colors.border },
  dividerText: { fontSize: 12, color: Colors.textMuted, fontWeight: '500' },
  authRow: { flexDirection: 'row', gap: 12, alignItems: 'center' },
  btnLogin: {
    flex: 1, height: 52, backgroundColor: Colors.scGreen,
    borderRadius: 14, alignItems: 'center', justifyContent: 'center',
  },
  btnLoginText: { color: Colors.scWhite, fontSize: 15, fontWeight: '600' },
  faceIdWrap: { alignItems: 'center', position: 'relative', width: 52 },
  pulseRing: {
    position: 'absolute',
    width: 52, height: 52, borderRadius: 14,
    borderWidth: 2, borderColor: Colors.scGreen,
  },
  btnFaceId: {
    width: 52, height: 52, backgroundColor: Colors.scWhite,
    borderWidth: 1.5, borderColor: Colors.scGreen,
    borderRadius: 14, alignItems: 'center', justifyContent: 'center',
  },
  faceIdTooltip: {
    fontSize: 9, color: Colors.scGreen, fontWeight: '600',
    marginTop: 4, textAlign: 'center',
  },
  linksRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: -8 },
  link: { fontSize: 13, color: Colors.scGreen, fontWeight: '500' },
  securityBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    padding: 12, backgroundColor: Colors.scGreenLight, borderRadius: 8,
    marginTop: 'auto',
  },
  securityText: { fontSize: 12, color: Colors.scGreenDark, fontWeight: '500', flex: 1 },
  footer: { paddingHorizontal: 24, paddingBottom: 24, alignItems: 'center' },
  footerText: { fontSize: 11, color: Colors.textMuted, textAlign: 'center', lineHeight: 16 },
});
