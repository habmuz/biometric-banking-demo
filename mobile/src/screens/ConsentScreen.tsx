import React from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, SafeAreaView,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';
import { useAuthStore } from '../store/authStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Consent'>;

const points = [
  {
    icon: '🔒',
    title: 'Your data stays on-device',
    body: 'Your face image is processed in real-time and never stored on our servers.',
  },
  {
    icon: '🛡️',
    title: 'ISO 30107-3 Liveness Detection',
    body: 'We verify you\'re physically present — photos and videos are rejected.',
  },
  {
    icon: '🗑️',
    title: 'Immediate deletion',
    body: 'Raw images are deleted immediately after authentication. Only a secure template is retained.',
  },
  {
    icon: '↩️',
    title: 'Withdraw anytime',
    body: 'You can disable biometric login in Settings at any time and your template will be deleted.',
  },
];

export default function ConsentScreen({ navigation }: Props) {
  const setPdpaConsented = useAuthStore((s) => s.setPdpaConsented);

  const handleConsent = () => {
    setPdpaConsented(true);
    navigation.replace('Login');
  };

  return (
    <SafeAreaView style={styles.root}>
      {/* Hero */}
      <View style={styles.hero}>
        <View style={styles.iconWrap}>
          <Text style={styles.heroIcon}>👤</Text>
        </View>
        <Text style={styles.heroTitle}>Face Login Setup</Text>
        <Text style={styles.heroSub}>
          Before we enable biometric login, please review how we protect your data under PDPA.
        </Text>
      </View>

      {/* Body */}
      <ScrollView style={styles.body} showsVerticalScrollIndicator={false}>
        {/* PDPA Badge */}
        <View style={styles.pdpaBadge}>
          <Text style={styles.pdpaText}>
            ⚠️  Protected under Singapore Personal Data Protection Act (PDPA) 2012
          </Text>
        </View>

        {points.map((p, i) => (
          <View key={i} style={styles.point}>
            <View style={styles.pointIcon}>
              <Text style={{ fontSize: 18 }}>{p.icon}</Text>
            </View>
            <View style={styles.pointText}>
              <Text style={styles.pointTitle}>{p.title}</Text>
              <Text style={styles.pointBody}>{p.body}</Text>
            </View>
          </View>
        ))}
      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.btnPrimary} onPress={handleConsent}>
          <Text style={styles.btnPrimaryText}>I Agree — Enable Face Login</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btnGhost} onPress={() => navigation.replace('Login')}>
          <Text style={styles.btnGhostText}>Not now, use password only</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.scWhite },
  hero: {
    backgroundColor: Colors.scGreen,
    paddingHorizontal: 28,
    paddingTop: 32,
    paddingBottom: 40,
    alignItems: 'center',
    gap: 12,
  },
  iconWrap: {
    width: 80, height: 80,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 40,
    alignItems: 'center', justifyContent: 'center',
    marginTop: 8,
  },
  heroIcon: { fontSize: 36 },
  heroTitle: { color: Colors.scWhite, fontSize: 20, fontWeight: '700', textAlign: 'center' },
  heroSub: {
    color: 'rgba(255,255,255,0.75)',
    fontSize: 13, textAlign: 'center', lineHeight: 20,
  },
  body: { flex: 1, paddingHorizontal: 24, paddingTop: 24 },
  pdpaBadge: {
    backgroundColor: '#FFF8E1',
    borderWidth: 1, borderColor: '#FFD54F',
    borderRadius: 8, padding: 12, marginBottom: 24,
  },
  pdpaText: { fontSize: 11, color: '#795548', fontWeight: '500', lineHeight: 18 },
  point: { flexDirection: 'row', gap: 14, marginBottom: 22, alignItems: 'flex-start' },
  pointIcon: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: Colors.scGreenLight,
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  pointText: { flex: 1 },
  pointTitle: { fontSize: 14, fontWeight: '600', color: Colors.textPrimary, marginBottom: 3 },
  pointBody: { fontSize: 12, color: Colors.textSecondary, lineHeight: 18 },
  footer: { paddingHorizontal: 24, paddingBottom: 32, paddingTop: 16, gap: 12 },
  btnPrimary: {
    height: 52, backgroundColor: Colors.scGreen,
    borderRadius: 14, alignItems: 'center', justifyContent: 'center',
  },
  btnPrimaryText: { color: Colors.scWhite, fontSize: 15, fontWeight: '600' },
  btnGhost: { height: 44, alignItems: 'center', justifyContent: 'center' },
  btnGhostText: { color: Colors.textSecondary, fontSize: 13 },
});
