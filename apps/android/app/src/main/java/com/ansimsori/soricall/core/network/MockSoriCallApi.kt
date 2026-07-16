package com.ansimsori.soricall.core.network

class MockSoriCallApi : SoriCallApiContract {
    override suspend fun sendSignupVerification(phoneNumber: String) = PhoneVerificationDto("mock-signup-verification", "123456")
    override suspend fun confirmSignupVerification(verificationId: String, code: String) = "mock-verification-token"
    override suspend fun register(phoneNumber: String, verificationToken: String, password: String, displayName: String) = AuthSessionDto("mock-token", "mock-refresh", "mock-user", displayName)
    override suspend fun login(phoneNumber: String, password: String) = AuthSessionDto("mock-token", "mock-refresh", "mock-user", "사용자")
    override suspend fun createFamily(name: String, createdBy: String) = "mock-family"
    override suspend fun createProtectedUser(familyId: String, request: ProtectedUserCreateDto) = "mock-protected-user"
    override suspend fun createConfirmationContact(familyId: String, protectedUserId: String, request: ConfirmationContactCreateDto) = "mock-contact"
    override suspend fun resolveDeviceEnrollment(token: String) = DeviceEnrollmentDto("mock-enrollment", "mock-protected-user", "부모님", "1234", "INVITED")
    override suspend fun sendDeviceVerification(token: String, phoneNumber: String) = PhoneVerificationDto("mock-verification", "123456")
    override suspend fun confirmDeviceVerification(token: String, verificationId: String, code: String) = DeviceEnrollmentDto("mock-enrollment", "mock-protected-user", "부모님", "1234", "PHONE_VERIFIED")
    override suspend fun completeDeviceEnrollment(token: String) = DeviceEnrollmentDto("mock-enrollment", "mock-protected-user", "부모님", "1234", "ACTIVE")

    override suspend fun validateSenior(seniorId: String) = seniorId.isNotBlank()

    override suspend fun createCallSession(seniorId: String, phoneNumber: String) =
        CallSessionResponseDto("mock-session", "mock-action", 20, "LOW", "VERIFY", listOf("UNKNOWN_NUMBER"))

    override suspend fun reportActionResult(callSessionId: String, actionId: String, status: String) = Unit

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
