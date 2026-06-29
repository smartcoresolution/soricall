package com.ansimsori.soricall.domain.repository

import com.ansimsori.soricall.domain.model.CallRisk
import com.ansimsori.soricall.domain.model.RiskLevel

class CallRiskRepository {
    fun evaluateIncomingNumber(phoneNumber: String): CallRisk {
        val digits = phoneNumber.filter { it.isDigit() }
        val last4 = digits.takeLast(4)

        return when {
            last4 in setOf("7777", "0000") -> CallRisk(
                score = 90,
                level = RiskLevel.CRITICAL,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = true,
                reasonCodes = listOf("RISK_NUMBER_MATCH"),
            )
            last4.isBlank() -> CallRisk(
                score = 45,
                level = RiskLevel.CAUTION,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = false,
                reasonCodes = listOf("UNKNOWN_NUMBER"),
            )
            else -> CallRisk(
                score = 30,
                level = RiskLevel.LOW,
                shouldBlock = false,
                shouldReject = false,
                shouldSilence = false,
                reasonCodes = emptyList(),
            )
        }
    }
}

