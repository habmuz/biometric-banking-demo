import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, RefreshControl, ActivityIndicator,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { Colors } from '../constants/colors';
import { useAuthStore } from '../store/authStore';
import { getPortfolio, Portfolio } from '../services/portfolioApi';

type Props = NativeStackScreenProps<RootStackParamList, 'Dashboard'>;

const TYPE_LABEL: Record<string, string> = {
  current: 'Current Account',
  savings: 'Savings Account',
  fixed_deposit: 'Fixed Deposit',
  investment: 'Investment',
};

const TYPE_ICON: Record<string, string> = {
  current: '🏦',
  savings: '💰',
  fixed_deposit: '📈',
  investment: '📊',
};

function formatSGD(value: number) {
  return value.toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function DashboardScreen({ navigation }: Props) {
  const { accessToken, username, logout } = useAuthStore();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [balancesHidden, setBalancesHidden] = useState(false);

  const fetchPortfolio = async (isRefresh = false) => {
    if (!accessToken) return;
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await getPortfolio(accessToken);
      setPortfolio(data);
    } catch (e: any) {
      if (e.response?.status === 401) {
        await logout();
        navigation.replace('Login');
      } else {
        setError('Unable to load portfolio. Pull to refresh.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchPortfolio(); }, []);

  const handleLogout = async () => {
    await logout();
    navigation.replace('Login');
  };

  return (
    <SafeAreaView style={styles.root}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Good morning,</Text>
          <Text style={styles.username}>{username ?? 'User'} 👋</Text>
        </View>
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Text style={{ fontSize: 18 }}>↩</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => fetchPortfolio(true)}
            tintColor={Colors.scGreen}
          />
        }
      >
        {/* Total Portfolio Card */}
        <View style={styles.portfolioCard}>
          <View style={styles.portfolioTopRow}>
            <Text style={styles.portfolioLabel}>TOTAL PORTFOLIO VALUE</Text>
            <TouchableOpacity onPress={() => setBalancesHidden((v) => !v)}>
              <Text style={{ fontSize: 16, color: 'rgba(255,255,255,0.7)' }}>
                {balancesHidden ? '👁️' : '🙈'}
              </Text>
            </TouchableOpacity>
          </View>
          {loading ? (
            <ActivityIndicator color={Colors.scWhite} size="large" style={{ marginVertical: 16 }} />
          ) : (
            <>
              <Text style={styles.portfolioValue}>
                {portfolio
                  ? (balancesHidden ? 'S$ ••••••' : `S$ ${formatSGD(portfolio.totalValue)}`)
                  : '—'}
              </Text>
              <Text style={styles.portfolioSub}>
                {portfolio
                  ? `as of ${new Date(portfolio.lastUpdated).toLocaleDateString('en-SG', { day: 'numeric', month: 'short', year: 'numeric' })}`
                  : ''}
              </Text>
            </>
          )}

          {/* Auth badge */}
          <View style={styles.authBadge}>
            <Text style={styles.authBadgeText}>
              🔒 Biometric Login · ACR=3 · MAS Compliant
            </Text>
          </View>
        </View>

        {/* Accounts */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Accounts</Text>
          {error && (
            <View style={styles.errorCard}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}
          {!loading && portfolio?.accounts.map((account) => (
            <TouchableOpacity key={account.id} style={styles.accountCard}>
              <View style={styles.accountLeft}>
                <View style={styles.accountIconWrap}>
                  <Text style={{ fontSize: 22 }}>{TYPE_ICON[account.type] ?? '💳'}</Text>
                </View>
                <View>
                  <Text style={styles.accountName}>{account.name}</Text>
                  <Text style={styles.accountType}>{TYPE_LABEL[account.type] ?? account.type}</Text>
                  <Text style={styles.accountNumber}>{account.accountNumber}</Text>
                </View>
              </View>
              <View style={styles.accountRight}>
                <Text style={styles.accountBalance}>
                  {balancesHidden
                    ? '••••••'
                    : `${account.currency} ${formatSGD(account.balance)}`}
                </Text>
                <Text style={styles.accountArrow}>›</Text>
              </View>
            </TouchableOpacity>
          ))}
          {loading && [1, 2, 3].map((i) => (
            <View key={i} style={[styles.accountCard, styles.skeleton]} />
          ))}
        </View>

        {/* Quick actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            {[
              { icon: '📤', label: 'Transfer' },
              { icon: '📱', label: 'Pay Bills' },
              { icon: '💳', label: 'Cards' },
              { icon: '📊', label: 'Invest' },
            ].map((a) => (
              <TouchableOpacity key={a.label} style={styles.actionBtn}>
                <Text style={{ fontSize: 24 }}>{a.icon}</Text>
                <Text style={styles.actionLabel}>{a.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.scBg },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8,
    backgroundColor: Colors.scWhite,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  greeting: { fontSize: 13, color: Colors.textSecondary },
  username: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary },
  logoutBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: Colors.scGreenLight,
    alignItems: 'center', justifyContent: 'center',
  },
  portfolioCard: {
    margin: 20, borderRadius: 20, padding: 24,
    backgroundColor: Colors.scGreen,
    shadowColor: Colors.scGreenDark,
    shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.35, shadowRadius: 16,
    elevation: 8,
  },
  portfolioTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  portfolioLabel: { fontSize: 11, color: 'rgba(255,255,255,0.65)', fontWeight: '600', letterSpacing: 1 },
  portfolioValue: { fontSize: 36, fontWeight: '800', color: Colors.scWhite, marginBottom: 4 },
  portfolioSub: { fontSize: 12, color: 'rgba(255,255,255,0.55)' },
  authBadge: {
    marginTop: 16, backgroundColor: 'rgba(0,0,0,0.15)',
    borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6,
    alignSelf: 'flex-start',
  },
  authBadgeText: { fontSize: 11, color: 'rgba(255,255,255,0.75)', fontWeight: '500' },
  section: { paddingHorizontal: 20, marginBottom: 8 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: Colors.textPrimary, marginBottom: 12 },
  accountCard: {
    backgroundColor: Colors.scWhite, borderRadius: 14, padding: 16,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    marginBottom: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 8, elevation: 2,
  },
  skeleton: { height: 76, backgroundColor: Colors.border, opacity: 0.5 },
  accountLeft: { flexDirection: 'row', gap: 14, alignItems: 'center' },
  accountIconWrap: {
    width: 44, height: 44, borderRadius: 12,
    backgroundColor: Colors.scGreenLight,
    alignItems: 'center', justifyContent: 'center',
  },
  accountName: { fontSize: 14, fontWeight: '600', color: Colors.textPrimary },
  accountType: { fontSize: 11, color: Colors.textSecondary, marginTop: 1 },
  accountNumber: { fontSize: 11, color: Colors.textMuted, marginTop: 1 },
  accountRight: { alignItems: 'flex-end', gap: 4 },
  accountBalance: { fontSize: 15, fontWeight: '700', color: Colors.textPrimary },
  accountArrow: { fontSize: 18, color: Colors.textMuted },
  actionsGrid: { flexDirection: 'row', gap: 12 },
  actionBtn: {
    flex: 1, backgroundColor: Colors.scWhite,
    borderRadius: 14, paddingVertical: 16,
    alignItems: 'center', gap: 8,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 8, elevation: 2,
  },
  actionLabel: { fontSize: 12, fontWeight: '600', color: Colors.textSecondary },
  errorCard: {
    backgroundColor: '#FDECEA', borderRadius: 10, padding: 12, marginBottom: 12,
    borderLeftWidth: 4, borderLeftColor: Colors.scRed,
  },
  errorText: { fontSize: 13, color: Colors.scRed },
});
