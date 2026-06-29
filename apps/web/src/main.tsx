import React, { FormEvent, useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  BellRing,
  Check,
  ChevronLeft,
  ChevronRight,
  Database,
  History,
  Home,
  Info,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  Mic,
  Phone,
  PhoneCall,
  Shield,
  UserPlus,
  Users,
  Video,
} from "lucide-react";
import {
  ApiHealth,
  CallEvaluation,
  EmergencyNotification,
  FaceProfile,
  Family,
  FamilyMember,
  RiskEvent,
  SafeWord,
  Senior,
  UserPublic,
  VideoVerification,
  VoiceProfile,
  apiGet,
  apiPost,
  getResolvedApiBaseUrl,
} from "./api";
import "./styles.css";

type Workspace = {
  token: string | null;
  account: UserPublic | null;
  role: "SENIOR" | "GUARDIAN" | null;
  family: Family | null;
  senior: Senior | null;
  safeWord: SafeWord | null;
  members: FamilyMember[];
  faceProfiles: FaceProfile[];
  voiceProfiles: VoiceProfile[];
  riskEvents: RiskEvent[];
  notifications: EmergencyNotification[];
  videoVerifications: VideoVerification[];
};

type Screen =
  | "welcome"
  | "signup"
  | "consent"
  | "login"
  | "role"
  | "connect"
  | "home"
  | "family"
  | "guard"
  | "verify"
  | "history"
  | "settings";

type AuthResponse = {
  access_token: string;
  user: UserPublic;
};

const storageKey = "soricall.mobile.workspace.v2";
const appScreens: Screen[] = ["home", "family", "guard", "verify", "history", "settings"];

const emptyWorkspace: Workspace = {
  token: null,
  account: null,
  role: null,
  family: null,
  senior: null,
  safeWord: null,
  members: [],
  faceProfiles: [],
  voiceProfiles: [],
  riskEvents: [],
  notifications: [],
  videoVerifications: [],
};

const bottomTabs: { key: Screen; label: string; icon: React.ElementType }[] = [
  { key: "home", label: "홈", icon: Home },
  { key: "family", label: "가족", icon: Users },
  { key: "guard", label: "경고", icon: Shield },
  { key: "verify", label: "확인", icon: Video },
  { key: "history", label: "기록", icon: History },
];

function App() {
  const [workspace, setWorkspace] = useState<Workspace>(() => loadWorkspace());
  const [screen, setScreen] = useState<Screen>("welcome");
  const [historyStack, setHistoryStack] = useState<Screen[]>([]);
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [apiBase, setApiBase] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("준비됨");
  const [error, setError] = useState<string | null>(null);
  const [signup, setSignup] = useState({
    email: "",
    password: "",
    passwordConfirm: "",
    displayName: "",
    phoneNumber: "",
  });
  const [consent, setConsent] = useState({
    requiredData: false,
    privacy: false,
    nonMedical: false,
    syntheticVoice: false,
    aiResearch: false,
    marketing: false,
  });
  const [login, setLogin] = useState({ email: "", password: "" });
  const [connect, setConnect] = useState({
    familyName: "김영희 가족",
    seniorName: "김영희 어르신",
    seniorPhone: "+821099998888",
    relation: "딸",
  });
  const [safeWord, setSafeWord] = useState("도와줘");
  const [safeWordMatched, setSafeWordMatched] = useState<boolean | null>(null);
  const [phoneNumber, setPhoneNumber] = useState("+821077770000");
  const [callEvaluation, setCallEvaluation] = useState<CallEvaluation | null>(null);
  const [memberDraft, setMemberDraft] = useState({
    name: "박서연",
    relation: "며느리",
    phone_number: "+821055556666",
  });
  const [settings, setSettings] = useState({
    unknownNumber: true,
    guardianAlert: true,
    voiceWarning: true,
  });

  const hasAccount = Boolean(workspace.account);
  const hasWorkspace = Boolean(workspace.account && workspace.family && workspace.senior);
  const latestRisk = workspace.riskEvents[0] ?? null;
  const latestNotification = workspace.notifications[0] ?? null;
  const latestVideo = workspace.videoVerifications[0] ?? null;
  const primaryMember = workspace.members[0] ?? null;
  const memberIds = useMemo(() => new Set(workspace.members.map((member) => member.id)), [workspace.members]);
  const faces = workspace.faceProfiles.filter((profile) => memberIds.has(profile.family_member_id));
  const voices = workspace.voiceProfiles.filter((profile) => memberIds.has(profile.family_member_id));

  useEffect(() => {
    void checkHealth();
  }, []);

  useEffect(() => {
    persistWorkspace(workspace);
  }, [workspace]);

  useEffect(() => {
    if ("serviceWorker" in navigator && import.meta.env.PROD) {
      navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
    }
  }, []);

  function navigate(next: Screen) {
    if (next === screen) return;
    setHistoryStack((current) => [...current, screen]);
    setScreen(next);
    setError(null);
  }

  function goBack() {
    setHistoryStack((current) => {
      const next = [...current];
      const previous = next.pop();
      setScreen(previous ?? "welcome");
      setError(null);
      return next;
    });
  }

  function goHome() {
    setHistoryStack([]);
    setScreen("welcome");
    setError(null);
  }

  async function run<T>(label: string, task: () => Promise<T>): Promise<T | null> {
    setBusy(true);
    setStatus(label);
    setError(null);
    try {
      const result = await task();
      setApiBase(getResolvedApiBaseUrl());
      setStatus("완료");
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청을 처리하지 못했습니다.");
      setStatus("오류");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function checkHealth() {
    await run("API 연결 확인 중", async () => {
      const result = await apiGet<ApiHealth>("/health");
      setHealth(result);
      return result;
    });
  }

  function validateSignupDraft() {
    if (!signup.email.trim() || !signup.password || !signup.displayName.trim()) {
      setError("이름, 이메일, 비밀번호를 입력해 주세요.");
      return false;
    }
    if (signup.password.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다.");
      return false;
    }
    if (signup.password !== signup.passwordConfirm) {
      setError("비밀번호 확인이 일치하지 않습니다.");
      return false;
    }
    return true;
  }

  function continueToConsent(event: FormEvent) {
    event.preventDefault();
    if (!validateSignupDraft()) return;
    navigate("consent");
  }

  async function submitSignup() {
    const requiredAccepted = consent.requiredData && consent.privacy && consent.nonMedical && consent.syntheticVoice;
    if (!requiredAccepted) {
      setError("필수 동의 항목을 모두 확인해 주세요.");
      return;
    }

    await run("회원가입 중", async () => {
      const response = await apiPost<AuthResponse>("/api/v1/auth/register", {
        email: signup.email.trim(),
        password: signup.password,
        display_name: signup.displayName.trim(),
        role: "GUARDIAN",
        phone_number: signup.phoneNumber || null,
      });
      setWorkspace({ ...emptyWorkspace, token: response.access_token, account: response.user, role: "GUARDIAN" });
      setLogin({ email: response.user.email ?? signup.email.trim(), password: "" });
      navigate("login");
      return response;
    });
  }

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    if (!login.email.trim() || !login.password) {
      setError("이메일과 비밀번호를 입력해 주세요.");
      return;
    }

    await run("로그인 중", async () => {
      const response = await apiPost<AuthResponse>("/api/v1/auth/login", {
        email: login.email.trim(),
        password: login.password,
      });
      setWorkspace((current) => ({
        ...current,
        token: response.access_token,
        account: response.user,
        role: response.user.role === "SENIOR" ? "SENIOR" : "GUARDIAN",
      }));
      navigate(workspace.family ? "home" : "role");
      return response;
    });
  }

  function chooseRole(role: "SENIOR" | "GUARDIAN") {
    setWorkspace((current) => ({ ...current, role }));
    navigate("connect");
  }

  async function submitConnect(event: FormEvent) {
    event.preventDefault();
    if (!workspace.account || !workspace.role) {
      setError("회원가입 또는 로그인을 먼저 진행해 주세요.");
      return;
    }

    await run("가족 연결 중", async () => {
      const family = await apiPost<Family>("/api/v1/families", {
        name: connect.familyName,
        created_by: workspace.account!.id,
      });
      const senior = await apiPost<Senior>("/api/v1/seniors", {
        family_id: family.id,
        name: connect.seniorName,
        phone_number: connect.seniorPhone,
        birth_year: 1948,
        user_id: workspace.role === "SENIOR" ? workspace.account!.id : null,
      });
      if (workspace.role === "GUARDIAN") {
        await apiPost(`/api/v1/seniors/${senior.id}/guardians`, {
          user_id: workspace.account!.id,
          relation: connect.relation,
          priority: 1,
          notify_enabled: true,
        });
      }

      const safe = await apiPost<SafeWord>(`/api/v1/families/${family.id}/safe-word`, {
        word: safeWord,
        hint: "가족 확인용 단어",
        updated_by: workspace.account!.id,
      });
      await apiPost("/api/v1/admin/risk-numbers", {
        phone_number: "+821077770000",
        label: "데모 사칭 의심 번호",
        risk_score: 92,
      });

      const seedMembers = await Promise.all(
        [
          { name: "김민준", relation: "아들", phone_number: "+821011112222" },
          { name: "이지은", relation: "딸", phone_number: "+821033334444" },
        ].map((member) => apiPost<FamilyMember>(`/api/v1/families/${family.id}/members`, member)),
      );

      await Promise.all(
        seedMembers.map((member, index) =>
          apiPost<FaceProfile>("/api/v1/face-profiles", {
            family_member_id: member.id,
            display_name: member.name,
            image_ref: `family-face-${index + 1}.jpg`,
            consent_accepted: true,
          }),
        ),
      );

      const audioRef = `family-voice-${Date.now()}.wav`;
      const voice = await apiPost<VoiceProfile>("/api/v1/voice-profiles", {
        family_member_id: seedMembers[0].id,
        display_name: `${seedMembers[0].name} 목소리`,
        consent_id: "service-consent",
      });
      await apiPost(`/api/v1/voice-profiles/${voice.id}/samples`, {
        audio_ref: audioRef,
        duration_ms: 4200,
        sample_rate: 16000,
        mime_type: "audio/wav",
        purpose: "ENROLLMENT",
      });
      await apiPost(`/api/v1/voice-profiles/${voice.id}/enroll`, { audio_ref: audioRef });

      const next = await fetchWorkspace({
        ...workspace,
        family,
        senior,
        safeWord: safe,
      });
      setWorkspace(next);
      setHistoryStack((current) => [...current, "connect"]);
      setScreen("home");
      return next;
    });
  }

  async function refreshWorkspace(source = workspace) {
    if (!source.family || !source.senior) return;
    await run("최신 데이터 불러오는 중", async () => {
      const next = await fetchWorkspace(source);
      setWorkspace(next);
      return next;
    });
  }

  async function fetchWorkspace(source: Workspace): Promise<Workspace> {
    if (!source.family || !source.senior) return source;
    const [members, allFaces, allVoices, risks, notifications, videos] = await Promise.all([
      apiGet<FamilyMember[]>(`/api/v1/families/${source.family.id}/members`),
      apiGet<FaceProfile[]>("/api/v1/face-profiles"),
      apiGet<VoiceProfile[]>("/api/v1/voice-profiles"),
      apiGet<RiskEvent[]>(`/api/v1/risk-events?senior_id=${source.senior.id}`),
      apiGet<EmergencyNotification[]>("/api/v1/emergency/notifications"),
      apiGet<VideoVerification[]>(`/api/v1/video-verifications?senior_id=${source.senior.id}`),
    ]);
    const ids = new Set(members.map((member) => member.id));
    return {
      ...source,
      members,
      faceProfiles: allFaces.filter((face) => ids.has(face.family_member_id)),
      voiceProfiles: allVoices.filter((voice) => ids.has(voice.family_member_id)),
      riskEvents: [...risks].reverse(),
      notifications: [...notifications].reverse(),
      videoVerifications: [...videos].reverse(),
    };
  }

  async function addFamilyMember(event: FormEvent) {
    event.preventDefault();
    if (!workspace.family) return;
    await run("가족 등록 중", async () => {
      const member = await apiPost<FamilyMember>(`/api/v1/families/${workspace.family!.id}/members`, memberDraft);
      await apiPost<FaceProfile>("/api/v1/face-profiles", {
        family_member_id: member.id,
        display_name: member.name,
        image_ref: `${member.name}-face.jpg`,
        consent_accepted: true,
      });
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      return member;
    });
  }

  async function saveSafeWord() {
    if (!workspace.family || !workspace.account) return;
    await run("안심 단어 저장 중", async () => {
      const saved = await apiPost<SafeWord>(`/api/v1/families/${workspace.family!.id}/safe-word`, {
        word: safeWord,
        hint: "가족 확인용 단어",
        updated_by: workspace.account!.id,
      });
      setWorkspace((current) => ({ ...current, safeWord: saved }));
      setSafeWordMatched(null);
      return saved;
    });
  }

  async function verifySafeWord() {
    if (!workspace.family) return;
    await run("안심 단어 확인 중", async () => {
      const result = await apiPost<{ matched: boolean }>(`/api/v1/families/${workspace.family!.id}/safe-word/verify`, {
        word: safeWord,
      });
      setSafeWordMatched(result.matched);
      return result;
    });
  }

  async function evaluateCall() {
    if (!workspace.senior) return;
    await run("위험도 평가 중", async () => {
      const evaluation = await apiPost<CallEvaluation>("/api/v1/calls/evaluate", {
        senior_id: workspace.senior!.id,
        phone_number: phoneNumber,
        direction: "INCOMING",
      });
      setCallEvaluation(evaluation);
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      navigate("guard");
      return evaluation;
    });
  }

  async function notifyGuardian() {
    const risk = workspace.riskEvents[0];
    if (!risk) return;
    await run("보호자 알림 전송 중", async () => {
      const result = await apiPost("/api/v1/emergency/notify", {
        risk_event_id: risk.id,
        message: "가족 사칭 의심 전화가 감지되었습니다. 지금 확인해 주세요.",
      });
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      return result;
    });
  }

  async function respondToNotification(response: "REAL_CALL" | "NOT_ME" | "UNKNOWN") {
    const notification = workspace.notifications[0];
    if (!notification) return;
    await run("보호자 응답 저장 중", async () => {
      const result = await apiPost("/api/v1/emergency/respond", {
        notification_id: notification.id,
        response,
      });
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      return result;
    });
  }

  async function requestVideoVerification() {
    if (!workspace.senior || !primaryMember) return;
    await run("화상 확인 요청 중", async () => {
      const result = await apiPost<VideoVerification>("/api/v1/video-verifications", {
        senior_id: workspace.senior!.id,
        family_member_id: primaryMember.id,
        risk_event_id: workspace.riskEvents[0]?.id ?? null,
      });
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      navigate("verify");
      return result;
    });
  }

  async function acceptVideoVerification() {
    const video = workspace.videoVerifications[0];
    if (!video) return;
    await run("얼굴 비교 저장 중", async () => {
      const result = await apiPost<VideoVerification>(`/api/v1/video-verifications/${video.id}/accept`, {
        match_score: 91,
      });
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      return result;
    });
  }

  async function enrollVoiceProfile() {
    if (!primaryMember) return;
    await run("음성 프로필 등록 중", async () => {
      const audioRef = `voice-${Date.now()}.wav`;
      const profile = await apiPost<VoiceProfile>("/api/v1/voice-profiles", {
        family_member_id: primaryMember.id,
        display_name: `${primaryMember.name} 목소리`,
        consent_id: "manual-consent",
      });
      await apiPost(`/api/v1/voice-profiles/${profile.id}/samples`, {
        audio_ref: audioRef,
        duration_ms: 3900,
        sample_rate: 16000,
        mime_type: "audio/wav",
        purpose: "ENROLLMENT",
      });
      await apiPost(`/api/v1/voice-profiles/${profile.id}/enroll`, { audio_ref: audioRef });
      const next = await fetchWorkspace(workspace);
      setWorkspace(next);
      return profile;
    });
  }

  function resetLocalWorkspace() {
    localStorage.removeItem(storageKey);
    setWorkspace(emptyWorkspace);
    setCallEvaluation(null);
    setSafeWordMatched(null);
    setHistoryStack([]);
    setScreen("welcome");
  }

  return (
    <main className="mobile-app">
      <header className="app-status">
        <span>9:41</span>
        <span className="network">LTE</span>
      </header>

      <section className="app-frame">
        {screen !== "welcome" && (
          <AppHeader
            title={titleFor(screen)}
            busy={busy}
            status={status}
            error={error}
            health={health}
            onBack={goBack}
            onHome={goHome}
          />
        )}

        <section className="screen">
          {screen === "welcome" && (
            <WelcomeScreen
              busy={busy}
              error={error}
              apiBase={apiBase}
              onSignup={() => navigate("signup")}
              onLogin={() => navigate("login")}
            />
          )}
          {screen === "signup" && (
            <SignupScreen
              draft={signup}
              setDraft={setSignup}
              error={error}
              busy={busy}
              onSubmit={continueToConsent}
              onLogin={() => navigate("login")}
            />
          )}
          {screen === "consent" && (
            <ConsentScreen
              consent={consent}
              setConsent={setConsent}
              error={error}
              busy={busy}
              onSubmit={() => void submitSignup()}
            />
          )}
          {screen === "login" && <LoginScreen draft={login} setDraft={setLogin} error={error} busy={busy} onSubmit={submitLogin} />}
          {screen === "role" && <RoleScreen role={workspace.role} onChoose={chooseRole} />}
          {screen === "connect" && (
            <ConnectScreen draft={connect} setDraft={setConnect} busy={busy} role={workspace.role} onSubmit={submitConnect} />
          )}
          {screen === "home" && hasWorkspace && (
            <HomeScreen
              workspace={workspace}
              faces={faces}
              voices={voices}
              latestRisk={latestRisk}
              callEvaluation={callEvaluation}
              onEvaluate={() => void evaluateCall()}
              onVideo={() => void requestVideoVerification()}
              onNavigate={navigate}
            />
          )}
          {screen === "family" && (
            <FamilyScreen
              workspace={workspace}
              faces={faces}
              voices={voices}
              memberDraft={memberDraft}
              setMemberDraft={setMemberDraft}
              onAdd={(event) => void addFamilyMember(event)}
              onVoice={() => void enrollVoiceProfile()}
            />
          )}
          {screen === "guard" && (
            <GuardScreen
              phoneNumber={phoneNumber}
              setPhoneNumber={setPhoneNumber}
              evaluation={callEvaluation}
              latestRisk={latestRisk}
              onEvaluate={() => void evaluateCall()}
              onNotify={() => void notifyGuardian()}
            />
          )}
          {screen === "verify" && (
            <VerifyScreen
              primaryMember={primaryMember}
              latestNotification={latestNotification}
              latestVideo={latestVideo}
              onRequest={() => void requestVideoVerification()}
              onAccept={() => void acceptVideoVerification()}
              onRespond={(response) => void respondToNotification(response)}
            />
          )}
          {screen === "history" && <HistoryScreen workspace={workspace} />}
          {screen === "settings" && (
            <SettingsScreen
              settings={settings}
              setSettings={setSettings}
              safeWord={safeWord}
              setSafeWord={setSafeWord}
              matched={safeWordMatched}
              apiBase={apiBase || getResolvedApiBaseUrl()}
              onSave={() => void saveSafeWord()}
              onVerify={() => void verifySafeWord()}
              onReset={resetLocalWorkspace}
            />
          )}
        </section>

        {appScreens.includes(screen) && hasWorkspace && <BottomTabs activeScreen={screen} onNavigate={navigate} />}
      </section>
    </main>
  );
}

function AppHeader(props: {
  title: string;
  busy: boolean;
  status: string;
  error: string | null;
  health: ApiHealth | null;
  onBack: () => void;
  onHome: () => void;
}) {
  return (
    <div className="app-header">
      <button className="nav-text-button" onClick={props.onBack} aria-label="이전 화면">
        <ChevronLeft size={24} />
      </button>
      <div className="header-title">
        <strong>{props.title}</strong>
        <span className={props.error ? "header-state bad" : "header-state"}>
          {props.busy ? "처리 중" : props.error ? props.error : props.health ? props.status : "API 확인 필요"}
        </span>
      </div>
      <button className="home-link-button" onClick={props.onHome} aria-label="홈으로">
        홈
      </button>
    </div>
  );
}

function WelcomeScreen(props: {
  busy: boolean;
  error: string | null;
  apiBase: string;
  onSignup: () => void;
  onLogin: () => void;
}) {
  return (
    <div className="onboarding">
      <div className="welcome-top-action">
        <button className="signup-pill" onClick={props.onSignup}>
          <UserPlus size={20} />
          회원가입
        </button>
      </div>
      <div className="brand-card">
        <div className="app-icon">
          <PhoneCall size={46} />
        </div>
        <h1>SoriCall</h1>
        <p>가족 사칭 전화를 감지하고 보호자 확인까지 이어주는 안심 통화 앱</p>
      </div>

      <div className="auth-actions">
        <button className="primary-button" onClick={props.onLogin} disabled={props.busy}>
          서비스 시작
        </button>
      </div>

      <div className={props.error ? "notice error" : "notice"}>
        <Database size={16} />
        <span>{props.error ?? `API: ${props.apiBase || "자동 탐색"}`}</span>
      </div>
    </div>
  );
}

function SignupScreen(props: {
  draft: { email: string; password: string; passwordConfirm: string; displayName: string; phoneNumber: string };
  setDraft: React.Dispatch<React.SetStateAction<{ email: string; password: string; passwordConfirm: string; displayName: string; phoneNumber: string }>>;
  error: string | null;
  busy: boolean;
  onSubmit: (event: FormEvent) => void;
  onLogin: () => void;
}) {
  return (
    <form className="auth-form" onSubmit={props.onSubmit}>
      <section className="section-card form-card">
        <p className="form-kicker">SoriCall 계정 만들기</p>
        <h2>보호 서비스를 시작할 계정을 만들어 주세요.</h2>
        <IconInput icon={Users} placeholder="이름" value={props.draft.displayName} onChange={(displayName) => props.setDraft((draft) => ({ ...draft, displayName }))} />
        <IconInput icon={Mail} placeholder="이메일" type="email" value={props.draft.email} onChange={(email) => props.setDraft((draft) => ({ ...draft, email }))} />
        <IconInput icon={Phone} placeholder="휴대폰 번호" type="tel" value={props.draft.phoneNumber} onChange={(phoneNumber) => props.setDraft((draft) => ({ ...draft, phoneNumber }))} />
        <IconInput icon={Lock} placeholder="비밀번호 8자 이상" type="password" value={props.draft.password} onChange={(password) => props.setDraft((draft) => ({ ...draft, password }))} />
        <IconInput icon={Lock} placeholder="비밀번호 확인" type="password" value={props.draft.passwordConfirm} onChange={(passwordConfirm) => props.setDraft((draft) => ({ ...draft, passwordConfirm }))} />
        {props.error && <p className="form-error">{props.error}</p>}
        <button className="primary-button" type="submit" disabled={props.busy}>
          {props.busy ? <Loader2 className="spin" size={18} /> : <UserPlus size={18} />}
          가입하고 동의하기
        </button>
        <button className="secondary-button" type="button" onClick={props.onLogin}>
          이미 계정이 있어요
        </button>
      </section>
    </form>
  );
}

function ConsentScreen(props: {
  consent: {
    requiredData: boolean;
    privacy: boolean;
    nonMedical: boolean;
    syntheticVoice: boolean;
    aiResearch: boolean;
    marketing: boolean;
  };
  setConsent: React.Dispatch<
    React.SetStateAction<{
      requiredData: boolean;
      privacy: boolean;
      nonMedical: boolean;
      syntheticVoice: boolean;
      aiResearch: boolean;
      marketing: boolean;
    }>
  >;
  error: string | null;
  busy: boolean;
  onSubmit: () => void;
}) {
  const allAccepted = Object.values(props.consent).every(Boolean);
  const requiredAccepted =
    props.consent.requiredData && props.consent.privacy && props.consent.nonMedical && props.consent.syntheticVoice;

  function setAll(next: boolean) {
    props.setConsent({
      requiredData: next,
      privacy: next,
      nonMedical: next,
      syntheticVoice: next,
      aiResearch: next,
      marketing: next,
    });
  }

  function toggle(key: keyof typeof props.consent) {
    props.setConsent((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <div className="consent-screen">
      <section className="consent-guide">
        <div className="consent-guide-title">
          <Info size={22} />
          <strong>안내</strong>
        </div>
        <p>
          SoriCall은 치매를 진단하지 않습니다. 가족이 등록한 목소리와 얼굴 정보를 바탕으로 통화 중 의심 신호와
          보호자 확인을 돕는 비의료 참고 서비스입니다.
        </p>
      </section>

      <button className="consent-all" type="button" onClick={() => setAll(!allAccepted)}>
        <span className={allAccepted ? "check-box checked" : "check-box"}>{allAccepted && <Check size={18} />}</span>
        <strong>전체 동의</strong>
        <ChevronRight size={24} />
      </button>

      <div className="consent-list">
        <ConsentItem checked={props.consent.requiredData} required label="데이터 수집 및 분석에 동의합니다." onClick={() => toggle("requiredData")} />
        <ConsentItem checked={props.consent.privacy} required label="개인정보 처리 방침에 동의합니다." onClick={() => toggle("privacy")} />
        <ConsentItem checked={props.consent.nonMedical} required label="비의료적 서비스임을 이해하고 동의합니다." onClick={() => toggle("nonMedical")} />
        <ConsentItem checked={props.consent.syntheticVoice} required label="제3자 음성 포함 가능성을 이해하고 동의합니다." onClick={() => toggle("syntheticVoice")} />
      </div>

      <div className="consent-section-label">선택 동의</div>
      <div className="consent-list">
        <ConsentItem checked={props.consent.aiResearch} label="AI 모델 개선 및 연구 활용에 동의합니다." onClick={() => toggle("aiResearch")} />
        <ConsentItem checked={props.consent.marketing} label="서비스 소식과 보호 알림 안내 수신에 동의합니다." onClick={() => toggle("marketing")} />
      </div>

      {props.error && <p className="form-error">{props.error}</p>}
      <button className="primary-button" type="button" disabled={props.busy || !requiredAccepted} onClick={props.onSubmit}>
        {props.busy ? <Loader2 className="spin" size={18} /> : <UserPlus size={18} />}
        동의하고 가입 완료
      </button>
    </div>
  );
}

function ConsentItem(props: { checked: boolean; required?: boolean; label: string; onClick: () => void }) {
  return (
    <button className="consent-item" type="button" onClick={props.onClick}>
      <span className={props.checked ? "check-box checked" : "check-box"}>{props.checked && <Check size={18} />}</span>
      <strong>
        {props.required && <em>필수</em>}
        {props.label}
      </strong>
    </button>
  );
}

function LoginScreen(props: {
  draft: { email: string; password: string };
  setDraft: React.Dispatch<React.SetStateAction<{ email: string; password: string }>>;
  error: string | null;
  busy: boolean;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form className="auth-form" onSubmit={props.onSubmit}>
      <section className="section-card form-card">
        <p className="form-kicker">다시 시작하기</p>
        <h2>가입한 계정으로 로그인하세요.</h2>
        <IconInput icon={Mail} placeholder="이메일" type="email" value={props.draft.email} onChange={(email) => props.setDraft((draft) => ({ ...draft, email }))} />
        <IconInput icon={Lock} placeholder="비밀번호" type="password" value={props.draft.password} onChange={(password) => props.setDraft((draft) => ({ ...draft, password }))} />
        {props.error && <p className="form-error">{props.error}</p>}
        <button className="primary-button" type="submit" disabled={props.busy}>
          {props.busy ? <Loader2 className="spin" size={18} /> : <Shield size={18} />}
          로그인
        </button>
      </section>
    </form>
  );
}

function RoleScreen(props: { role: "SENIOR" | "GUARDIAN" | null; onChoose: (role: "SENIOR" | "GUARDIAN") => void }) {
  return (
    <div className="stack">
      <section className="service-title-block">
        <h2>목소리와 가족 확인으로 안심을 지켜볼까요?</h2>
      </section>
      <button className={props.role === "GUARDIAN" ? "role-card selected" : "role-card"} onClick={() => props.onChoose("GUARDIAN")}>
        <div className="role-avatar">보</div>
        <div>
          <strong>부모님 전화 안심확인</strong>
          <span>부모님 통화와 위험 알림을 보호자가 함께 확인합니다.</span>
        </div>
        <ChevronRight size={20} />
      </button>
      <button className={props.role === "SENIOR" ? "role-card selected" : "role-card"} onClick={() => props.onChoose("SENIOR")}>
        <div className="role-avatar">나</div>
        <div>
          <strong>내 안심 보호 시작</strong>
          <span>내 전화와 가족 확인 요청을 보호자에게 연결합니다.</span>
        </div>
        <ChevronRight size={20} />
      </button>
      <button className="history-link-card" onClick={() => props.onChoose("GUARDIAN")}>
        <History size={24} />
        <strong>이전 결과 보기</strong>
        <ChevronRight size={22} />
      </button>
      <div className="notice">
        <Shield size={18} />
        <span>본 서비스는 의료 진단이 아닌 가족 보호 참고 정보를 제공합니다.</span>
      </div>
    </div>
  );
}

function ConnectScreen(props: {
  draft: { familyName: string; seniorName: string; seniorPhone: string; relation: string };
  setDraft: React.Dispatch<React.SetStateAction<{ familyName: string; seniorName: string; seniorPhone: string; relation: string }>>;
  role: "SENIOR" | "GUARDIAN" | null;
  busy: boolean;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form className="stack" onSubmit={props.onSubmit}>
      <section className="section-card form-card">
        <p className="form-kicker">{props.role === "SENIOR" ? "내 보호 연결" : "부모님 연결"}</p>
        <h2>가족 DB를 만들고 서비스를 연결합니다.</h2>
        <input value={props.draft.familyName} onChange={(event) => props.setDraft((draft) => ({ ...draft, familyName: event.target.value }))} placeholder="가족 이름" />
        <input value={props.draft.seniorName} onChange={(event) => props.setDraft((draft) => ({ ...draft, seniorName: event.target.value }))} placeholder="어르신 이름" />
        <input inputMode="tel" value={props.draft.seniorPhone} onChange={(event) => props.setDraft((draft) => ({ ...draft, seniorPhone: event.target.value }))} placeholder="어르신 휴대폰" />
        {props.role === "GUARDIAN" && (
          <input value={props.draft.relation} onChange={(event) => props.setDraft((draft) => ({ ...draft, relation: event.target.value }))} placeholder="관계" />
        )}
        <button className="primary-button" type="submit" disabled={props.busy}>
          {props.busy ? <Loader2 className="spin" size={18} /> : <Database size={18} />}
          연결하고 홈으로
        </button>
      </section>
    </form>
  );
}

function IconInput(props: {
  icon: React.ElementType;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  type?: string;
}) {
  const Icon = props.icon;
  return (
    <label className="icon-input">
      <Icon size={17} />
      <input
        type={props.type ?? "text"}
        value={props.value}
        onChange={(event) => props.onChange(event.target.value)}
        placeholder={props.placeholder}
      />
    </label>
  );
}

function HomeScreen(props: {
  workspace: Workspace;
  faces: FaceProfile[];
  voices: VoiceProfile[];
  latestRisk: RiskEvent | null;
  callEvaluation: CallEvaluation | null;
  onEvaluate: () => void;
  onVideo: () => void;
  onNavigate: (screen: Screen) => void;
}) {
  return (
    <div className="stack">
      <section className="greeting">
        <div className="portrait">{props.workspace.senior?.name.slice(0, 1)}</div>
        <div>
          <h2>{props.workspace.senior?.name} 오늘도 안심하세요.</h2>
          <p>{props.workspace.account?.display_name} 계정으로 보호 서비스가 연결되어 있습니다.</p>
        </div>
      </section>
      <section className={props.latestRisk ? "risk-banner active" : "risk-banner"}>
        <Shield size={23} />
        <div>
          <strong>{props.latestRisk ? "위험 전화 확인 필요" : "안심 상태"}</strong>
          <span>{props.latestRisk?.summary ?? "최근 위험 전화가 없습니다."}</span>
        </div>
      </section>
      <div className="quick-grid">
        <QuickButton icon={PhoneCall} label="위험 전화 평가" onClick={props.onEvaluate} danger />
        <QuickButton icon={Video} label="화상 가족 확인" onClick={props.onVideo} />
        <QuickButton icon={Users} label="가족 등록" onClick={() => props.onNavigate("family")} />
        <QuickButton icon={KeyRound} label="안심 단어" onClick={() => props.onNavigate("settings")} />
      </div>
      <section className="summary-card">
        <SummaryRow label="가족 연락처" value={`${props.workspace.members.length}명`} />
        <SummaryRow label="얼굴 프로필" value={`${props.faces.length}개`} />
        <SummaryRow label="음성 프로필" value={`${props.voices.length}개`} />
        <SummaryRow label="최근 위험도" value={props.callEvaluation?.risk_level ?? "-"} />
      </section>
    </div>
  );
}

function FamilyScreen(props: {
  workspace: Workspace;
  faces: FaceProfile[];
  voices: VoiceProfile[];
  memberDraft: { name: string; relation: string; phone_number: string };
  setMemberDraft: React.Dispatch<React.SetStateAction<{ name: string; relation: string; phone_number: string }>>;
  onAdd: (event: FormEvent) => void;
  onVoice: () => void;
}) {
  return (
    <div className="stack">
      <section className="section-card">
        <div className="section-title">
          <h2>연결된 가족</h2>
          <span>{props.workspace.members.length}명</span>
        </div>
        <div className="family-list">
          {props.workspace.members.map((member) => (
            <article className="family-item" key={member.id}>
              <div className="face">{member.name.slice(0, 1)}</div>
              <div>
                <strong>{member.name}</strong>
                <span>{member.relation ?? "가족"} · 끝자리 {member.phone_number_last4 ?? "----"}</span>
              </div>
              <Check size={18} />
            </article>
          ))}
        </div>
      </section>
      <form className="section-card form-card" onSubmit={props.onAdd}>
        <h2>가족 추가</h2>
        <input aria-label="이름" value={props.memberDraft.name} onChange={(event) => props.setMemberDraft((draft) => ({ ...draft, name: event.target.value }))} />
        <input aria-label="관계" value={props.memberDraft.relation} onChange={(event) => props.setMemberDraft((draft) => ({ ...draft, relation: event.target.value }))} />
        <input aria-label="전화번호" inputMode="tel" value={props.memberDraft.phone_number} onChange={(event) => props.setMemberDraft((draft) => ({ ...draft, phone_number: event.target.value }))} />
        <button className="primary-button" type="submit">
          가족과 얼굴 등록
        </button>
      </form>
      <section className="section-card">
        <div className="section-title">
          <h2>인증 프로필</h2>
          <span>얼굴 {props.faces.length} · 음성 {props.voices.length}</span>
        </div>
        <button className="secondary-button" onClick={props.onVoice}>
          <Mic size={18} />
          음성 프로필 등록
        </button>
      </section>
    </div>
  );
}

function GuardScreen(props: {
  phoneNumber: string;
  setPhoneNumber: (value: string) => void;
  evaluation: CallEvaluation | null;
  latestRisk: RiskEvent | null;
  onEvaluate: () => void;
  onNotify: () => void;
}) {
  return (
    <div className="stack">
      <section className="alert-card">
        <AlertTriangle size={44} />
        <h2>의심 전화 경고</h2>
        <p>번호 위험도와 가족 사칭 패턴을 평가합니다.</p>
      </section>
      <section className="section-card form-card">
        <label>
          수신 번호
          <input inputMode="tel" value={props.phoneNumber} onChange={(event) => props.setPhoneNumber(event.target.value)} />
        </label>
        <button className="danger-button" onClick={props.onEvaluate}>
          위험도 평가 API 호출
        </button>
      </section>
      {props.evaluation && (
        <section className="danger-result">
          <span>{props.evaluation.risk_level}</span>
          <h2>{props.evaluation.message_for_senior}</h2>
          <p>위험도 {props.evaluation.risk_score}점 · {props.evaluation.reason_codes.join(", ")}</p>
          <button className="warning-button" onClick={props.onNotify} disabled={!props.latestRisk}>
            <BellRing size={18} />
            보호자 알림 보내기
          </button>
        </section>
      )}
    </div>
  );
}

function VerifyScreen(props: {
  primaryMember: FamilyMember | null;
  latestNotification: EmergencyNotification | null;
  latestVideo: VideoVerification | null;
  onRequest: () => void;
  onAccept: () => void;
  onRespond: (response: "REAL_CALL" | "NOT_ME" | "UNKNOWN") => void;
}) {
  return (
    <div className="stack">
      <section className="video-card">
        <div className="video-placeholder">
          <Video size={44} />
          <span>화상 확인 대기</span>
        </div>
        <h2>{props.primaryMember?.name ?? "가족"} 얼굴 확인</h2>
        <p>요청 상태: {props.latestVideo?.status ?? "요청 전"} · 결과: {props.latestVideo?.result ?? "-"}</p>
        <button className="primary-button" onClick={props.onRequest}>
          화상 확인 요청 저장
        </button>
        <button className="secondary-button" onClick={props.onAccept} disabled={!props.latestVideo}>
          얼굴 일치 수락 저장
        </button>
      </section>
      <section className="section-card">
        <div className="section-title">
          <h2>보호자 응답</h2>
          <span>{props.latestNotification?.status ?? "알림 없음"}</span>
        </div>
        <button className="secondary-button" onClick={() => props.onRespond("REAL_CALL")} disabled={!props.latestNotification}>
          내가 전화함
        </button>
        <button className="danger-button" onClick={() => props.onRespond("NOT_ME")} disabled={!props.latestNotification}>
          내가 아님, 사칭 의심
        </button>
      </section>
    </div>
  );
}

function HistoryScreen({ workspace }: { workspace: Workspace }) {
  const items = [
    ...workspace.riskEvents.map((item) => ({
      id: `risk-${item.id}`,
      icon: AlertTriangle,
      title: `${item.risk_level} · ${item.risk_score}점`,
      text: item.summary ?? item.reason_codes.join(", "),
    })),
    ...workspace.notifications.map((item) => ({
      id: `noti-${item.id}`,
      icon: BellRing,
      title: `보호자 알림 · ${item.status}`,
      text: item.response ?? item.message ?? "응답 대기",
    })),
    ...workspace.videoVerifications.map((item) => ({
      id: `video-${item.id}`,
      icon: Video,
      title: `화상 확인 · ${item.status}`,
      text: `${item.result} · ${item.match_score ?? "-"}점`,
    })),
  ];
  return (
    <div className="stack">
      <section className="section-card">
        <div className="section-title">
          <h2>서비스 기록</h2>
          <span>{items.length}건</span>
        </div>
        <div className="timeline">
          {items.length === 0 && <p className="empty">아직 저장된 기록이 없습니다.</p>}
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.id}>
                <Icon size={18} />
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.text}</span>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function SettingsScreen(props: {
  settings: { unknownNumber: boolean; guardianAlert: boolean; voiceWarning: boolean };
  setSettings: React.Dispatch<React.SetStateAction<{ unknownNumber: boolean; guardianAlert: boolean; voiceWarning: boolean }>>;
  safeWord: string;
  setSafeWord: (value: string) => void;
  matched: boolean | null;
  apiBase: string;
  onSave: () => void;
  onVerify: () => void;
  onReset: () => void;
}) {
  return (
    <div className="stack">
      <section className="section-card form-card">
        <h2>안심 단어</h2>
        <input value={props.safeWord} onChange={(event) => props.setSafeWord(event.target.value)} />
        <div className="two-buttons">
          <button className="primary-button" onClick={props.onSave}>저장</button>
          <button className="secondary-button" onClick={props.onVerify}>검증</button>
        </div>
        {props.matched !== null && <p className={props.matched ? "ok" : "bad"}>{props.matched ? "일치합니다." : "일치하지 않습니다."}</p>}
      </section>
      <section className="section-card">
        <Toggle label="모르는 번호 주의 표시" checked={props.settings.unknownNumber} onClick={() => toggleSetting(props.setSettings, "unknownNumber")} />
        <Toggle label="위험 전화 보호자 알림" checked={props.settings.guardianAlert} onClick={() => toggleSetting(props.setSettings, "guardianAlert")} />
        <Toggle label="음성 경고 안내" checked={props.settings.voiceWarning} onClick={() => toggleSetting(props.setSettings, "voiceWarning")} />
      </section>
      <section className="section-card">
        <div className="api-info">
          <Database size={18} />
          <span>{props.apiBase || "API 자동 탐색"}</span>
        </div>
        <button className="ghost-button" onClick={props.onReset}>
          로그아웃 및 이 기기 데이터 초기화
        </button>
      </section>
    </div>
  );
}

function BottomTabs({ activeScreen, onNavigate }: { activeScreen: Screen; onNavigate: (screen: Screen) => void }) {
  return (
    <nav className="bottom-tabs" aria-label="주요 메뉴">
      {bottomTabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <button className={activeScreen === tab.key ? "active" : ""} key={tab.key} onClick={() => onNavigate(tab.key)}>
            <Icon size={19} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function StepLine({ number, title }: { number: string; title: string }) {
  return (
    <div className="step-line">
      <span>{number}</span>
      <strong>{title}</strong>
      <ChevronRight size={18} />
    </div>
  );
}

function QuickButton(props: { icon: React.ElementType; label: string; onClick: () => void; danger?: boolean }) {
  const Icon = props.icon;
  return (
    <button className={props.danger ? "quick-button danger" : "quick-button"} onClick={props.onClick}>
      <Icon size={27} />
      <span>{props.label}</span>
    </button>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Toggle({ label, checked, onClick }: { label: string; checked: boolean; onClick: () => void }) {
  return (
    <button className="toggle" onClick={onClick}>
      <span>{label}</span>
      <i className={checked ? "on" : ""} />
    </button>
  );
}

function toggleSetting<T extends Record<string, boolean>>(
  setSettings: React.Dispatch<React.SetStateAction<T>>,
  key: keyof T,
) {
  setSettings((current) => ({ ...current, [key]: !current[key] }));
}

function titleFor(screen: Screen): string {
  return {
    welcome: "SoriCall",
    signup: "회원가입",
    consent: "동의 절차",
    login: "로그인",
    role: "서비스 시작",
    connect: "부모님 연결",
    home: "홈",
    family: "가족 등록",
    guard: "의심 전화 경고",
    verify: "화상 확인",
    history: "기록",
    settings: "설정",
  }[screen];
}

function loadWorkspace(): Workspace {
  try {
    const stored = localStorage.getItem(storageKey);
    return stored ? { ...emptyWorkspace, ...JSON.parse(stored) } : emptyWorkspace;
  } catch {
    return emptyWorkspace;
  }
}

function persistWorkspace(workspace: Workspace) {
  if (!workspace.account) return;
  localStorage.setItem(storageKey, JSON.stringify(workspace));
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
