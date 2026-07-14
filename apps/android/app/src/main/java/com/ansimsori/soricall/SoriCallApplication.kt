package com.ansimsori.soricall

import android.app.Application
import com.ansimsori.soricall.core.network.HttpSoriCallApi
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SoriCallApplication : Application() {
    private val preferences by lazy {
        val masterKey = MasterKey.Builder(this).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        EncryptedSharedPreferences.create(
            this,
            "soricall_secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }
    val api by lazy { HttpSoriCallApi(BuildConfig.SORICALL_API_BASE_URL) { accessToken() } }

    fun configuredSeniorId(): String? =
        preferences.getString("senior_id", null)

    fun accessToken(): String? = preferences.getString("access_token", null)
    fun currentUserId(): String? = preferences.getString("user_id", null)

    fun saveAuth(accessToken: String, refreshToken: String, userId: String) {
        preferences.edit().putString("access_token", accessToken).putString("refresh_token", refreshToken).putString("user_id", userId).apply()
    }

    fun saveConnection(seniorId: String, accessToken: String) {
        preferences.edit().putString("senior_id", seniorId).putString("access_token", accessToken).apply()
    }

    fun clearConnection() {
        preferences.edit().remove("senior_id").remove("access_token").apply()
    }
}
