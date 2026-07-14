package com.ansimsori.soricall.feature.safeword

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SafeWordScreen() {
    var safeWordHint by remember { mutableStateOf("우리 가족만 아는 단어") }

    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text(text = "안심 단어", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Text(
            text = "통화 중 가족이 맞는지 확인할 때 사용합니다. 원문은 서버에 저장하지 않습니다.",
            fontSize = 18.sp,
            lineHeight = 27.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = safeWordHint,
            onValueChange = { safeWordHint = it },
            label = { Text("힌트") },
        )
    }
}

