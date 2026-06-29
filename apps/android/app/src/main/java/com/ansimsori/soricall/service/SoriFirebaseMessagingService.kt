package com.ansimsori.soricall.service

class SoriFirebaseMessagingService {
    fun handleGuardianNotificationPlaceholder(message: String): GuardianPushPayload {
        return GuardianPushPayload(
            title = "가족 사칭 의심 전화",
            message = message,
            notificationId = "placeholder-notification-id",
        )
    }
}

data class GuardianPushPayload(
    val title: String,
    val message: String,
    val notificationId: String,
)
