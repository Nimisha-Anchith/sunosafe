plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "app.sunosafe.companion"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.sunosafe.companion"
        minSdk = 26          // Android 8.0: notification channels
        targetSdk = 35
        versionCode = 5
        versionName = "0.5.0"
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
    // Deliberately no libraries: only Android's own APIs and the Kotlin standard
    // library, so there is very little third-party code inside a security app.
    testImplementation("junit:junit:4.13.2")
}
