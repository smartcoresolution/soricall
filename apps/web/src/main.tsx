import React, { useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  Activity, AlertTriangle, ArrowLeft, Bell, Check, CheckCircle2, ChevronRight,
  CircleUserRound, Clock3, FileClock, HeartHandshake, Home, LockKeyhole, Mic,
  Phone, PhoneCall, PhoneOff, Plus, Settings, Shield, ShieldAlert, Sparkles,
  UserRoundCheck, Users, Video, Volume2, X,
} from "lucide-react";
import { apiPost, setApiAccessToken, type Family, type UserPublic } from "./api";
import "./styles.css";
import "./feedback.css";

type Screen =
  | "welcome" | "signup" | "consent" | "login" | "home" | "protected"
  | "contacts" | "biometrics" | "normal" | "analysis" | "blocked"
  | "confirm" | "history" | "admin";

const protectedRelations = ["아버지", "어머니", "할아버지", "할머니", "기타"];
const contactRelations = ["아들", "딸", "손자", "손녀", "배우자", "기타 가족"];
const protectedRelationCodes: Record<string, string> = { 아버지: "FATHER", 어머니: "MOTHER", 할아버지: "GRANDFATHER", 할머니: "GRANDMOTHER", 기타: "OTHER" };
const contactRelationCodes: Record<string, string> = { 아들: "SON", 딸: "DAUGHTER", 손자: "GRANDSON", 손녀: "GRANDDAUGHTER", 배우자: "SPOUSE", "기타 가족": "OTHER" };

type AuthResponse = { access_token: string; refresh_token: string; user: UserPublic };
type ProtectedUserResponse = { id: string };

function App() {
  const [screen, setScreen] = useState<Screen>("welcome");
  const [protectedRelation, setProtectedRelation] = useState("어머니");
  const [contactRelation, setContactRelation] = useState("딸");
  const [agreed, setAgreed] = useState([true, true, true, true, false]);
  const [analysisStep, setAnalysisStep] = useState(2);
  const [signup, setSignup] = useState({ name: "", email: "", password: "", passwordConfirm: "" });
  const [login, setLogin] = useState({ email: "", password: "" });
  const [protectedForm, setProtectedForm] = useState({ name: "", phone: "" });
  const [contactForm, setContactForm] = useState({ name: "", phone: "", primary: true });
  const [session, setSession] = useState<AuthResponse | null>(null);
  const [familyId, setFamilyId] = useState<string | null>(null);
  const [protectedUserId, setProtectedUserId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [apiError, setApiError] = useState("");

  const runApi = async (action: () => Promise<void>) => {
    setBusy(true); setApiError("");
    try { await action(); } catch (error) { setApiError(error instanceof Error ? error.message : "요청을 처리하지 못했습니다."); }
    finally { setBusy(false); }
  };

  const register = () => runApi(async () => {
    if (signup.password !== signup.passwordConfirm) throw new Error("비밀번호 확인이 일치하지 않습니다.");
    const auth = await apiPost<AuthResponse>("/api/v1/auth/register", { email: signup.email, password: signup.password, display_name: signup.name, role: "GUARDIAN" });
    setApiAccessToken(auth.access_token); setSession(auth); setScreen("protected");
  });
  const signIn = () => runApi(async () => {
    const auth = await apiPost<AuthResponse>("/api/v1/auth/login", login);
    setApiAccessToken(auth.access_token); setSession(auth); setScreen("home");
  });
  const saveProtectedUser = () => runApi(async () => {
    if (!session) throw new Error("먼저 회원가입 또는 로그인이 필요합니다.");
    let currentFamilyId = familyId;
    if (!currentFamilyId) {
      const family = await apiPost<Family>("/api/v1/families", { name: `${protectedForm.name} 통화보호 가족`, created_by: session.user.id });
      currentFamilyId = family.id; setFamilyId(family.id);
    }
    const member = await apiPost<ProtectedUserResponse>(`/api/v1/families/${currentFamilyId}/protected-call-users`, { name: protectedForm.name, phone_number: protectedForm.phone, relation_code: protectedRelationCodes[protectedRelation] });
    setProtectedUserId(member.id); setScreen("contacts");
  });
  const saveContact = () => runApi(async () => {
    if (!familyId || !protectedUserId) throw new Error("보호받을 가족을 먼저 등록해 주세요.");
    await apiPost(`/api/v1/families/${familyId}/protected-call-users/${protectedUserId}/confirmation-contacts`, { name: contactForm.name, phone_number: contactForm.phone, relation_code: contactRelationCodes[contactRelation], is_primary_contact: contactForm.primary, notification_priority: 1, notify_enabled: true });
    setScreen("biometrics");
  });

  const title = useMemo(() => ({
    signup: "회원가입", consent: "서비스 이용 동의", login: "로그인",
    protected: "통화 보호 가족 등록", contacts: "확인 가족 등록",
    biometrics: "가족 정보 등록", normal: "안전한 전화", analysis: "의심전화 분석",
    blocked: "고위험 전화 차단", confirm: "가족 확인 요청", history: "통화기록",
    admin: "관리자 페이지", home: "통화 보호 홈", welcome: "",
  }[screen]), [screen]);

  const goBack = () => setScreen(screen === "signup" ? "welcome" : "home");

  return (
    <div className="site-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setScreen("home")}>
          <span className="brand-mark"><Shield size={22} /></span>
          <span>SoriCall<small>안심소리 가족콜</small></span>
        </button>
        {screen !== "welcome" && <div className="top-title">{title}</div>}
        <div className="top-actions">
          <button className="icon-button"><Bell size={20} /><i /></button>
          <button className="avatar">김</button>
        </div>
      </header>

      <main className={`page ${screen === "welcome" ? "welcome-page" : ""}`}>
        {screen !== "welcome" && screen !== "home" && (
          <button className="back-button" onClick={goBack}><ArrowLeft size={18} /> 이전</button>
        )}
        {screen === "welcome" && <Welcome onSignup={() => setScreen("signup")} onLogin={() => setScreen("login")} />}
        {screen === "signup" && <Signup value={signup} setValue={setSignup} onNext={() => setScreen("consent")} />}
        {screen === "consent" && <Consent agreed={agreed} setAgreed={setAgreed} onNext={register} />}
        {screen === "login" && <Login value={login} setValue={setLogin} onNext={signIn} />}
        {screen === "protected" && <ProtectedRegistration value={protectedForm} setValue={setProtectedForm} relation={protectedRelation} setRelation={setProtectedRelation} onNext={saveProtectedUser} />}
        {screen === "contacts" && <ContactRegistration value={contactForm} setValue={setContactForm} relation={contactRelation} setRelation={setContactRelation} onNext={saveContact} />}
        {screen === "biometrics" && <Biometrics onDone={() => setScreen("home")} />}
        {screen === "home" && <Dashboard navigate={setScreen} />}
        {screen === "normal" && <NormalCall onHome={() => setScreen("home")} />}
        {screen === "analysis" && <Analysis step={analysisStep} setStep={setAnalysisStep} onBlock={() => setScreen("blocked")} />}
        {screen === "blocked" && <BlockedCall onConfirm={() => setScreen("confirm")} />}
        {screen === "confirm" && <Confirmation onDone={() => setScreen("history")} />}
        {screen === "history" && <HistoryPage />}
        {screen === "admin" && <AdminPage />}
      </main>
      {(busy || apiError) && <div className={`api-feedback ${apiError ? "error" : ""}`}>{busy ? "안전하게 저장하고 있습니다…" : apiError}<button onClick={() => setApiError("")}><X /></button></div>}

      {!(["welcome", "signup", "consent", "login", "normal", "analysis", "blocked", "confirm"] as Screen[]).includes(screen) && (
        <nav className="bottom-nav">
          <NavItem active={screen === "home"} icon={<Home />} label="홈" onClick={() => setScreen("home")} />
          <NavItem active={screen === "protected" || screen === "contacts"} icon={<Users />} label="가족" onClick={() => setScreen("protected")} />
          <NavItem active={screen === "history"} icon={<FileClock />} label="기록" onClick={() => setScreen("history")} />
          <NavItem active={screen === "admin"} icon={<Settings />} label="관리" onClick={() => setScreen("admin")} />
        </nav>
      )}
    </div>
  );
}

function Welcome({ onSignup, onLogin }: { onSignup: () => void; onLogin: () => void }) {
  return <div className="hero-grid">
    <section className="hero-copy">
      <span className="eyebrow"><Sparkles size={16} /> AI 가족 사칭 전화 보호</span>
      <h1>부모님의 전화를<br/><em>보이스피싱으로부터</em><br/>지켜드립니다.</h1>
      <p>가족의 전화번호와 목소리를 기억하고, 의심되는 통화는 가족에게 한 번 더 확인합니다.</p>
      <div className="hero-actions"><button className="primary large" onClick={onSignup}>통화 보호 시작하기 <ChevronRight /></button><button className="text-button" onClick={onLogin}>이미 가입했어요</button></div>
      <div className="trust-row"><span><CheckCircle2 /> 가족 번호 확인</span><span><CheckCircle2 /> AI 음성 분석</span><span><CheckCircle2 /> 가족 즉시 알림</span></div>
    </section>
    <section className="phone-preview">
      <div className="preview-status"><span>9:41</span><span>● ● ●</span></div>
      <div className="shield-orbit"><ShieldAlert /><i /><i /></div>
      <small>의심전화 분석 중</small><h3>가족 사칭 여부를<br/>확인하고 있어요</h3>
      <div className="analysis-mini"><span className="done"><Check /> 전화번호 확인</span><span className="active"><Activity /> 음성 위험 분석</span><span><Clock3 /> 가족 확인 대기</span></div>
    </section>
  </div>;
}

function Signup({ value, setValue, onNext }: { value: {name:string;email:string;password:string;passwordConfirm:string}; setValue: React.Dispatch<React.SetStateAction<typeof value>>; onNext: () => void }) { return <FormCard step="1 / 3" title="가족의 안심을 시작해요" description="가입 정보는 통화 보호와 가족 확인에만 사용됩니다.">
  <Field label="이름" placeholder="이름을 입력해 주세요" value={value.name} onChange={name => setValue(v => ({...v,name}))}/><Field label="이메일" placeholder="example@email.com" type="email" value={value.email} onChange={email => setValue(v => ({...v,email}))}/><Field label="비밀번호" placeholder="8자 이상 입력해 주세요" type="password" value={value.password} onChange={password => setValue(v => ({...v,password}))}/><Field label="비밀번호 확인" placeholder="한 번 더 입력해 주세요" type="password" value={value.passwordConfirm} onChange={passwordConfirm => setValue(v => ({...v,passwordConfirm}))}/>
  <button className="primary full" disabled={!value.name || !value.email || value.password.length < 8 || value.password !== value.passwordConfirm} onClick={onNext}>다음</button><p className="form-note"><LockKeyhole /> 개인정보는 암호화하여 안전하게 보관합니다.</p>
</FormCard>; }

function Consent({ agreed, setAgreed, onNext }: { agreed: boolean[]; setAgreed: (v: boolean[]) => void; onNext: () => void }) {
  const items = [["서비스 이용약관", true], ["개인정보 수집·이용", true], ["가족 전화번호 및 음성 특징정보 처리", true], ["통화 위험분석 및 가족 알림", true], ["얼굴정보 처리", false]] as const;
  const toggle = (i: number) => setAgreed(agreed.map((v, n) => n === i ? !v : v));
  return <FormCard step="2 / 3" title="서비스 이용에 동의해 주세요" description="얼굴정보는 선택사항이며 동의하지 않아도 서비스를 이용할 수 있습니다.">
    <button className={`agree-all ${agreed.every(Boolean) ? "checked" : ""}`} onClick={() => setAgreed(items.map(() => !agreed.every(Boolean)))}><span><Check /></span>전체 동의</button>
    <div className="consent-list">{items.map(([label, required], i) => <button key={label} onClick={() => toggle(i)}><span className={agreed[i] ? "check checked" : "check"}><Check /></span><b>{required ? "[필수]" : "[선택]"}</b>{label}<ChevronRight /></button>)}</div>
    <button className="primary full" disabled={!agreed.slice(0, 4).every(Boolean)} onClick={onNext}>동의하고 계속하기</button>
  </FormCard>;
}

function Login({ value, setValue, onNext }: { value:{email:string;password:string}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; onNext: () => void }) { return <FormCard title="다시 만나서 반가워요" description="등록한 계정으로 로그인해 주세요."><Field label="이메일" placeholder="example@email.com" type="email" value={value.email} onChange={email => setValue(v => ({...v,email}))}/><Field label="비밀번호" placeholder="비밀번호" type="password" value={value.password} onChange={password => setValue(v => ({...v,password}))}/><div className="between"><label><input type="checkbox"/> 로그인 유지</label><button className="link">비밀번호 찾기</button></div><button className="primary full" disabled={!value.email || !value.password} onClick={onNext}>로그인</button></FormCard>; }

function ProtectedRegistration({ value, setValue, relation, setRelation, onNext }: { value:{name:string;phone:string}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; relation: string; setRelation: (v: string) => void; onNext: () => void }) { return <FormCard step="1 / 3" title="보이스피싱으로부터 누구의 전화를 보호할까요?" description="부모님 또는 조부모님의 휴대전화에 의심전화 경고와 차단을 제공합니다.">
  <RelationGrid options={protectedRelations} value={relation} setValue={setRelation}/><Field label="성함" placeholder="예: 김영희" value={value.name} onChange={name => setValue(v => ({...v,name}))}/><Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value.phone} onChange={phone => setValue(v => ({...v,phone}))}/>
  <InfoBox icon={<Shield />}><b>정보 등록 후 보호할 가족의 휴대전화에서 로그인하면</b><br/>보이스피싱 통화 보호가 자동으로 시작됩니다.</InfoBox><button className="primary full" disabled={!value.name || value.phone.length < 4} onClick={onNext}>다음: 확인 가족 등록</button>
</FormCard>; }

function ContactRegistration({ value, setValue, relation, setRelation, onNext }: { value:{name:string;phone:string;primary:boolean}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; relation: string; setRelation: (v: string) => void; onNext: () => void }) { return <FormCard step="2 / 3" title="의심전화를 확인해 줄 가족을 등록해 주세요" description="보호받을 가족에게 의심전화가 오면 실제 통화 여부를 확인합니다.">
  <label className="section-label">보호받을 가족과의 관계</label><RelationGrid options={contactRelations} value={relation} setValue={setRelation}/><Field label="성함" placeholder="예: 김민지" value={value.name} onChange={name => setValue(v => ({...v,name}))}/><Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value.phone} onChange={phone => setValue(v => ({...v,phone}))}/>
  <label className="toggle-row"><span><b>가장 먼저 확인할 가족</b><small>의심전화 발생 시 첫 번째로 알림을 보냅니다.</small></span><input type="checkbox" checked={value.primary} onChange={e => setValue(v => ({...v,primary:e.target.checked}))}/></label>
  <button className="secondary full"><Plus /> 확인 가족 한 명 더 추가</button><button className="primary full" disabled={!value.name || value.phone.length < 4} onClick={onNext}>다음: 가족 정보 등록</button>
</FormCard>; }

function Biometrics({ onDone }: { onDone: () => void }) { return <FormCard step="3 / 3" title="가족의 목소리를 등록해 주세요" description="등록 가족의 목소리와 의심전화의 목소리를 비교해 가족 사칭 가능성을 확인합니다.">
  <div className="profile-select"><span className="person-icon">김</span><span><b>김민지 · 딸</b><small>음성 등록 필요</small></span><ChevronRight /></div>
  <div className="record-card"><div className="mic-ring"><Mic /></div><b>아래 문장을 자연스럽게 읽어 주세요</b><p>“엄마, 오늘 저녁에 다시 전화드릴게요.”</p><div className="wave">{Array.from({length: 28}).map((_, i) => <i key={i} style={{height: `${12 + (i * 13) % 35}px`}}/>)}</div><button className="primary round"><Mic /> 녹음 시작</button></div>
  <button className="optional-card"><Video /><span><b>얼굴정보도 등록할까요?</b><small>선택사항 · 나중에 등록할 수 있어요</small></span><ChevronRight /></button><button className="primary full" onClick={onDone}>등록 완료</button>
</FormCard>; }

function Dashboard({ navigate }: { navigate: (s: Screen) => void }) { return <div className="dashboard">
  <section className="status-hero"><div><span className="status-pill"><i/> 통화 보호 켜짐</span><h1>김영희 어머니의 전화를<br/><em>보이스피싱으로부터</em> 보호하고 있습니다.</h1><p>마지막 확인 오늘 오전 9:41 · 모든 기능 정상</p></div><div className="hero-shield"><Shield /><span><Check /></span></div></section>
  <section className="stat-grid"><Stat icon={<PhoneCall/>} value="12" label="이번 달 확인 전화"/><Stat icon={<ShieldAlert/>} value="3" label="의심전화 감지" tone="orange"/><Stat icon={<PhoneOff/>} value="1" label="고위험 차단" tone="red"/><Stat icon={<Users/>} value="2명" label="확인 가족"/></section>
  <div className="section-heading"><div><span>통화 보호 상태</span><h2>모든 준비가 완료됐어요</h2></div><button onClick={() => navigate("protected")}>관리하기 <ChevronRight/></button></div>
  <section className="ready-grid"><Ready icon={<Phone/>} title="가족 연락처" text="등록 완료 · 3개 번호"/><Ready icon={<Mic/>} title="가족 음성" text="등록 완료 · 품질 좋음"/><Ready icon={<UserRoundCheck/>} title="확인 가족" text="김민지 외 1명"/><Ready icon={<Activity/>} title="AI 위험 분석" text="정상 작동 중"/></section>
  <div className="section-heading"><div><span>최근 통화</span><h2>통화 보호 기록</h2></div><button onClick={() => navigate("history")}>전체 보기 <ChevronRight/></button></div>
  <section className="recent-list"><CallRow tone="safe" icon={<Check/>} title="등록된 가족 전화" meta="김민지 · 딸 · 오늘 오전 9:41" badge="안전" onClick={() => navigate("normal")}/><CallRow tone="warn" icon={<AlertTriangle/>} title="가족 사칭 의심전화" meta="번호 끝 8821 · 어제 오후 3:18" badge="확인 완료" onClick={() => navigate("analysis")}/><CallRow tone="danger" icon={<PhoneOff/>} title="고위험 전화 차단" meta="번호 끝 4402 · 7월 12일" badge="차단" onClick={() => navigate("blocked")}/></section>
</div>; }

function NormalCall({ onHome }: { onHome: () => void }) { return <CallStage tone="safe" icon={<PhoneCall/>} eyebrow="등록된 가족 전화" title="김민지 딸의 전화입니다" description="등록된 전화번호와 가족 정보가 일치합니다."><div className="caller-card"><span className="person-icon">김</span><span><b>김민지</b><small>딸 · 010-••••-4421</small></span><span className="safe-label"><Check/> 안전</span></div><button className="primary full" onClick={onHome}><PhoneCall/> 통화 계속하기</button></CallStage>; }

function Analysis({ step, setStep, onBlock }: { step: number; setStep: (n: number) => void; onBlock: () => void }) { const steps = [["전화번호 확인", "등록되지 않은 번호입니다"], ["가족 음성 비교", "가족 목소리와 유사합니다"], ["AI 합성음 분석", "합성음 가능성이 감지됐습니다"], ["통화내용 분석", "송금 요구 표현이 감지됐습니다"], ["가족 확인", "김민지 딸에게 확인 중입니다"]]; return <CallStage tone="warn" icon={<ShieldAlert/>} eyebrow="통화 중 실시간 확인" title="가족 사칭이 의심됩니다" description="돈을 보내거나 앱을 설치하지 마세요. 가족에게 확인하고 있습니다."><div className="analysis-list">{steps.map(([a,b], i) => <div key={a} className={i < step ? "complete" : i === step ? "working" : "pending"}><span>{i < step ? <Check/> : i === step ? <Activity/> : <Clock3/>}</span><div><b>{a}</b><small>{i <= step ? b : "확인 대기"}</small></div>{i === step && <i className="pulse"/>}</div>)}</div><div className="button-row"><button className="secondary" onClick={() => setStep(Math.min(4, step + 1))}>분석 진행 보기</button><button className="danger" onClick={onBlock}><PhoneOff/> 지금 통화 끊기</button></div></CallStage>; }

function BlockedCall({ onConfirm }: { onConfirm: () => void }) { return <CallStage tone="danger" icon={<PhoneOff/>} eyebrow="고위험 전화 차단" title="보이스피싱 위험이 높아 전화를 차단했습니다" description="가족 목소리처럼 들려도 저장된 가족 번호로 다시 확인하세요."><div className="risk-reasons"><b>차단한 이유</b><span><X/> 등록되지 않은 전화번호</span><span><X/> AI 합성음 가능성 높음</span><span><X/> 송금 요구 표현 감지</span></div><button className="primary full"><PhoneCall/> 저장된 가족에게 다시 전화</button><button className="secondary full" onClick={onConfirm}><HeartHandshake/> 확인 가족에게 요청</button></CallStage>; }

function Confirmation({ onDone }: { onDone: () => void }) { return <CallStage tone="confirm" icon={<HeartHandshake/>} eyebrow="가족 확인 요청" title="지금 김영희 어머니께 전화하셨나요?" description="가족의 응답은 의심전화 위험도 판단에 바로 반영됩니다."><div className="confirm-caller"><span className="person-icon">김</span><div><b>김영희 어머니</b><small>의심전화 수신 · 지금</small></div></div><button className="answer yes" onClick={onDone}><CheckCircle2/><span><b>네, 제가 전화했어요</b><small>정상 가족 통화입니다</small></span></button><button className="answer no" onClick={onDone}><X/><span><b>아니요, 제가 아닙니다</b><small>즉시 위험도를 높이고 차단합니다</small></span></button><button className="answer unknown" onClick={onDone}><AlertTriangle/><span><b>잘 모르겠습니다</b><small>추가 확인을 진행합니다</small></span></button></CallStage>; }

function HistoryPage() { return <div className="content-wide"><div className="page-heading"><span className="eyebrow">통화 보호 기록</span><h1>최근 통화를 확인하세요</h1><p>민감한 통화내용은 기본적으로 숨겨지며 보존기간 후 자동 삭제됩니다.</p></div><div className="filter-row"><button className="active">전체 16</button><button>안전 12</button><button>주의 2</button><button>차단 2</button></div><section className="history-table"><div className="table-head"><span>상태</span><span>통화 정보</span><span>판단 근거</span><span>가족 확인</span><span>시간</span></div><HistoryRow tone="safe" status="안전" call="김민지 · 딸" reason="등록 가족 번호 일치" confirm="확인 불필요" time="오늘 09:41"/><HistoryRow tone="warn" status="주의" call="번호 끝 8821" reason="미등록 번호 · 유사 음성" confirm="전화했음" time="어제 15:18"/><HistoryRow tone="danger" status="차단" call="번호 끝 4402" reason="합성음 · 송금 요구" confirm="전화하지 않음" time="7월 12일"/></section></div>; }

function AdminPage() { return <div className="content-wide"><div className="page-heading admin-heading"><div><span className="eyebrow">SoriCall Admin</span><h1>서비스 운영 현황</h1><p>개인정보 원본은 노출하지 않고 운영 상태와 감사 기록만 제공합니다.</p></div><span className="status-pill"><i/> 모든 시스템 정상</span></div><section className="stat-grid admin-stats"><Stat icon={<CircleUserRound/>} value="1,284" label="통화 보호 사용자"/><Stat icon={<Activity/>} value="8,420" label="이번 달 분석 통화"/><Stat icon={<ShieldAlert/>} value="327" label="위험 통화 감지" tone="orange"/><Stat icon={<PhoneOff/>} value="86" label="고위험 차단" tone="red"/></section><section className="admin-grid"><div className="admin-card"><h3>서비스 상태</h3><SystemRow label="업무 API" value="정상"/><SystemRow label="AI 음성 분석" value="정상"/><SystemRow label="가족 알림 FCM" value="지연 2건" warn/><SystemRow label="Android 단말" value="1,118대 연결"/></div><div className="admin-card"><h3>오늘의 위험등급</h3><div className="donut"><span><b>241</b>분석 통화</span></div><div className="legend"><span><i className="green"/>안전 73%</span><span><i className="yellow"/>주의 18%</span><span><i className="red"/>위험 9%</span></div></div><div className="admin-card wide"><h3>최근 운영 알림</h3><CallRow tone="warn" icon={<Bell/>} title="FCM 알림 재시도 2건" meta="5분 전 · 자동 재시도 대기" badge="확인"/><CallRow tone="safe" icon={<Check/>} title="개인정보 자동 파기 완료" meta="오늘 02:00 · 184건" badge="완료"/></div></section></div>; }

function FormCard({ step, title, description, children }: { step?: string; title: string; description: string; children: React.ReactNode }) { return <div className="form-wrap"><div className="form-card">{step && <span className="step">{step}</span>}<h1>{title}</h1><p className="lead">{description}</p><div className="form-content">{children}</div></div></div>; }
function Field({ label, placeholder, type="text", suffix, value, onChange }: { label: string; placeholder: string; type?: string; suffix?: string; value?:string; onChange?:(value:string)=>void }) { return <label className="field"><span>{label}</span><div><input type={type} placeholder={placeholder} value={value} onChange={e => onChange?.(e.target.value)}/>{suffix && <button type="button">{suffix}</button>}</div></label>; }
function RelationGrid({ options, value, setValue }: { options: string[]; value: string; setValue: (v:string)=>void }) { return <div className="relation-grid">{options.map(o => <button key={o} className={o===value?"selected":""} onClick={() => setValue(o)}>{o===value && <Check/>}{o}</button>)}</div>; }
function InfoBox({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) { return <div className="info-box"><span>{icon}</span><p>{children}</p></div>; }
function Stat({ icon, value, label, tone="teal" }: { icon: React.ReactNode; value: string; label: string; tone?: string }) { return <div className={`stat ${tone}`}><span>{icon}</span><div><b>{value}</b><small>{label}</small></div></div>; }
function Ready({ icon,title,text }: {icon:React.ReactNode;title:string;text:string}) { return <div className="ready-card"><span>{icon}</span><div><b>{title}</b><small>{text}</small></div><CheckCircle2/></div>; }
function CallRow({tone,icon,title,meta,badge,onClick}:{tone:string;icon:React.ReactNode;title:string;meta:string;badge:string;onClick?:()=>void}) { return <button className="call-row" onClick={onClick}><span className={`call-icon ${tone}`}>{icon}</span><span><b>{title}</b><small>{meta}</small></span><em className={tone}>{badge}</em><ChevronRight/></button>; }
function CallStage({tone,icon,eyebrow,title,description,children}:{tone:string;icon:React.ReactNode;eyebrow:string;title:string;description:string;children:React.ReactNode}) { return <div className={`call-stage ${tone}`}><div className="call-stage-icon">{icon}<i/></div><span className="call-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p><div className="call-stage-body">{children}</div></div>; }
function HistoryRow({tone,status,call,reason,confirm,time}:{tone:string;status:string;call:string;reason:string;confirm:string;time:string}) { return <div className="table-row"><span><em className={tone}>{status}</em></span><b>{call}</b><span>{reason}</span><span>{confirm}</span><span>{time}</span></div>; }
function SystemRow({label,value,warn=false}:{label:string;value:string;warn?:boolean}) { return <div className="system-row"><span>{label}</span><b className={warn?"warn":""}><i/>{value}</b></div>; }
function NavItem({active,icon,label,onClick}:{active:boolean;icon:React.ReactNode;label:string;onClick:()=>void}) { return <button className={active?"active":""} onClick={onClick}>{icon}<span>{label}</span></button>; }

ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
