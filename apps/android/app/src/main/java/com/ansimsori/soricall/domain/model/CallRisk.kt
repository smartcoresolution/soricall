package com.ansimsori.soricall.domain.model

data class CallRisk(
    val score: Int,
    val level: RiskLevel,
    val shouldBlock: Boolean,
    val shouldReject: Boolean,
    val shouldSilence: Boolean,
    val reasonCodes: List<String>,
)

