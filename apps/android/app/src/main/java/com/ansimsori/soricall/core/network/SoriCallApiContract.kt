package com.ansimsori.soricall.core.network

interface SoriCallApiContract {
    suspend fun sendSignupVerification(phoneNumber: String): PhoneVerificationDto
    suspend fun confirmSignupVerification(verificationId: String, code: String): String
    suspend fun register(phoneNumber: String, verificationToken: String, password: String, displayName: String): AuthSessionDto
    suspend fun login(phoneNumber: String, password: String): AuthSessionDto
    suspend fun createFamily(name: String, createdBy: String): String
    suspend fun createProtectedUser(familyId: String, request: ProtectedUserCreateDto): String
    suspend fun createConfirmationContact(familyId: String, protectedUserId: String, request: ConfirmationContactCreateDto): String
    suspend fun resolveDeviceEnrollment(token: String): DeviceEnrollmentDto
    suspend fun sendDeviceVerification(token: String, phoneNumber: String): PhoneVerificationDto
    suspend fun confirmDeviceVerification(token: String, verificationId: String, code: String): DeviceEnrollmentDto
    suspend fun completeDeviceEnrollment(token: String): DeviceEnrollmentDto

    suspend fun validateSenior(seniorId: String): Boolean

    suspend fun createCallSession(seniorId: String, phoneNumber: String): CallSessionResponseDto

    suspend fun reportActionResult(callSessionId: String, actionId: String, status: String)

    suspend fun evaluateCall(request: CallEvaluateRequestDto): CallEvaluateResponseDto

    suspend fun createVoiceProfile(request: VoiceProfileCreateDto): String

    suspend fun addVoiceSample(profileId: String, request: VoiceSampleCreateDto): String

    suspend fun enrollVoiceProfile(profileId: String, audioRef: String): String

    suspend fun respondToEmergency(request: EmergencyRespondRequestDto): String
}
