package com.ansimsori.soricall.service

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import com.ansimsori.soricall.MainActivity
import com.ansimsori.soricall.SoriCallApplication
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class SoriFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        (application as SoriCallApplication).registerPushToken(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val confirmationId = message.data["confirmation_id"]
        val riskEventId = message.data["risk_event_id"]
        val deepLink = when {
            confirmationId != null -> "soricall://connect?confirmation_id=$confirmationId"
            riskEventId != null -> "soricall://connect?risk_event_id=$riskEventId"
            else -> "soricall://connect"
        }
        val intent = Intent(this, MainActivity::class.java)
            .setAction(Intent.ACTION_VIEW)
            .setData(Uri.parse(deepLink))
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val pendingIntent = PendingIntent.getActivity(
            this,
            deepLink.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "가족 통화 확인", NotificationManager.IMPORTANCE_HIGH),
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(message.notification?.title ?: "가족 통화 확인 요청")
            .setContentText(message.notification?.body ?: "확인이 필요한 전화가 있습니다.")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()
        if (
            ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        ) {
            manager.notify(deepLink.hashCode(), notification)
        }
    }

    private companion object {
        const val CHANNEL_ID = "family_confirmation"
    }
}
