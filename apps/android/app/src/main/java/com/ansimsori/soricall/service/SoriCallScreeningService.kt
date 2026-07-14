package com.ansimsori.soricall.service

import android.telecom.Call
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import android.telecom.CallScreeningService
import android.telecom.CallScreeningService.CallResponse
import com.ansimsori.soricall.domain.repository.CallRiskRepository
import com.ansimsori.soricall.SoriCallApplication
import com.ansimsori.soricall.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

class SoriCallScreeningService : CallScreeningService() {
    private val callRiskRepository = CallRiskRepository()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    override fun onScreenCall(callDetails: Call.Details) {
        val phoneNumber = callDetails.handle?.schemeSpecificPart
        if (phoneNumber.isNullOrBlank()) {
            respondToCall(callDetails, allowCallResponse())
            return
        }

        val application = applicationContext as SoriCallApplication
        val seniorId = application.configuredSeniorId()
        if (seniorId == null) {
            respondToCall(callDetails, responseFor(callRiskRepository.evaluateIncomingNumber(phoneNumber)))
            return
        }
        scope.launch {
            val serverResult = withTimeoutOrNull(2_500) {
                runCatching { application.api.createCallSession(seniorId, phoneNumber) }.getOrNull()
            }
            if (serverResult == null) {
                respondToCall(callDetails, responseFor(callRiskRepository.evaluateIncomingNumber(phoneNumber)))
                return@launch
            }
            val block = serverResult.decision == "BLOCK"
            val silence = serverResult.decision in setOf("BLOCK", "RECALL")
            val response = CallResponse.Builder()
                .setDisallowCall(block)
                .setRejectCall(block)
                .setSilenceCall(silence)
                .setSkipCallLog(false)
                .setSkipNotification(false)
                .build()
            respondToCall(callDetails, response)
            if (serverResult.decision != "ALLOW") showWarning(serverResult.riskLevel)
            runCatching {
                application.api.reportActionResult(serverResult.callSessionId, serverResult.responseActionId, "EXECUTED")
            }
        }
    }

    private fun showWarning(riskLevel: String) {
        val manager = getSystemService(NotificationManager::class.java)
        val channelId = "soricall_call_warning"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(channelId, "의심 전화 경고", NotificationManager.IMPORTANCE_HIGH),
            )
        }
        val intent = Intent(this, MainActivity::class.java).putExtra("risk_level", riskLevel)
        val pendingIntent = PendingIntent.getActivity(
            this, 1001, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = android.app.Notification.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.stat_sys_warning)
            .setContentTitle("가족 사칭 의심 전화")
            .setContentText("전화를 끊고 저장된 가족 번호로 다시 확인하세요.")
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true)
            .setAutoCancel(true)
            .build()
        manager.notify(1001, notification)
    }

    private fun responseFor(risk: com.ansimsori.soricall.domain.model.CallRisk): CallResponse {
        val response = CallResponse.Builder()
            .setDisallowCall(risk.shouldBlock)
            .setRejectCall(risk.shouldReject)
            .setSilenceCall(risk.shouldSilence)
            .setSkipCallLog(false)
            .setSkipNotification(false)
            .build()

        return response
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
