plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.ansimsori.soricall"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.ansimsori.soricall"
        minSdk = 29
        targetSdk = 35
        versionCode = 6
        versionName = "0.3.3"
        buildConfigField("String", "SORICALL_API_BASE_URL", "\"https://www.ansimsori.ai/soricall-api\"")
    }

    signingConfigs {
        create("release") {
            val localPasswordFile = file("/home/soricall/.android/soricall-release-v2.pass")
            val localPassword = localPasswordFile.takeIf { it.isFile }?.readText()?.trim()
            storeFile = file(System.getenv("SORICALL_KEYSTORE_PATH") ?: "/home/soricall/.android/soricall-release-v2.jks")
            storePassword = System.getenv("SORICALL_KEYSTORE_PASSWORD") ?: localPassword
            keyAlias = System.getenv("SORICALL_KEY_ALIAS") ?: "soricall"
            keyPassword = System.getenv("SORICALL_KEY_PASSWORD") ?: localPassword
        }
    }

    buildTypes {
        getByName("release") {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = false
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.15"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
