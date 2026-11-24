import type { CapacitorConfig } from '@capacitor/cli';
const config: CapacitorConfig = {
  appId: 'org.unicornschool.tkzone', appName: 'TK-ZONE', webDir: 'dist',
  server: { androidScheme: 'https', hostname: 'localhost', cleartext: false },
  android: { allowMixedContent: false, webContentsDebuggingEnabled: false },
  ios: { contentInset: 'automatic', scheme: 'App' },
  plugins: { SplashScreen: { launchShowDuration: 900, backgroundColor: '#440CB0', showSpinner: false },
    StatusBar: { backgroundColor: '#440CB0', style: 'LIGHT' },
    PushNotifications: { presentationOptions: ['badge','sound','alert'] } },
};
export default config;
