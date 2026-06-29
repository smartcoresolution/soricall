package com.ansimsori.soricall.feature.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun OnboardingScreen(onStart: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Text(
            text = "가족 사칭 전화를 한 번 더 확인합니다.",
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
            lineHeight = 34.sp,
        )
        Text(
            text = "모르는 번호, 돈 요구, 앱 설치 요구가 보이면 보호자에게 바로 알립니다.",
            fontSize = 19.sp,
            lineHeight = 28.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(modifier = Modifier.fillMaxWidth(), onClick = onStart) {
            Text(text = "시작하기", fontSize = 20.sp)
        }
    }
}

