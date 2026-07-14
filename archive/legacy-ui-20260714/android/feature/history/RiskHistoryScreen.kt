package com.ansimsori.soricall.feature.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ansimsori.soricall.domain.model.RiskEvent

@Composable
fun RiskHistoryScreen(events: List<RiskEvent>) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text(text = "위험 이력", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        events.forEach { event ->
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(text = event.title, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                Text(
                    text = "${event.riskLevel} · 끝번호 ${event.phoneNumberLast4}",
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.error,
                )
                Text(text = event.message, fontSize = 17.sp, lineHeight = 25.sp)
            }
            Divider()
        }
    }
}

