package com.ansimsori.soricall

import android.app.Application
import com.ansimsori.soricall.core.network.HttpSoriCallApi
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class SoriCallApplication : Application() {
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
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

    fun pendingDeviceToken(): String? = preferences.getString("device_enrollment_token", null)

    fun savePendingDeviceToken(token: String) {
        preferences.edit().putString("device_enrollment_token", token).apply()
    }

    fun savePendingSharedMedia(uri: String, mimeType: String?) {
        val current = preferences.getStringSet("pending_shared_media_uris", emptySet()).orEmpty()
        preferences.edit()
            .putStringSet("pending_shared_media_uris", current + uri)
            .putString("pending_shared_media_mime", mimeType)
            .apply()
    }

    fun pendingSharedMedia(): Set<String> =
        preferences.getStringSet("pending_shared_media_uris", emptySet()).orEmpty()

    fun clearPendingSharedMedia() {
        preferences.edit().remove("pending_shared_media_uris").remove("pending_shared_media_mime").apply()
    }

    fun accessToken(): String? = preferences.getString("access_token", null)
    fun currentUserId(): String? = preferences.getString("user_id", null)
    fun screeningFamilyHashes(): Set<String> =
        preferences.getStringSet("screening_family_hashes", emptySet()) ?: emptySet()
    fun screeningRiskHashes(): Set<String> =
        preferences.getStringSet("screening_risk_hashes", emptySet()) ?: emptySet()

    suspend fun refreshScreeningCache(seniorId: String) {
        val cache = api.getScreeningCache(seniorId)
        preferences.edit()
            .putStringSet("screening_family_hashes", cache.familyNumberHashes)
            .putStringSet("screening_risk_hashes", cache.riskNumberHashes)
            .putString("screening_cache_version", cache.version)
            .putLong("screening_cache_updated_at", System.currentTimeMillis())
            .apply()
    }

    fun recordScreeningDecision(source: String, elapsedMs: Long) {
        preferences.edit()
            .putString("last_screening_source", source)
            .putLong("last_screening_elapsed_ms", elapsedMs)
            .putLong("last_screening_at", System.currentTimeMillis())
            .apply()
    }

    fun registerPushToken(token: String) {
        preferences.edit().putString("fcm_token", token).apply()
        if (accessToken().isNullOrBlank()) return
        applicationScope.launch {
            runCatching { api.registerPushToken(token) }
        }
    }

    fun saveAuth(accessToken: String, refreshToken: String, userId: String, seniorId: String? = null) {
        preferences.edit()
            .putString("access_token", accessToken)
            .putString("refresh_token", refreshToken)
            .putString("user_id", userId)
            .apply {
                if (seniorId != null) putString("senior_id", seniorId)
            }
            .apply()
        preferences.getString("fcm_token", null)?.let(::registerPushToken)
    }

    fun saveConnection(seniorId: String, accessToken: String) {
        preferences.edit().putString("senior_id", seniorId).putString("access_token", accessToken).apply()
    }

    fun completeDeviceConnection(seniorId: String) {
        preferences.edit().putString("senior_id", seniorId).remove("device_enrollment_token").apply()
    }

    fun clearConnection() {
        preferences.edit().remove("senior_id").remove("access_token").apply()
    }
}
