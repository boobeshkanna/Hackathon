package com.vernacularartisancatalog;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;

public class BackgroundSyncService extends Service {
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // Background sync logic will be implemented here
        return START_STICKY;
    }
}
