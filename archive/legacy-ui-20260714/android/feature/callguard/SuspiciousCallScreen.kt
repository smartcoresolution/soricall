package com.ansimsori.soricall.feature.callguard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SuspiciousCallScreen(onGuardianAlert: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(
            text = "위험한 전화일 수 있습니다",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.error,
        )
        Text(
            text = "돈을 보내라거나 앱을 설치하라고 하면 전화를 끊으세요.",
            fontSize = 21.sp,
            lineHeight = 30.sp,
        )
        Button(onClick = onGuardianAlert) {
            Text(text = "보호자에게 확인", fontSize = 20.sp)
        }
    }
}

