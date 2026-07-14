package com.ansimsori.soricall.feature.emergency

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ansimsori.soricall.domain.model.EmergencyNotification
import com.ansimsori.soricall.domain.model.GuardianResponse

@Composable
fun GuardianResponseScreen(
    notification: EmergencyNotification,
    onRespond: (GuardianResponse) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(text = notification.title, fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Text(
            text = notification.message,
            fontSize = 21.sp,
            lineHeight = 30.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = { onRespond(GuardianResponse.REAL_CALL) }) {
            Text(text = "내가 전화함", fontSize = 20.sp)
        }
        Button(onClick = { onRespond(GuardianResponse.NOT_ME) }) {
            Text(text = "내가 아님, 사칭 의심", fontSize = 20.sp)
        }
        OutlinedButton(onClick = { onRespond(GuardianResponse.UNKNOWN) }) {
            Text(text = "확인 어려움", fontSize = 20.sp)
        }
    }
}
