package com.ansimsori.soricall.service

import android.telecom.Call
import android.telecom.CallScreeningService
import android.telecom.CallScreeningService.CallResponse
import com.ansimsori.soricall.domain.repository.CallRiskRepository

class SoriCallScreeningService : CallScreeningService() {
    private val callRiskRepository = CallRiskRepository()

    override fun onScreenCall(callDetails: Call.Details) {
        val phoneNumber = callDetails.handle?.schemeSpecificPart
        if (phoneNumber.isNullOrBlank()) {
            respondToCall(callDetails, allowCallResponse())
            return
        }

        val risk = callRiskRepository.evaluateIncomingNumber(phoneNumber)
        val response = CallResponse.Builder()
            .setDisallowCall(risk.shouldBlock)
            .setRejectCall(risk.shouldReject)
            .setSilenceCall(risk.shouldSilence)
            .setSkipCallLog(false)
            .setSkipNotification(false)
            .build()

        respondToCall(callDetails, response)
    }

    private fun allowCallResponse(): CallResponse {
        return CallResponse.Builder()
            .setDisallowCall(false)
            .setRejectCall(false)
            .setSilenceCall(false)
            .setSkipCallLog(false)
            .setSkipNotification(false)
            .build()
    }
}
