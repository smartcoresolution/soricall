package com.ansimsori.soricall.core.network

import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class HttpSoriCallApi(
    private val baseUrl: String,
    private val tokenProvider: () -> String? = { null },
) : SoriCallApiContract by MockSoriCallApi() {
    override suspend fun register(email: String, password: String, displayName: String): AuthSessionDto = withContext(Dispatchers.IO) {
        parseAuth(request("/api/v1/auth/register", JSONObject().put("email", email).put("password", password).put("display_name", displayName).put("role", "GUARDIAN")))
    }

    override suspend fun login(email: String, password: String): AuthSessionDto = withContext(Dispatchers.IO) {
        parseAuth(request("/api/v1/auth/login", JSONObject().put("email", email).put("password", password)))
    }

    override suspend fun createFamily(name: String, createdBy: String): String = withContext(Dispatchers.IO) {
        request("/api/v1/families", JSONObject().put("name", name).put("created_by", createdBy)).getString("id")
    }

    override suspend fun createProtectedUser(familyId: String, request: ProtectedUserCreateDto): String = withContext(Dispatchers.IO) {
        this@HttpSoriCallApi.request("/api/v1/families/$familyId/protected-call-users", JSONObject().put("name", request.name).put("phone_number", request.phoneNumber).put("relation_code", request.relationCode)).getString("id")
    }

    override suspend fun createConfirmationContact(familyId: String, protectedUserId: String, request: ConfirmationContactCreateDto): String = withContext(Dispatchers.IO) {
        this@HttpSoriCallApi.request("/api/v1/families/$familyId/protected-call-users/$protectedUserId/confirmation-contacts", JSONObject().put("name", request.name).put("phone_number", request.phoneNumber).put("relation_code", request.relationCode).put("is_primary_contact", request.primary).put("notification_priority", 1).put("notify_enabled", true)).getString("id")
    }

    private fun parseAuth(json: JSONObject): AuthSessionDto {
        val user = json.getJSONObject("user")
        return AuthSessionDto(json.getString("access_token"), json.getString("refresh_token"), user.getString("id"), user.getString("display_name"))
    }
    override suspend fun validateSenior(seniorId: String): Boolean = withContext(Dispatchers.IO) {
        runCatching { get("/api/v1/seniors/$seniorId").getString("id") == seniorId }.getOrDefault(false)
    }

    override suspend fun createCallSession(seniorId: String, phoneNumber: String): CallSessionResponseDto =
        withContext(Dispatchers.IO) {
            val json = request(
                "/api/v1/call-sessions",
                JSONObject().put("senior_id", seniorId).put("phone_number", phoneNumber).put("direction", "INCOMING"),
            )
            CallSessionResponseDto(
                callSessionId = json.getString("call_session_id"),
                responseActionId = json.getString("response_action_id"),
                riskScore = json.getInt("risk_score"),
                riskLevel = json.getString("risk_level"),
                decision = json.getString("decision"),
                reasonCodes = json.getJSONArray("reason_codes").let { array ->
                    List(array.length()) { array.getString(it) }
                },
            )
        }

    override suspend fun reportActionResult(callSessionId: String, actionId: String, status: String) {
        withContext(Dispatchers.IO) {
            request(
                "/api/v1/call-sessions/$callSessionId/actions/$actionId/result",
                JSONObject().put("status", status),
            )
        }
    }

    private fun request(path: String, body: JSONObject): JSONObject {
        val connection = URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 1_500
        connection.readTimeout = 1_500
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json")
        tokenProvider()?.takeIf { it.isNotBlank() }?.let {
            connection.setRequestProperty("Authorization", "Bearer $it")
        }
        connection.outputStream.use { it.write(body.toString().toByteArray()) }
        val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
        val responseBody = stream.bufferedReader().use { it.readText() }
        if (connection.responseCode !in 200..299) error("SoriCall API ${connection.responseCode}: $responseBody")
        return JSONObject(responseBody)
    }

    private fun get(path: String): JSONObject {
        val connection = URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 1_500
        connection.readTimeout = 1_500
        tokenProvider()?.takeIf { it.isNotBlank() }?.let {
            connection.setRequestProperty("Authorization", "Bearer $it")
        }
        val responseBody = connection.inputStream.bufferedReader().use { it.readText() }
        return JSONObject(responseBody)
    }
}
