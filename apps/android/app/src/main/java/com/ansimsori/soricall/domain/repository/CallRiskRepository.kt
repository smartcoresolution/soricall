package com.ansimsori.soricall.domain.repository

import com.ansimsori.soricall.domain.model.CallRisk
import com.ansimsori.soricall.domain.model.RiskLevel
import java.security.MessageDigest

class CallRiskRepository(
    private val familyNumberHashes: Set<String> = emptySet(),
    private val riskNumberHashes: Set<String> = emptySet(),
) {
    fun evaluateIncomingNumber(phoneNumber: String): CallRisk {
        val normalized = phoneNumber.filter { it.isDigit() || it == '+' }
        val numberHash = MessageDigest.getInstance("SHA-256")
            .digest("phone-number:$normalized".toByteArray())
            .joinToString("") { "%02x".format(it) }

        return when {
            numberHash in familyNumberHashes -> CallRisk(
                score = 10,
                level = RiskLevel.LOW,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = false,
                reasonCodes = emptyList(),
            )
            numberHash in riskNumberHashes -> CallRisk(
                score = 90,
                level = RiskLevel.CRITICAL,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = true,
                reasonCodes = listOf("RISK_NUMBER_MATCH"),
            )
            normalized.isBlank() -> CallRisk(
                score = 45,
                level = RiskLevel.CAUTION,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = false,
                reasonCodes = listOf("UNKNOWN_NUMBER"),
            )
            else -> CallRisk(
                score = 30,
                level = RiskLevel.CAUTION,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = false,
                reasonCodes = listOf("UNKNOWN_NUMBER"),
            )
        }
    }
}
