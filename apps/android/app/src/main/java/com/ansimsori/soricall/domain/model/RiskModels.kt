package com.ansimsori.soricall.domain.model

enum class RiskLevel {
    LOW,
    CAUTION,
    HIGH,
    CRITICAL,
}

data class RiskEvent(
    val id: String,
    val title: String,
    val phoneNumberLast4: String,
    val riskLevel: RiskLevel,
    val message: String,
)

data class FamilyMember(
    val id: String,
    val name: String,
    val relation: String,
    val phoneNumberLast4: String,
)

enum class GuardianResponse {
    REAL_CALL,
    NOT_ME,
    UNKNOWN,
}

data class EmergencyNotification(
    val id: String,
    val title: String,
    val message: String,
    val status: String,
)

data class VoiceProfile(
    val id: String,
    val displayName: String,
    val status: String,
    val qualityScore: Int?,
)
