package com.ansimsori.soricall.domain.repository

import com.ansimsori.soricall.domain.model.FamilyMember
import com.ansimsori.soricall.domain.model.EmergencyNotification
import com.ansimsori.soricall.domain.model.GuardianResponse
import com.ansimsori.soricall.domain.model.RiskEvent
import com.ansimsori.soricall.domain.model.RiskLevel
import com.ansimsori.soricall.domain.model.VoiceProfile

class LocalDemoRepository {
    fun familyMembers(): List<FamilyMember> = listOf(
        FamilyMember(
            id = "family-1",
            name = "김민수",
            relation = "아들",
            phoneNumberLast4 = "5678",
        ),
        FamilyMember(
            id = "family-2",
            name = "박지은",
            relation = "딸",
            phoneNumberLast4 = "1122",
        ),
    )

    fun riskEvents(): List<RiskEvent> = listOf(
        RiskEvent(
            id = "risk-1",
            title = "모르는 번호 주의",
            phoneNumberLast4 = "0000",
            riskLevel = RiskLevel.CAUTION,
            message = "가족이라고 해도 저장된 가족 번호로 다시 확인하세요.",
        ),
        RiskEvent(
            id = "risk-2",
            title = "위험번호 차단 권장",
            phoneNumberLast4 = "7777",
            riskLevel = RiskLevel.CRITICAL,
            message = "전화를 끊고 보호자에게 확인하세요.",
        ),
    )

    fun emergencyNotification(): EmergencyNotification = EmergencyNotification(
        id = "emergency-1",
        title = "가족 사칭 의심 전화",
        message = "부모님이 가족 사칭 의심 전화를 받고 있습니다.",
        status = "SENT",
    )

    fun respondToEmergency(response: GuardianResponse): String {
        return when (response) {
            GuardianResponse.REAL_CALL -> "내가 전화함"
            GuardianResponse.NOT_ME -> "내가 아님, 사칭 의심"
            GuardianResponse.UNKNOWN -> "확인 어려움"
        }
    }

    fun voiceProfiles(): List<VoiceProfile> = listOf(
        VoiceProfile(
            id = "voice-1",
            displayName = "김민수 목소리",
            status = "ENROLLED",
            qualityScore = 95,
        ),
    )
}
