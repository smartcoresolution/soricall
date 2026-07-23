package com.ansimsori.soricall.feature.family

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Button
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ansimsori.soricall.domain.model.FamilyMember

@Composable
fun FamilyListScreen(
    members: List<FamilyMember>,
    onSafeWord: () -> Unit,
    onVoiceProfile: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text(text = "등록된 가족", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        members.forEach { member ->
            FamilyMemberRow(member)
            Divider()
        }
        Spacer(modifier = Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            Button(modifier = Modifier.weight(1f), onClick = onSafeWord) {
                Text("안심 단어")
            }
            OutlinedButton(modifier = Modifier.weight(1f), onClick = onVoiceProfile) {
                Text("음성 등록")
            }
        }
    }
}

@Composable
private fun FamilyMemberRow(member: FamilyMember) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(text = member.name, fontSize = 21.sp, fontWeight = FontWeight.SemiBold)
        Text(
            text = "${member.relation} · 끝번호 ${member.phoneNumberLast4}",
            fontSize = 17.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

