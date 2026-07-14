package com.ansimsori.soricall.feature.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SettingsScreen() {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text(text = "설정", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Text(
            text = "동의 이력, 개인정보 삭제, 알림 설정을 이곳에서 관리합니다.",
            fontSize = 19.sp,
            lineHeight = 28.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(text = "통화 녹음 우회 기능은 제공하지 않습니다.", fontSize = 18.sp)
    }
}

