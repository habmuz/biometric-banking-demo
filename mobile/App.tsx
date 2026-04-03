import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import { useAuthStore } from './src/store/authStore';
import ConsentScreen from './src/screens/ConsentScreen';
import LoginScreen from './src/screens/LoginScreen';
import SignUpScreen from './src/screens/SignUpScreen';
import CaptureScreen from './src/screens/CaptureScreen';
import ProcessingScreen from './src/screens/ProcessingScreen';
import AuthResultScreen from './src/screens/AuthResultScreen';
import DashboardScreen from './src/screens/DashboardScreen';

export type RootStackParamList = {
  Consent: undefined;
  Login: undefined;
  SignUp: undefined;
  Capture: { username: string; mode: 'login' | 'register' };
  Processing: { username: string; imageBase64: string; mode: 'login' | 'register' };
  AuthResult: { success: boolean; reason?: string; username: string; mode?: 'login' | 'register' };
  Dashboard: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  const { accessToken, loadToken } = useAuthStore();

  useEffect(() => { loadToken(); }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <NavigationContainer>
          <StatusBar style="light" />
          <Stack.Navigator
            screenOptions={{ headerShown: false, animation: 'slide_from_right' }}
            initialRouteName={accessToken ? 'Dashboard' : 'Consent'}
          >
            <Stack.Screen name="Consent" component={ConsentScreen} />
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="SignUp" component={SignUpScreen} />
            <Stack.Screen
              name="Capture"
              component={CaptureScreen}
              options={{ animation: 'fade' }}
            />
            <Stack.Screen
              name="Processing"
              component={ProcessingScreen}
              options={{ animation: 'fade', gestureEnabled: false }}
            />
            <Stack.Screen name="AuthResult" component={AuthResultScreen} />
            <Stack.Screen
              name="Dashboard"
              component={DashboardScreen}
              options={{ gestureEnabled: false }}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
