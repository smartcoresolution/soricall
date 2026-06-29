package com.ansimsori.soricall.core.network

interface SoriCallApiContract {
    suspend fun evaluateCall(request: CallEvaluateRequestDto): CallEvaluateResponseDto

    suspend fun createVoiceProfile(request: VoiceProfileCreateDto): String

    suspend fun addVoiceSample(profileId: String, request: VoiceSampleCreateDto): String

    suspend fun enrollVoiceProfile(profileId: String, audioRef: String): String

    suspend fun respondToEmergency(request: EmergencyRespondRequestDto): String
}

