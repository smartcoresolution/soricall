package com.ansimsori.soricall.core.network

class MockSoriCallApi : SoriCallApiContract {
    override suspend fun evaluateCall(request: CallEvaluateRequestDto): CallEvaluateResponseDto {
        val isRiskNumber = request.phoneNumber.endsWith("0000") || request.phoneNumber.endsWith("7777")
        return CallEvaluateResponseDto(
            callEventId = "mock-call-event",
            riskScore = if (isRiskNumber) 90 else 30,
            riskLevel = if (isRiskNumber) "CRITICAL" else "LOW",
            callerType = if (isRiskNumber) "RISK_NUMBER" else "UNKNOWN",
            actionRecommended = if (isRiskNumber) {
                "SILENCE_OR_BLOCK_AND_NOTIFY_GUARDIAN"
            } else {
                "ALLOW"
            },
            reasonCodes = if (isRiskNumber) listOf("RISK_NUMBER_MATCH") else emptyList(),
            messageForSenior = if (isRiskNumber) {
                "매우 위험한 전화일 수 있습니다."
            } else {
                "일반 전화로 보입니다."
            },
        )
    }

    override suspend fun createVoiceProfile(request: VoiceProfileCreateDto): String {
        return "mock-voice-profile"
    }

    override suspend fun addVoiceSample(profileId: String, request: VoiceSampleCreateDto): String {
        return "mock-voice-sample"
    }

    override suspend fun enrollVoiceProfile(profileId: String, audioRef: String): String {
        return "ENROLLED"
    }

    override suspend fun respondToEmergency(request: EmergencyRespondRequestDto): String {
        return "RESPONDED"
    }
}

