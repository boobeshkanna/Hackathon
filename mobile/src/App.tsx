import React, { useEffect } from 'react';
import { Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { database } from './database/schema';
import { backgroundSyncService } from './services/BackgroundSync';
import { notificationService } from './services/NotificationService';
import { CaptureScreen } from './screens/CaptureScreen';
import { QueueScreen } from './screens/QueueScreen';
import { BulkCaptureScreen } from './screens/BulkCaptureScreen';
import { ReviewScreen } from './screens/ReviewScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

/**
 * Main App Component
 * Zero-UI Edge Client for Vernacular Artisan Catalog
 */
export default function App() {
  useEffect(() => {
    initializeApp();

    return () => {
      cleanup();
    };
  }, []);

  /**
   * Initialize app services
   */
  const initializeApp = async () => {
    try {
      // Initialize database
      await database.init();
      console.log('Database initialized');

      // Initialize notifications
      await notificationService.initialize();
      console.log('Notifications initialized');

      // Start background sync
      await backgroundSyncService.startSync();
      console.log('Background sync started');
    } catch (error) {
      console.error('App initialization failed:', error);
    }
  };

  /**
   * Cleanup on app unmount
   */
  const cleanup = async () => {
    try {
      backgroundSyncService.stopSync();
      await database.close();
    } catch (error) {
      console.error('Cleanup failed:', error);
    }
  };

  /**
   * Main Tab Navigator
   */
  const MainTabs = () => (
    <Tab.Navigator
      screenOptions={{
        headerShown: true,
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: '#8E8E93',
      }}
    >
      <Tab.Screen
        name="Capture"
        component={CaptureScreen}
        options={{
          tabBarLabel: 'Capture',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ fontSize: size, color }}>📷</Text>
          ),
        }}
      />
      <Tab.Screen
        name="Queue"
        component={QueueScreen}
        options={{
          tabBarLabel: 'Queue',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ fontSize: size, color }}>📋</Text>
          ),
        }}
      />
      <Tab.Screen
        name="Bulk"
        component={BulkCaptureScreen}
        options={{
          tabBarLabel: 'Bulk',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ fontSize: size, color }}>📦</Text>
          ),
        }}
      />
    </Tab.Navigator>
  );

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
        }}
      >
        <Stack.Screen name="MainTabs" component={MainTabs} />
        <Stack.Screen 
          name="Review" 
          component={ReviewScreen as any}
          options={{
            headerShown: true,
            title: 'Review & Publish',
            headerBackTitle: 'Back',
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
