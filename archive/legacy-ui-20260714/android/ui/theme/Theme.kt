package com.ansimsori.soricall.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val SoriCallColors: ColorScheme = lightColorScheme(
    primary = Color(0xFF155E75),
    onPrimary = Color.White,
    secondary = Color(0xFF4D7C0F),
    tertiary = Color(0xFFB45309),
    error = Color(0xFFB91C1C),
    background = Color(0xFFF8FAFC),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF111827),
    onSurfaceVariant = Color(0xFF4B5563),
)

@Composable
fun SoriCallTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = SoriCallColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}

