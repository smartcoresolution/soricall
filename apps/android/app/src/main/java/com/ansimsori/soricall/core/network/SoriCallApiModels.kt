package com.ansimsori.soricall.core.network

data class RegisterRequestDto(
    val email: String,
    val password: String,
    val displayName: String,
    val role: String,
    val phoneNumber: String? = null,
)

data class FamilyCreateDto(
    val name: String,
    val createdBy: String? = null,
)

data class FamilyMemberCreateDto(
    val name: String,
    val relation: String? = null,
    val phoneNumber: String? = null,
    val userId: String? = null,
)

data class SeniorCreateDto(
    val familyId: String,
    val name: String,
    val phoneNumber: String? = null,
    val birthYear: Int? = null,
    val userId: String? = null,
)

data class CallEvaluateRequestDto(
    val seniorId: String,
    val phoneNumber: String,
    val direction: String,
)

data class CallEvaluateResponseDto(
    val callEventId: String,
    val riskScore: Int,
    val riskLevel: String,
    val callerType: String,
    val actionRecommended: String,
    val reasonCodes: List<String>,
    val messageForSenior: String,
)

data class VoiceProfileCreateDto(
    val familyMemberId: String,
    val displayName: String,
    val consentId: String? = null,
)

data class VoiceSampleCreateDto(
    val audioRef: String,
    val objectKey: String? = null,
    val durationMs: Int? = null,
    val sampleRate: Int? = null,
    val mimeType: String? = null,
    val purpose: String = "ENROLLMENT",
)

data class EmergencyRespondRequestDto(
    val notificationId: String,
    val response: String,
)

