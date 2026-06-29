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

@Composable
fun EmergencyConfirmScreen(onShowWarning: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(text = "가족 확인", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Text(
            text = "가족 목소리처럼 들려도 AI로 조작될 수 있습니다.",
            fontSize = 21.sp,
            lineHeight = 30.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = onShowWarning) {
            Text(text = "보호자에게 확인 요청", fontSize = 20.sp)
        }
        OutlinedButton(onClick = onShowWarning) {
            Text(text = "위험 이력 보기", fontSize = 20.sp)
        }
    }
}

