package com.ansimsori.soricall

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ansimsori.soricall.core.network.ConfirmationContactCreateDto
import com.ansimsori.soricall.core.network.ProtectedUserCreateDto
import kotlinx.coroutines.launch

private val Teal = Color(0xFF0D766B)
private val TealSoft = Color(0xFFE3F3EE)
private val Orange = Color(0xFFDE7147)
private val OrangeSoft = Color(0xFFFFF0E4)
private val Red = Color(0xFFD44A3E)
private val RedSoft = Color(0xFFFEE9E5)
private val Ink = Color(0xFF18312E)
private val Muted = Color(0xFF71837F)

class MainActivity : ComponentActivity() {
    private val incomingRisk = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        incomingRisk.value = intent.getStringExtra("risk_level")
        setContent { SoriCallAndroidApp(incomingRisk.value) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        incomingRisk.value = intent.getStringExtra("risk_level")
    }
}

private enum class AppScreen {
    PARENT_READY, START, SIGNUP, CONSENT, LOGIN, HOME, PROTECTED, CONTACT, BIOMETRICS,
    NORMAL, ANALYSIS, BLOCKED, CONFIRM, HISTORY, SETTINGS,
}

@Composable
private fun SoriCallAndroidApp(incomingRisk: String?) {
    val application = LocalContext.current.applicationContext as SoriCallApplication
    val scope = rememberCoroutineScope()
    var screen by remember(incomingRisk) {
        mutableStateOf(
            when (incomingRisk) {
                "CRITICAL" -> AppScreen.BLOCKED
                "HIGH", "CAUTION" -> AppScreen.ANALYSIS
                else -> AppScreen.PARENT_READY
            },
        )
    }
    var signupName by remember { mutableStateOf("") }; var signupEmail by remember { mutableStateOf("") }; var signupPassword by remember { mutableStateOf("") }
    var loginEmail by remember { mutableStateOf("") }; var loginPassword by remember { mutableStateOf("") }
    var familyId by remember { mutableStateOf<String?>(null) }; var protectedUserId by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }; var busy by remember { mutableStateOf(false) }
    fun apiAction(action: suspend () -> Unit) { scope.launch { busy = true; error = null; runCatching { action() }.onFailure { error = it.message ?: "요청을 처리하지 못했습니다." }; busy = false } }
    val colors = lightColorScheme(primary = Teal, secondary = Orange, error = Red, onSurface = Ink)
    MaterialTheme(colorScheme = colors) {
        Scaffold(
            containerColor = Color(0xFFF5F8F6),
            bottomBar = {
                if (screen in listOf(AppScreen.HOME, AppScreen.PROTECTED, AppScreen.HISTORY, AppScreen.SETTINGS)) {
                    NavigationBar(containerColor = Color.White) {
                        Nav("홈", "⌂", screen == AppScreen.HOME) { screen = AppScreen.HOME }
                        Nav("가족", "♧", screen == AppScreen.PROTECTED) { screen = AppScreen.PROTECTED }
                        Nav("기록", "◷", screen == AppScreen.HISTORY) { screen = AppScreen.HISTORY }
                        Nav("설정", "⚙", screen == AppScreen.SETTINGS) { screen = AppScreen.SETTINGS }
                    }
                }
            },
        ) { padding ->
            Surface(
                modifier = Modifier.fillMaxSize().padding(padding),
                color = Color.Transparent,
            ) {
                when (screen) {
                    AppScreen.PARENT_READY -> ParentReadyScreen()
                    AppScreen.START -> StartScreen({ screen = AppScreen.SIGNUP }, { screen = AppScreen.LOGIN })
                    AppScreen.SIGNUP -> SignupScreen(signupName, { signupName = it }, signupEmail, { signupEmail = it }, signupPassword, { signupPassword = it }) { screen = AppScreen.CONSENT }
                    AppScreen.CONSENT -> ConsentScreen { apiAction { val auth = application.api.register(signupEmail, signupPassword, signupName); application.saveAuth(auth.accessToken, auth.refreshToken, auth.userId); screen = AppScreen.PROTECTED } }
                    AppScreen.LOGIN -> LoginScreen(loginEmail, { loginEmail = it }, loginPassword, { loginPassword = it }) { apiAction { val auth = application.api.login(loginEmail, loginPassword); application.saveAuth(auth.accessToken, auth.refreshToken, auth.userId); screen = AppScreen.HOME } }
                    AppScreen.PROTECTED -> ProtectedFamilyScreen { name, phone, relation -> apiAction { val userId = checkNotNull(application.currentUserId()) { "로그인이 필요합니다." }; val newFamily = familyId ?: application.api.createFamily("$name 통화보호 가족", userId).also { familyId = it }; protectedUserId = application.api.createProtectedUser(newFamily, ProtectedUserCreateDto(name, phone, protectedRelationCode(relation))); screen = AppScreen.CONTACT } }
                    AppScreen.CONTACT -> ConfirmationContactScreen { name, phone, relation, primary -> apiAction { application.api.createConfirmationContact(checkNotNull(familyId) { "가족 정보가 없습니다." }, checkNotNull(protectedUserId) { "보호받을 가족 정보가 없습니다." }, ConfirmationContactCreateDto(name, phone, contactRelationCode(relation), primary)); screen = AppScreen.BIOMETRICS } }
                    AppScreen.BIOMETRICS -> BiometricsScreen { screen = AppScreen.HOME }
                    AppScreen.HOME -> HomeScreen { screen = it }
                    AppScreen.NORMAL -> NormalCallScreen { screen = AppScreen.HOME }
                    AppScreen.ANALYSIS -> AnalysisScreen({ screen = AppScreen.BLOCKED }, { screen = AppScreen.CONFIRM })
                    AppScreen.BLOCKED -> BlockedScreen({ screen = AppScreen.CONFIRM }, { screen = AppScreen.HOME })
                    AppScreen.CONFIRM -> ConfirmationRequestScreen { screen = AppScreen.HISTORY }
                    AppScreen.HISTORY -> HistoryScreen()
                    AppScreen.SETTINGS -> SettingsScreen()
                }
                if (busy) Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = .18f)), contentAlignment = Alignment.Center) { Pill("안전하게 저장하고 있습니다…", Teal, Color.White) }
                error?.let { Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.BottomCenter) { Text(it, color = Color.White, modifier = Modifier.background(Red, RoundedCornerShape(12.dp)).padding(14.dp)) } }
            }
        }
    }
}

@Composable
private fun ParentReadyScreen() {
    val activity = LocalContext.current as? ComponentActivity
    Page {
        Spacer(Modifier.height(34.dp))
        StatusIcon("✓", TealSoft, Teal, 92)
        Spacer(Modifier.height(26.dp))
        Text("SoriCall 설치 완료", fontSize = 29.sp, fontWeight = FontWeight.ExtraBold, color = Ink)
        Spacer(Modifier.height(12.dp))
        Body("부모님 전화 보호를 연결하려면\n방금 전 설치 안내 화면으로 돌아가 주세요.", centered = true)
        Spacer(Modifier.height(24.dp))
        InfoCard("다음 단계", "설치 안내 화면에서 ‘설치를 완료했어요’를 누른 뒤 휴대전화 본인 확인과 권한 설정을 진행합니다.")
        Spacer(Modifier.weight(1f))
        PrimaryButton("설치 안내 화면으로 돌아가기", { activity?.finish() })
        Caption("화면이 닫히면 브라우저의 SoriCall 설치 안내가 다시 표시됩니다.")
    }
}

private fun protectedRelationCode(value: String) = mapOf("아버지" to "FATHER", "어머니" to "MOTHER", "할아버지" to "GRANDFATHER", "할머니" to "GRANDMOTHER")[value] ?: "OTHER"
private fun contactRelationCode(value: String) = mapOf("아들" to "SON", "딸" to "DAUGHTER", "손자" to "GRANDSON", "손녀" to "GRANDDAUGHTER", "배우자" to "SPOUSE")[value] ?: "OTHER"

@Composable
private fun StartScreen(onSignup: () -> Unit, onLogin: () -> Unit) = Page {
    Spacer(Modifier.height(40.dp))
    StatusIcon("✓", TealSoft, Teal, 92)
    Spacer(Modifier.height(28.dp))
    Text("부모님의 전화를", fontSize = 28.sp, fontWeight = FontWeight.ExtraBold, color = Ink)
    Text("보이스피싱으로부터", fontSize = 31.sp, fontWeight = FontWeight.ExtraBold, color = Teal)
    Text("지켜드립니다", fontSize = 28.sp, fontWeight = FontWeight.ExtraBold, color = Ink)
    Spacer(Modifier.height(18.dp))
    Body("가족의 전화번호와 목소리를 기억하고,\n의심되는 통화는 가족에게 한 번 더 확인합니다.", centered = true)
    Spacer(Modifier.weight(1f))
    PrimaryButton("통화 보호 시작하기", onSignup)
    TextButtonLine("이미 가입했어요", onLogin)
}

@Composable
private fun SignupScreen(name: String, onName: (String) -> Unit, email: String, onEmail: (String) -> Unit, password: String, onPassword: (String) -> Unit, onNext: () -> Unit) = FormPage("1 / 3", "가족의 안심을 시작해요", "통화 보호와 가족 확인에 사용할 정보를 입력해 주세요.") {
    var confirmation by remember { mutableStateOf("") }
    Input("이름", "이름을 입력해 주세요", name, onName)
    Input("이메일", "example@email.com", email, onEmail)
    Input("비밀번호", "8자 이상 입력", password, onPassword, password = true)
    Input("비밀번호 확인", "한 번 더 입력", confirmation, { confirmation = it }, password = true)
    PrimaryButton("다음", onNext, name.isNotBlank() && email.isNotBlank() && password.length >= 8 && password == confirmation)
    Caption("🔒 개인정보는 암호화하여 안전하게 보관합니다.")
}

@Composable
private fun ConsentScreen(onNext: () -> Unit) {
    var required by remember { mutableStateOf(listOf(true, true, true, true)) }
    var face by remember { mutableStateOf(false) }
    FormPage("2 / 3", "서비스 이용에 동의해 주세요", "얼굴정보는 선택사항이며 동의하지 않아도 이용할 수 있습니다.") {
        val labels = listOf("서비스 이용약관", "개인정보 수집·이용", "가족 전화번호 및 음성 특징정보", "통화 위험분석 및 가족 알림")
        labels.forEachIndexed { index, label ->
            CheckRow("필수", label, required[index]) { required = required.mapIndexed { i, v -> if (i == index) !v else v } }
        }
        CheckRow("선택", "얼굴정보 처리", face) { face = !face }
        PrimaryButton("동의하고 계속하기", onNext, required.all { it })
    }
}

@Composable
private fun LoginScreen(email: String, onEmail: (String) -> Unit, password: String, onPassword: (String) -> Unit, onLogin: () -> Unit) = FormPage(null, "다시 만나서 반가워요", "등록한 계정으로 로그인해 주세요.") {
    Input("이메일", "example@email.com", email, onEmail)
    Input("비밀번호", "비밀번호", password, onPassword, password = true)
    PrimaryButton("로그인", onLogin, email.isNotBlank() && password.isNotBlank())
    TextButtonLine("비밀번호를 잊으셨나요?", {})
}

@Composable
private fun ProtectedFamilyScreen(onNext: (String, String, String) -> Unit) {
    var selected by remember { mutableStateOf("어머니") }
    var name by remember { mutableStateOf("") }; var phone by remember { mutableStateOf("") }
    FormPage("1 / 3", "보이스피싱으로부터 누구의 전화를 보호할까요?", "부모님 또는 조부모님의 휴대전화에 의심전화 경고와 차단을 제공합니다.") {
        ChoiceGrid(listOf("아버지", "어머니", "할아버지", "할머니", "기타"), selected) { selected = it }
        Input("성함", "예: 김영희", name, { name = it })
        Input("휴대전화 번호", "010-0000-0000", phone, { phone = it })
        InfoCard("통화 보호 시작 안내", "등록한 가족의 휴대전화에서 로그인하면 보호가 자동으로 시작됩니다.")
        PrimaryButton("다음: 확인 가족 등록", { onNext(name, phone, selected) }, name.isNotBlank() && phone.length >= 4)
    }
}

@Composable
private fun ConfirmationContactScreen(onNext: (String, String, String, Boolean) -> Unit) {
    var selected by remember { mutableStateOf("딸") }
    var first by remember { mutableStateOf(true) }
    var name by remember { mutableStateOf("") }; var phone by remember { mutableStateOf("") }
    FormPage("2 / 3", "의심전화를 확인해 줄 가족", "보호받을 가족에게 의심전화가 오면 실제 통화 여부를 확인합니다.") {
        ChoiceGrid(listOf("아들", "딸", "손자", "손녀", "배우자", "기타"), selected) { selected = it }
        Input("성함", "예: 김민지", name, { name = it })
        Input("휴대전화 번호", "010-0000-0000", phone, { phone = it })
        ToggleCard("가장 먼저 확인할 가족", "의심전화 발생 시 첫 번째로 알림", first) { first = it }
        OutlinedFullButton("＋ 확인 가족 한 명 더 추가", {})
        PrimaryButton("다음: 가족 음성 등록", { onNext(name, phone, selected, first) }, name.isNotBlank() && phone.length >= 4)
    }
}

@Composable
private fun BiometricsScreen(onDone: () -> Unit) = FormPage("3 / 3", "가족의 목소리를 등록해 주세요", "등록 가족의 목소리와 의심전화 목소리를 비교합니다.") {
    PersonCard("김민지", "딸 · 음성 등록 필요")
    CardBox {
        StatusIcon("●", TealSoft, Teal, 68)
        Title("안내 문장을 읽어 주세요", 18)
        Body("“엄마, 오늘 저녁에 다시 전화드릴게요.”", centered = true)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
            repeat(22) { i -> Box(Modifier.padding(horizontal = 2.dp).width(3.dp).height((10 + i * 7 % 30).dp).background(Teal, CircleShape)) }
        }
        PrimaryButton("🎙 녹음 시작", {})
    }
    OutlinedFullButton("▣ 얼굴정보 등록하기 · 선택", {})
    PrimaryButton("등록 완료", onDone)
}

@Composable
private fun HomeScreen(navigate: (AppScreen) -> Unit) = Page {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { Caption("안녕하세요, 김민지님"); Title("통화 보호 홈", 27) }
        CircleBadge("🔔", Color.White, Ink, 44)
    }
    CardBox(background = Teal) {
        Pill("●  통화 보호 켜짐", Color.White.copy(alpha = .14f), Color.White)
        Text("김영희 어머니의 전화를", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Text("보이스피싱으로부터\n보호하고 있습니다.", color = Color(0xFF8FF1CD), fontSize = 25.sp, fontWeight = FontWeight.ExtraBold)
        Caption("마지막 확인 오늘 오전 9:41 · 모든 기능 정상", Color(0xFFC7E6DE))
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        MiniStat("12", "확인 전화", TealSoft, Modifier.weight(1f))
        MiniStat("3", "의심 감지", OrangeSoft, Modifier.weight(1f))
        MiniStat("1", "고위험 차단", RedSoft, Modifier.weight(1f))
    }
    SectionTitle("통화 보호 준비", "모든 준비가 완료됐어요")
    ReadyRow("✓", "가족 연락처", "3개 번호 등록 완료")
    ReadyRow("♪", "가족 음성", "품질 좋음")
    ReadyRow("♧", "확인 가족", "김민지 외 1명")
    SectionTitle("최근 통화", "통화 보호 기록")
    CallRecord("안전", "등록된 가족 전화", "김민지 · 오늘 09:41", TealSoft) { navigate(AppScreen.NORMAL) }
    CallRecord("주의", "가족 사칭 의심전화", "번호 끝 8821 · 어제", OrangeSoft) { navigate(AppScreen.ANALYSIS) }
    CallRecord("차단", "고위험 전화 차단", "번호 끝 4402 · 7월 12일", RedSoft) { navigate(AppScreen.BLOCKED) }
}

@Composable
private fun NormalCallScreen(onContinue: () -> Unit) = CallPage("✓", TealSoft, Teal, "등록된 가족 전화", "김민지 딸의 전화입니다", "등록된 전화번호와 가족 정보가 일치합니다.") {
    PersonCard("김민지", "딸 · 010-••••-4421")
    PrimaryButton("☎ 통화 계속하기", onContinue)
}

@Composable
private fun AnalysisScreen(onBlock: () -> Unit, onConfirm: () -> Unit) = CallPage("!", OrangeSoft, Orange, "통화 중 실시간 확인", "가족 사칭이 의심됩니다", "돈을 보내거나 앱을 설치하지 마세요.") {
    AnalysisRow("✓", "전화번호 확인", "등록되지 않은 번호", true)
    AnalysisRow("✓", "가족 음성 비교", "가족 목소리와 유사", true)
    AnalysisRow("●", "AI 합성음 분석", "합성음 가능성 감지", true)
    AnalysisRow("◷", "통화내용 분석", "확인 중", false)
    OutlinedFullButton("확인 가족에게 요청", onConfirm)
    DangerButton("☎ 지금 통화 끊기", onBlock)
}

@Composable
private fun BlockedScreen(onConfirm: () -> Unit, onHome: () -> Unit) = CallPage("×", RedSoft, Red, "고위험 전화 차단", "보이스피싱 위험이 높아 전화를 차단했습니다", "가족 목소리처럼 들려도 저장된 번호로 다시 확인하세요.") {
    CardBox(background = Color(0xFFFFF4F2)) { Caption("차단한 이유", Red); Body("× 등록되지 않은 전화번호\n× AI 합성음 가능성 높음\n× 송금 요구 표현 감지") }
    PrimaryButton("☎ 저장된 가족에게 다시 전화", onHome)
    OutlinedFullButton("♧ 확인 가족에게 요청", onConfirm)
}

@Composable
private fun ConfirmationRequestScreen(onDone: () -> Unit) = CallPage("?", Color(0xFFE9EFFC), Color(0xFF4C70BA), "가족 확인 요청", "지금 김영희 어머니께 전화하셨나요?", "응답은 의심전화 위험도에 바로 반영됩니다.") {
    AnswerButton("✓", "네, 제가 전화했어요", "정상 가족 통화입니다", Teal, onDone)
    AnswerButton("×", "아니요, 제가 아닙니다", "즉시 위험도를 높이고 차단합니다", Red, onDone)
    AnswerButton("!", "잘 모르겠습니다", "추가 확인을 진행합니다", Orange, onDone)
}

@Composable
private fun HistoryScreen() = Page {
    Title("통화기록", 27); Body("민감한 통화내용은 기본적으로 숨겨집니다.")
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { Pill("전체 16", Teal, Color.White); Pill("안전 12", Color.White, Muted); Pill("주의 2", Color.White, Muted) }
    CallRecord("안전", "김민지 · 딸", "등록 가족 번호 · 오늘 09:41", TealSoft) {}
    CallRecord("주의", "번호 끝 8821", "미등록 번호 · 전화했음", OrangeSoft) {}
    CallRecord("차단", "번호 끝 4402", "합성음·송금 요구 · 7월 12일", RedSoft) {}
}

@Composable
private fun SettingsScreen() = Page {
    Title("설정", 27)
    PersonCard("김영희 어머니", "보이스피싱 통화 보호 켜짐")
    ToggleCard("의심전화 경고", "주의 이상 전화에 경고 표시", true) {}
    ToggleCard("확인 가족 알림", "위험 통화 시 가족에게 알림", true) {}
    ToggleCard("큰 글씨", "통화 경고를 더 크게 표시", true) {}
    SectionTitle("개인정보", "등록정보 관리")
    OutlinedFullButton("음성·얼굴 정보 관리", {})
    OutlinedFullButton("동의 내역 및 데이터 삭제", {})
}

@Composable
private fun Page(content: @Composable ColumnScope.() -> Unit) = Column(
    modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
    verticalArrangement = Arrangement.spacedBy(15.dp),
    content = content,
)

@Composable
private fun FormPage(step: String?, title: String, description: String, content: @Composable ColumnScope.() -> Unit) = Page {
    step?.let { Pill(it, TealSoft, Teal) }; Title(title, 27); Body(description); Spacer(Modifier.height(2.dp)); content()
}

@Composable
private fun CallPage(symbol: String, bg: Color, fg: Color, eyebrow: String, title: String, description: String, content: @Composable ColumnScope.() -> Unit) = Page {
    Spacer(Modifier.height(20.dp)); StatusIcon(symbol, bg, fg, 96); Text(eyebrow, color = fg, fontWeight = FontWeight.Bold, modifier = Modifier.align(Alignment.CenterHorizontally)); Text(title, fontSize = 28.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.Center, lineHeight = 38.sp, modifier = Modifier.fillMaxWidth()); Body(description, centered = true); Spacer(Modifier.height(8.dp)); content()
}

@Composable private fun Title(text: String, size: Int) = Text(text, fontSize = size.sp, fontWeight = FontWeight.ExtraBold, color = Ink, lineHeight = (size + 9).sp)
@Composable private fun Body(text: String, centered: Boolean = false) = Text(text, color = Muted, fontSize = 16.sp, lineHeight = 25.sp, textAlign = if (centered) TextAlign.Center else TextAlign.Start, modifier = if (centered) Modifier.fillMaxWidth() else Modifier)
@Composable private fun Caption(text: String, color: Color = Muted) = Text(text, color = color, fontSize = 12.sp, lineHeight = 18.sp)

@Composable
private fun Input(label: String, placeholder: String, value: String = "", onValueChange: (String) -> Unit = {}, password: Boolean = false) { Column(verticalArrangement = Arrangement.spacedBy(6.dp)) { Text(label, fontWeight = FontWeight.Bold, fontSize = 13.sp); OutlinedTextField(value, onValueChange, placeholder = { Text(placeholder) }, visualTransformation = if (password) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None, modifier = Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(12.dp)) } }

@Composable
private fun PrimaryButton(text: String, onClick: () -> Unit, enabled: Boolean = true) = Button(onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().height(54.dp), shape = RoundedCornerShape(14.dp), colors = ButtonDefaults.buttonColors(containerColor = Teal)) { Text(text, fontWeight = FontWeight.Bold, fontSize = 16.sp) }
@Composable private fun DangerButton(text: String, onClick: () -> Unit) = Button(onClick, modifier = Modifier.fillMaxWidth().height(54.dp), colors = ButtonDefaults.buttonColors(containerColor = Red), shape = RoundedCornerShape(14.dp)) { Text(text, fontWeight = FontWeight.Bold) }
@Composable private fun OutlinedFullButton(text: String, onClick: () -> Unit) = OutlinedButton(onClick, modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(14.dp)) { Text(text, fontWeight = FontWeight.Bold) }
@Composable private fun TextButtonLine(text: String, onClick: () -> Unit) = Text(text, color = Teal, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(12.dp))

@Composable private fun StatusIcon(text: String, bg: Color, fg: Color, size: Int) = Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) { Box(Modifier.size(size.dp).background(bg, CircleShape), contentAlignment = Alignment.Center) { Text(text, color = fg, fontSize = (size / 2).sp, fontWeight = FontWeight.Bold) } }
@Composable private fun CircleBadge(text: String, bg: Color, fg: Color, size: Int) = Box(Modifier.size(size.dp).background(bg, CircleShape), contentAlignment = Alignment.Center) { Text(text, color = fg) }
@Composable private fun Pill(text: String, bg: Color, fg: Color) = Text(text, color = fg, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.background(bg, RoundedCornerShape(50)).border(1.dp, fg.copy(alpha = .12f), RoundedCornerShape(50)).padding(horizontal = 12.dp, vertical = 7.dp))

@Composable
private fun ChoiceGrid(options: List<String>, selected: String, onSelect: (String) -> Unit) = Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { options.chunked(2).forEach { row -> Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) { row.forEach { option -> Box(Modifier.weight(1f).height(48.dp).background(if (selected == option) TealSoft else Color.White, RoundedCornerShape(12.dp)).border(if (selected == option) 2.dp else 1.dp, if (selected == option) Teal else Color(0xFFD8E3DF), RoundedCornerShape(12.dp)).clickable { onSelect(option) }, contentAlignment = Alignment.Center) { Text(option, color = if (selected == option) Teal else Muted, fontWeight = if (selected == option) FontWeight.Bold else FontWeight.Normal) } }; if (row.size == 1) Spacer(Modifier.weight(1f)) } } }

@Composable private fun CardBox(background: Color = Color.White, content: @Composable ColumnScope.() -> Unit) = Column(Modifier.fillMaxWidth().background(background, RoundedCornerShape(18.dp)).border(1.dp, Color(0xFFE0E9E6), RoundedCornerShape(18.dp)).padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
@Composable private fun InfoCard(title: String, text: String) = CardBox(TealSoft) { Text("⌾  $title", color = Teal, fontWeight = FontWeight.Bold); Caption(text, Color(0xFF4E7069)) }
@Composable private fun PersonCard(name: String, meta: String) = Row(Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(15.dp)).border(1.dp, Color(0xFFDCE6E2), RoundedCornerShape(15.dp)).padding(14.dp), verticalAlignment = Alignment.CenterVertically) { CircleBadge(name.take(1), TealSoft, Teal, 45); Spacer(Modifier.width(12.dp)); Column(Modifier.weight(1f)) { Text(name, fontWeight = FontWeight.Bold); Caption(meta) }; Text("›", color = Muted, fontSize = 24.sp) }
@Composable private fun ToggleCard(title: String, text: String, checked: Boolean, onChange: (Boolean) -> Unit) = Row(Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(14.dp)).padding(14.dp), verticalAlignment = Alignment.CenterVertically) { Column(Modifier.weight(1f)) { Text(title, fontWeight = FontWeight.Bold); Caption(text) }; Switch(checked, onChange) }
@Composable private fun CheckRow(type: String, label: String, checked: Boolean, onClick: () -> Unit) = Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) { Checkbox(checked, { onClick() }); Text("[$type]", color = if (type == "필수") Teal else Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold); Spacer(Modifier.width(6.dp)); Text(label, color = Ink) }
@Composable private fun MiniStat(value: String, label: String, bg: Color, modifier: Modifier) = Column(modifier.background(bg, RoundedCornerShape(14.dp)).padding(13.dp)) { Text(value, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp); Caption(label) }
@Composable private fun SectionTitle(eyebrow: String, title: String) = Column { Text(eyebrow, color = Teal, fontSize = 12.sp, fontWeight = FontWeight.Bold); Text(title, color = Ink, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold) }
@Composable private fun ReadyRow(symbol: String, title: String, meta: String) = Row(Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(14.dp)).padding(14.dp), verticalAlignment = Alignment.CenterVertically) { CircleBadge(symbol, TealSoft, Teal, 40); Spacer(Modifier.width(12.dp)); Column(Modifier.weight(1f)) { Text(title, fontWeight = FontWeight.Bold); Caption(meta) }; Text("✓", color = Teal, fontWeight = FontWeight.Bold) }
@Composable private fun CallRecord(status: String, title: String, meta: String, bg: Color, onClick: () -> Unit) = Row(Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(14.dp)).clickable(onClick = onClick).padding(14.dp), verticalAlignment = Alignment.CenterVertically) { Pill(status, bg, if (bg == RedSoft) Red else if (bg == OrangeSoft) Orange else Teal); Spacer(Modifier.width(12.dp)); Column(Modifier.weight(1f)) { Text(title, fontWeight = FontWeight.Bold); Caption(meta) }; Text("›", color = Muted, fontSize = 24.sp) }
@Composable private fun AnalysisRow(symbol: String, title: String, detail: String, active: Boolean) = Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) { CircleBadge(symbol, if (active) OrangeSoft else Color(0xFFF0F3F2), if (active) Orange else Muted, 38); Spacer(Modifier.width(12.dp)); Column { Text(title, fontWeight = FontWeight.Bold, color = if (active) Ink else Muted); Caption(detail) } }
@Composable private fun AnswerButton(symbol: String, title: String, detail: String, color: Color, onClick: () -> Unit) = Row(Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(14.dp)).border(1.dp, color.copy(alpha = .25f), RoundedCornerShape(14.dp)).clickable(onClick = onClick).padding(16.dp), verticalAlignment = Alignment.CenterVertically) { CircleBadge(symbol, color.copy(alpha = .1f), color, 42); Spacer(Modifier.width(12.dp)); Column { Text(title, color = color, fontWeight = FontWeight.Bold); Caption(detail) } }
@Composable private fun RowScope.Nav(label: String, symbol: String, selected: Boolean, onClick: () -> Unit) = NavigationBarItem(selected, onClick, icon = { Text(symbol, fontSize = 20.sp) }, label = { Text(label) })
