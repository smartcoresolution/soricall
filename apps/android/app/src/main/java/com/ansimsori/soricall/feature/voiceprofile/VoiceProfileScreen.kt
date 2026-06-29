package com.ansimsori.soricall.feature.voiceprofile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Divider
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ansimsori.soricall.domain.model.VoiceProfile

@Composable
fun VoiceProfileScreen(profiles: List<VoiceProfile> = emptyList()) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(text = "가족 음성 등록", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Text(
            text = "가족이 직접 누른 뒤 짧은 음성 샘플을 등록합니다. 통화 녹음은 하지 않습니다.",
            fontSize = 19.sp,
            lineHeight = 28.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = {}) {
            Text(text = "음성 샘플 등록", fontSize = 20.sp)
        }
        profiles.forEach { profile ->
            Divider()
            Text(text = profile.displayName, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            Text(
                text = "${profile.status} · 품질 ${profile.qualityScore ?: 0}",
                fontSize = 17.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
