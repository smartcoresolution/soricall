package com.ansimsori.soricall.feature.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun DeviceConnectionScreen(onConnect: suspend (String, String) -> Boolean, onConnected: () -> Unit) {
    var seniorId by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }
    var working by remember { mutableStateOf(false) }
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("어르신 단말 연결")
        Text("보호자 앱에서 확인한 어르신 ID와 로그인 토큰을 입력하세요.")
        OutlinedTextField(seniorId, { seniorId = it.trim() }, label = { Text("어르신 ID") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(token, { token = it.trim() }, label = { Text("로그인 토큰") }, modifier = Modifier.fillMaxWidth())
        Button(
            enabled = seniorId.isNotBlank() && token.isNotBlank() && !working,
            onClick = {
                working = true
                scope.launch {
                    if (onConnect(seniorId, token)) onConnected() else message = "연결 정보를 확인할 수 없습니다."
                    working = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (working) "확인 중" else "이 단말 연결") }
        message?.let { Text(it) }
    }
}
