package com.ansimsori.soricall

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ansimsori.soricall.domain.repository.LocalDemoRepository
import com.ansimsori.soricall.feature.callguard.SuspiciousCallScreen
import com.ansimsori.soricall.feature.emergency.EmergencyConfirmScreen
import com.ansimsori.soricall.feature.emergency.GuardianResponseScreen
import com.ansimsori.soricall.feature.family.FamilyListScreen
import com.ansimsori.soricall.feature.history.RiskHistoryScreen
import com.ansimsori.soricall.feature.onboarding.OnboardingScreen
import com.ansimsori.soricall.feature.onboarding.DeviceConnectionScreen
import com.ansimsori.soricall.feature.safeword.SafeWordScreen
import com.ansimsori.soricall.feature.settings.SettingsScreen
import com.ansimsori.soricall.feature.voiceprofile.VoiceProfileScreen
import com.ansimsori.soricall.ui.theme.SoriCallTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SoriCallTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    SoriCallApp()
                }
            }
        }
    }
}

enum class SoriCallScreen(val label: String) {
    ONBOARDING("시작"),
    CONNECTION("단말 연결"),
    FAMILY("가족"),
    SAFE_WORD("안심 단어"),
    EMERGENCY("가족 확인"),
    GUARDIAN("보호자"),
    VOICE("음성"),
    HISTORY("이력"),
    SETTINGS("설정"),
}

@Composable
fun SoriCallApp(repository: LocalDemoRepository = LocalDemoRepository()) {
    val application = androidx.compose.ui.platform.LocalContext.current.applicationContext as SoriCallApplication
    var currentScreen by remember {
        mutableStateOf(if (application.configuredSeniorId() == null) SoriCallScreen.CONNECTION else SoriCallScreen.ONBOARDING)
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                listOf(
                    SoriCallScreen.FAMILY,
                    SoriCallScreen.EMERGENCY,
                    SoriCallScreen.GUARDIAN,
                    SoriCallScreen.HISTORY,
                    SoriCallScreen.SETTINGS,
                ).forEach { screen ->
                    NavigationBarItem(
                        selected = currentScreen == screen,
                        onClick = { currentScreen = screen },
                        label = { Text(screen.label) },
                        icon = { Text(screen.label.take(1)) },
                    )
                }
            }
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(20.dp),
        ) {
            AppHeader()
            Spacer(modifier = Modifier.height(16.dp))
            when (currentScreen) {
                SoriCallScreen.CONNECTION -> DeviceConnectionScreen(
                    onConnect = { seniorId, token ->
                        application.saveConnection(seniorId, token)
                        val valid = application.api.validateSenior(seniorId)
                        if (!valid) application.clearConnection()
                        valid
                    },
                    onConnected = { currentScreen = SoriCallScreen.ONBOARDING },
                )
                SoriCallScreen.ONBOARDING -> OnboardingScreen(
                    onStart = { currentScreen = SoriCallScreen.FAMILY },
                )
                SoriCallScreen.FAMILY -> FamilyListScreen(
                    members = repository.familyMembers(),
                    onSafeWord = { currentScreen = SoriCallScreen.SAFE_WORD },
                    onVoiceProfile = { currentScreen = SoriCallScreen.VOICE },
                )
                SoriCallScreen.SAFE_WORD -> SafeWordScreen()
                SoriCallScreen.EMERGENCY -> EmergencyConfirmScreen(
                    onShowWarning = { currentScreen = SoriCallScreen.HISTORY },
                )
                SoriCallScreen.GUARDIAN -> GuardianResponseScreen(
                    notification = repository.emergencyNotification(),
                    onRespond = {
                        repository.respondToEmergency(it)
                        currentScreen = SoriCallScreen.HISTORY
                    },
                )
                SoriCallScreen.VOICE -> VoiceProfileScreen(
                    profiles = repository.voiceProfiles(),
                )
                SoriCallScreen.HISTORY -> RiskHistoryScreen(events = repository.riskEvents())
                SoriCallScreen.SETTINGS -> SettingsScreen()
            }
        }
    }
}

@Composable
private fun AppHeader() {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            text = "SoriCall",
            fontSize = 30.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = "안심소리 가족콜",
            fontSize = 18.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
fun LargeActionRow(
    primaryText: String,
    secondaryText: String,
    onPrimary: () -> Unit,
    onSecondary: () -> Unit,
) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Button(modifier = Modifier.weight(1f), onClick = onPrimary) {
            Text(primaryText)
        }
        Spacer(modifier = Modifier.width(12.dp))
        Button(modifier = Modifier.weight(1f), onClick = onSecondary) {
            Text(secondaryText)
        }
    }
}
