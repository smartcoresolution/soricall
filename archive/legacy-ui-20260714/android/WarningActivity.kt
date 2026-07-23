package com.ansimsori.soricall

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ansimsori.soricall.feature.callguard.SuspiciousCallScreen
import com.ansimsori.soricall.ui.theme.SoriCallTheme

class WarningActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SoriCallTheme {
                Surface(Modifier.fillMaxSize().padding(24.dp)) {
                    SuspiciousCallScreen(onGuardianAlert = { finish() })
                }
            }
        }
    }
}
