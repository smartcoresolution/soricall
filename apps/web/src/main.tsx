import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactDOM from "react-dom/client";
import QRCode from "qrcode";
import {
  Activity, AlertTriangle, ArrowLeft, Bell, Check, CheckCircle2, ChevronRight,
  CircleUserRound, ClipboardList, Clock3, Database, Download, FileClock, FileText, HeartHandshake, Home, LayoutDashboard, LockKeyhole, Mic,
  Pause, Phone, PhoneCall, PhoneOff, Play, Plus, Shield, ShieldAlert,
  Search, Trash2, UserPlus, UserRoundCheck, Users, Video, Volume2, X,
} from "lucide-react";
import { apiDelete, apiGet, apiPost, setApiAccessToken, type Family, type UserPublic } from "./api";
import "./styles.css";
import "./feedback.css";

type Screen =
  | "welcome" | "parentConnect" | "setupChoice" | "selfPhone" | "signup" | "consent" | "signupComplete" | "login" | "home" | "protected"
  | "contacts" | "deviceInvite" | "registrationPlan" | "invite" | "enrollmentStatus" | "enrollmentVerify" | "biometrics" | "normal" | "analysis" | "blocked"
  | "faceRegistration" | "parentAppInstall" | "enrollmentComplete" | "confirm" | "history" | "adminLogin" | "admin";

const familyRelations = ["친할아버지", "친할머니", "외할아버지", "외할머니", "아버지", "어머니", "배우자의 아버지", "배우자의 어머니", "기타"];
const contactRelations = ["아들", "딸", "손자", "손녀", "배우자", "기타 가족"];
const protectedRelationCodes: Record<string, string> = {
  친할아버지: "PATERNAL_GRANDFATHER", 친할머니: "PATERNAL_GRANDMOTHER",
  외할아버지: "MATERNAL_GRANDFATHER", 외할머니: "MATERNAL_GRANDMOTHER",
  아버지: "FATHER", 어머니: "MOTHER",
  "배우자의 아버지": "SPOUSE_FATHER", "배우자의 어머니": "SPOUSE_MOTHER", 기타: "OTHER",
};
const contactRelationCodes: Record<string, string> = { 아들: "SON", 딸: "DAUGHTER", 손자: "GRANDSON", 손녀: "GRANDDAUGHTER", 배우자: "SPOUSE", "기타 가족": "OTHER" };

type AuthResponse = { access_token: string; refresh_token: string; user: UserPublic; family_id?: string | null; senior_id?: string | null };
type ProtectedUserResponse = { id: string; name?: string; relation_code?: string; phone_number?: string | null; phone_number_last4?: string | null; protection_status?: string };
type RegisteredProtectedFamily = {
  id: string;
  name: string;
  relation: string;
  phoneLast4: string;
  phoneNumber?: string;
  status?: string;
};
type ConfirmationContactResponse = { id: string; name: string; relation_code?: string | null; phone_number_last4?: string | null; approval_status?: string; trust_level?: string; phoneNumber?: string };
type FamilyMemberView = { id: string; name: string; relation: string | null };
type VoiceProfileCreated = { id: string; status?: string };
type FaceProfileView = { id: string; status?: string };
type EnrollmentInvitation = {
  id: string;
  family_id: string;
  family_member_id: string;
  family_member_name: string;
  relation_code: string | null;
  phone_number_last4: string | null;
  channel: string;
  status: string;
  sent_at: string;
  expires_at: string;
  enrollment_url: string | null;
  member_approval_status: string;
  member_trust_level: string;
  phone_verified: boolean;
  requested_assets: string[];
  voice_deleted?: boolean;
  face_deleted?: boolean;
};
type DeviceEnrollment = { id: string; protected_user_id: string; protected_user_name: string; phone_number_last4: string | null; status: string; enrollment_url: string | null };
type AdminRow = Record<string, unknown> & { id?: string };
type AdminOverview = { metrics: Record<string, number>; seniors: AdminRow[]; family_members: AdminRow[]; calls: AdminRow[]; actions: AdminRow[]; confirmations: AdminRow[]; notifications: AdminRow[]; consents: AdminRow[]; admins: AdminRow[]; audits: AdminRow[] };
type RegistrationReadiness = { protectedUsers: number; contacts: number; voiceProfiles: number; faceProfiles: number };
const emptyAdminOverview = (): AdminOverview => ({ metrics: {}, seniors: [], family_members: [], calls: [], actions: [], confirmations: [], notifications: [], consents: [], admins: [], audits: [] });
const emptyReadiness = (): RegistrationReadiness => ({ protectedUsers: 0, contacts: 0, voiceProfiles: 0, faceProfiles: 0 });
const SESSION_STORAGE_KEY = "soricall.dev.session";
const ADMIN_SESSION_STORAGE_KEY = "soricall.admin.session";
type SetupMode = "self" | "helper";
const protectedRelationLabels = Object.fromEntries(Object.entries(protectedRelationCodes).map(([label, code]) => [code, label]));

function persistSession(session: AuthResponse | null): void {
  if (session) localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  else localStorage.removeItem(SESSION_STORAGE_KEY);
}

function storedSession(): AuthResponse | null {
  try {
    const value = localStorage.getItem(SESSION_STORAGE_KEY);
    return value ? JSON.parse(value) as AuthResponse : null;
  } catch {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

function storedAdminSession(): AuthResponse | null {
  try {
    const value = sessionStorage.getItem(ADMIN_SESSION_STORAGE_KEY);
    const saved = value ? JSON.parse(value) as AuthResponse : null;
    return saved?.user.role === "ADMIN" ? saved : null;
  } catch {
    sessionStorage.removeItem(ADMIN_SESSION_STORAGE_KEY);
    return null;
  }
}

function userMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message === "phone number already registered") return "이미 가입된 휴대전화 번호입니다.";
  if (message === "invalid phone number or password") return "휴대전화 번호 또는 비밀번호가 올바르지 않습니다.";
  if (message === "invalid admin credentials") return "관리자 ID 또는 비밀번호가 올바르지 않습니다.";
  if (message === "invalid phone verification code") return "인증번호가 올바르지 않습니다.";
  if (message === "phone verification expired") return "인증번호 유효시간이 지났습니다. 다시 받아 주세요.";
  if (message === "authentication required") return "로그인이 필요합니다.";
  if (message === "family access denied") return "이 가족 정보에 접근할 권한이 없습니다.";
  if (message === "phone number does not match invited family member") return "입력한 휴대전화 번호가 초대할 때 등록한 번호와 일치하지 않습니다. 문자 링크를 받은 본인의 번호를 다시 확인해 주세요. 번호가 일치하면 다음 단계에서 음성과 얼굴을 등록합니다.";
  if (message === "invitation expired") return "등록 링크의 유효기간이 지났습니다. 초대한 가족에게 새 링크를 요청해 주세요.";
  if (message === "invitation not found") return "유효하지 않은 등록 링크입니다.";
  return message || "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
}

const isValidMobilePhone = (value: string) => /^01[016789]-?\d{3,4}-?\d{4}$/.test(value.trim());

function initialScreenAfterLogin(
  protectedUsers: ProtectedUserResponse[],
  contacts: ConfirmationContactResponse[],
  invitations: EnrollmentInvitation[],
): Screen {
  const parentConnectionComplete = protectedUsers.some((item) => item.protection_status === "ACTIVE");
  const familyRegistrationComplete = contacts.some((item) => item.approval_status === "ACTIVE")
    || invitations.some((item) => item.status === "COMPLETED");
  return parentConnectionComplete || familyRegistrationComplete ? "home" : "setupChoice";
}

function openSmsComposer(phone: string, message: string): void {
  const recipient = phone.replace(/\D/g, "");
  if (/Android/i.test(navigator.userAgent)) {
    const body = encodeURIComponent(message);
    window.location.href = `intent:${recipient}#Intent;scheme=smsto;action=android.intent.action.SENDTO;launchFlags=0x40000000;S.sms_body=${body};end`;
    return;
  }
  window.location.href = `sms:${recipient}?body=${encodeURIComponent(message)}`;
}

function App() {
  const isAdminPath = /\/admin(?:\/login)?\/?$/.test(window.location.pathname);
  const initialAdminSession = isAdminPath ? storedAdminSession() : null;
  if (initialAdminSession) setApiAccessToken(initialAdminSession.access_token);
  const query = new URLSearchParams(window.location.search);
  const qrInvitationId = query.get("qr_invitation_id");
  const enrollmentToken = query.get("token") ?? query.get("qr_nonce");
  const enrollmentQuery = enrollmentToken
    ? `token=${encodeURIComponent(enrollmentToken)}${qrInvitationId ? `&qr_invitation_id=${encodeURIComponent(qrInvitationId)}` : ""}`
    : "";
  const tokenFromLink = query.get("device_token");
  if (tokenFromLink) window.localStorage.setItem("soricall_device_enrollment_token", tokenFromLink);
  const deviceToken = tokenFromLink ?? (query.get("resume_device_enrollment") === "1"
    ? window.localStorage.getItem("soricall_device_enrollment_token")
    : null);
  const missingResumeToken = query.get("resume_device_enrollment") === "1" && !deviceToken;
  const sessionRestoreStartedRef = useRef(false);
  const newSignupStartedRef = useRef(false);
  const [screen, setScreen] = useState<Screen>(isAdminPath ? (initialAdminSession ? "admin" : "adminLogin") : deviceToken ? "parentConnect" : enrollmentToken ? "enrollmentVerify" : "welcome");
  const [setupMode, setSetupMode] = useState<SetupMode>("helper");
  const [protectedRelation, setProtectedRelation] = useState("아버지");
  const [contactRelation, setContactRelation] = useState("딸");
  const [agreed, setAgreed] = useState([false, false, false, false, false]);
  const [analysisStep, setAnalysisStep] = useState(2);
  const [signup, setSignup] = useState({ name: "", phone: "", verificationId: "", verificationCode: "", verificationToken: "", password: "", passwordConfirm: "" });
  const [login, setLogin] = useState({ phone_number: "", password: "" });
  const [adminLogin, setAdminLogin] = useState({ admin_id: "", password: "" });
  const [protectedForm, setProtectedForm] = useState({ name: "", phone: "" });
  const [protectedFamilies, setProtectedFamilies] = useState<RegisteredProtectedFamily[]>([]);
  const [contactForm, setContactForm] = useState({ name: "", phone: "", primary: true });
  const [session, setSession] = useState<AuthResponse | null>(initialAdminSession);
  const [familyId, setFamilyId] = useState<string | null>(null);
  const [protectedUserId, setProtectedUserId] = useState<string | null>(null);
  const [enrollmentContact, setEnrollmentContact] = useState<ConfirmationContactResponse | null>(null);
  const [enrollmentContacts, setEnrollmentContacts] = useState<ConfirmationContactResponse[]>([]);
  const [invitations, setInvitations] = useState<EnrollmentInvitation[]>([]);
  const [parentInstallLink, setParentInstallLink] = useState("");
  const [busy, setBusy] = useState(false);
  const [apiError, setApiError] = useState("");
  const [apiMessage, setApiMessage] = useState("");
  const [invitePhone, setInvitePhone] = useState("");
  const [pendingVoiceEnrollment, setPendingVoiceEnrollment] = useState<{ audioRef: string; durationMs: number } | null>(null);
  const [registrationReadiness, setRegistrationReadiness] = useState<RegistrationReadiness>(emptyReadiness);

  const resetFamilyState = () => {
    setFamilyId(null);
    setProtectedUserId(null);
    setProtectedFamilies([]);
    setEnrollmentContact(null);
    setEnrollmentContacts([]);
    setInvitations([]);
    setParentInstallLink("");
    setRegistrationReadiness(emptyReadiness());
  };

  const loadRegistrationReadiness = async (
    protectedUsers: ProtectedUserResponse[],
    contacts: ConfirmationContactResponse[],
  ): Promise<void> => {
    const profileStates = await Promise.all(contacts.map(async (contact) => {
      const [voiceProfiles, faceProfiles] = await Promise.all([
        apiGet<VoiceProfileCreated[]>(`/api/v1/voice-profiles?family_member_id=${encodeURIComponent(contact.id)}`),
        apiGet<FaceProfileView[]>(`/api/v1/face-profiles?family_member_id=${encodeURIComponent(contact.id)}`),
      ]);
      return {
        voice: voiceProfiles.some((profile) => profile.status === "ENROLLED"),
        face: faceProfiles.some((profile) => profile.status === "ACTIVE"),
      };
    }));
    setRegistrationReadiness({
      protectedUsers: protectedUsers.length,
      contacts: contacts.length,
      voiceProfiles: profileStates.filter((state) => state.voice).length,
      faceProfiles: profileStates.filter((state) => state.face).length,
    });
  };

  useEffect(() => {
    if (window.location.protocol === "http:" && window.location.hostname === "175.118.124.67") {
      const secureUrl = new URL(window.location.href);
      secureUrl.protocol = "https:";
      secureUrl.hostname = "www.ansimsori.ai";
      secureUrl.port = "";
      window.location.replace(secureUrl.toString());
    }
  }, []);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, {
        scope: import.meta.env.BASE_URL,
        updateViaCache: "none",
      }).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (!enrollmentToken) return;
    setApiAccessToken(null);
    setBusy(true);
    apiGet<EnrollmentInvitation>(`/api/v1/enrollment-invitations/resolve?${enrollmentQuery}`)
      .then((invitation) => {
        setEnrollmentContact({ id: invitation.family_member_id, name: invitation.family_member_name });
        if (invitation.status === "COMPLETED") setScreen("enrollmentComplete");
        else if (invitation.status === "EXPIRED") throw new Error("invitation expired");
        else setScreen(invitation.phone_verified ? "biometrics" : "enrollmentVerify");
      })
      .catch((error) => setApiError(userMessage(error)))
      .finally(() => setBusy(false));
  }, [enrollmentToken, enrollmentQuery]);

  useEffect(() => {
    if (enrollmentToken || isAdminPath) return;
    if (sessionRestoreStartedRef.current) return;
    sessionRestoreStartedRef.current = true;
    const saved = storedSession();
    if (!saved?.refresh_token) return;
    setBusy(true);
    apiPost<AuthResponse>("/api/v1/auth/refresh", { refresh_token: saved.refresh_token })
      .then((refreshed) => {
        if (newSignupStartedRef.current) return;
        setApiAccessToken(refreshed.access_token);
        persistSession(refreshed);
        setSession(refreshed);
      })
      .catch(() => {
        if (newSignupStartedRef.current) return;
        persistSession(null);
        setApiAccessToken(null);
      })
      .finally(() => setBusy(false));
  }, [enrollmentToken, isAdminPath]);

  useEffect(() => {
    if (!session || enrollmentToken) return;
    let cancelled = false;
    const restoreFamilyState = async () => {
      try {
        const families = await apiGet<Family[]>("/api/v1/families");
        const family = families[0];
        if (!family) {
          if (!cancelled) {
            resetFamilyState();
            setScreen("setupChoice");
          }
          return;
        }
        if (cancelled) return;
        const protectedUsers = await apiGet<ProtectedUserResponse[]>(`/api/v1/families/${family.id}/protected-call-users`);
        const protectedUser = protectedUsers[0];
        const [contacts, restoredInvitations] = await Promise.all([
          protectedUser ? apiGet<ConfirmationContactResponse[]>(`/api/v1/families/${family.id}/protected-call-users/${protectedUser.id}/confirmation-contacts`) : Promise.resolve([]),
          apiGet<EnrollmentInvitation[]>(`/api/v1/families/${family.id}/enrollment-invitations`),
        ]);
        if (cancelled) return;
        setFamilyId(family.id);
        setProtectedUserId(protectedUser?.id ?? null);
        setProtectedFamilies(protectedUsers.map((item) => ({
          id: item.id,
          name: item.name ?? "보호 가족",
          relation: protectedRelationLabels[item.relation_code ?? ""] ?? "기타",
          phoneLast4: item.phone_number_last4 ?? "----",
          phoneNumber: item.phone_number ?? undefined,
          status: item.protection_status,
        })));
        setEnrollmentContacts(contacts);
        setInvitations(restoredInvitations);
        await loadRegistrationReadiness(protectedUsers, contacts);
        setScreen(initialScreenAfterLogin(protectedUsers, contacts, restoredInvitations));
      } catch (error) {
        if (!cancelled) setApiError(userMessage(error));
      }
    };
    void restoreFamilyState();
    return () => { cancelled = true; };
  }, [session, enrollmentToken]);

  useEffect(() => {
    if (screen !== "enrollmentStatus" || !familyId || !session) return;
    const reloadInvitations = () => {
      apiGet<EnrollmentInvitation[]>(`/api/v1/families/${familyId}/enrollment-invitations`)
        .then((restored) => setInvitations((current) => restored.map((item) => ({
          ...item,
          enrollment_url: current.find((existing) => existing.id === item.id)?.enrollment_url ?? item.enrollment_url,
        }))))
        .catch((error) => setApiError(userMessage(error)));
    };
    reloadInvitations();
    const intervalId = window.setInterval(reloadInvitations, 5000);
    return () => window.clearInterval(intervalId);
  }, [screen, familyId, session]);

  useEffect(() => {
    if (screen !== "parentAppInstall" || !familyId || !session) return;
    const reload = () => apiGet<ProtectedUserResponse[]>(`/api/v1/families/${familyId}/protected-call-users`).then((users) => {
      setProtectedFamilies((current) => users.map((item) => ({
        id: item.id,
        name: item.name ?? "보호 가족",
        relation: protectedRelationLabels[item.relation_code ?? ""] ?? "기타",
        phoneLast4: item.phone_number_last4 ?? "----",
        phoneNumber: item.phone_number ?? current.find((existing) => existing.id === item.id)?.phoneNumber,
        status: item.protection_status,
      })));
    }).catch(() => undefined);
    reload();
    const interval = window.setInterval(reload, 5000);
    return () => window.clearInterval(interval);
  }, [screen, familyId, session]);

  const runApi = async (action: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setApiError(""); setApiMessage("");
    try { await action(); } catch (error) { setApiError(userMessage(error)); }
    finally { setBusy(false); }
  };

  const startNewSignup = () => {
    newSignupStartedRef.current = true;
    persistSession(null);
    setApiAccessToken(null);
    setSession(null);
    resetFamilyState();
    setSignup({ name: "", phone: "", verificationId: "", verificationCode: "", verificationToken: "", password: "", passwordConfirm: "" });
    setLogin({ phone_number: "", password: "" });
    setAgreed([false, false, false, false, false]);
    setProtectedForm({ name: "", phone: "" });
    setContactForm({ name: "", phone: "", primary: true });
    setProtectedRelation("아버지");
    setContactRelation("딸");
    setApiError("");
    setApiMessage("");
    setScreen("signup");
  };

  const register = () => runApi(async () => {
    if (signup.password !== signup.passwordConfirm) throw new Error("비밀번호 확인이 일치하지 않습니다.");
    let auth: AuthResponse;
    try {
      auth = await apiPost<AuthResponse>("/api/v1/auth/register", { phone_number: signup.phone, verification_token: signup.verificationToken, password: signup.password, display_name: signup.name, role: "SENIOR" });
    } catch (error) {
      if (error instanceof Error && error.message === "phone number already registered") {
        setLogin({ phone_number: signup.phone, password: "" });
        setScreen("login");
        return;
      }
      throw error;
    }
    resetFamilyState();
    setFamilyId(auth.family_id ?? null);
    setProtectedUserId(auth.senior_id ?? null);
    setApiAccessToken(auth.access_token); persistSession(auth); setSession(auth); setScreen("signupComplete");
  });
  const sendSignupCode = () => runApi(async () => {
    const result = await apiPost<{ verification_id: string; development_code?: string | null }>("/api/v1/auth/phone-verifications", { phone_number: signup.phone });
    setSignup((current) => ({ ...current, verificationId: result.verification_id, verificationCode: result.development_code ?? "", verificationToken: "" }));
    setApiMessage(result.development_code ? `개발용 인증번호: ${result.development_code}` : "인증번호를 문자로 보냈습니다.");
  });
  const confirmSignupCode = () => runApi(async () => {
    const result = await apiPost<{ verification_token: string }>("/api/v1/auth/phone-verifications/confirm", { verification_id: signup.verificationId, code: signup.verificationCode });
    setSignup((current) => ({ ...current, verificationToken: result.verification_token }));
    setApiMessage("휴대전화 인증이 완료됐습니다.");
  });
  const signIn = () => runApi(async () => {
    const auth = await apiPost<AuthResponse>("/api/v1/auth/login", login);
    resetFamilyState();
    setApiAccessToken(auth.access_token); persistSession(auth); setSession(auth);
    const families = await apiGet<Family[]>("/api/v1/families");
    const family = families[0];
    if (!family) {
      setFamilyId(auth.family_id ?? null);
      setProtectedUserId(auth.senior_id ?? null);
      setScreen("setupChoice");
      return;
    }
    const protectedUsers = await apiGet<ProtectedUserResponse[]>(`/api/v1/families/${family.id}/protected-call-users`);
    const protectedUser = protectedUsers[0];
    const [contacts, restoredInvitations] = await Promise.all([
      protectedUser
        ? apiGet<ConfirmationContactResponse[]>(`/api/v1/families/${family.id}/protected-call-users/${protectedUser.id}/confirmation-contacts`)
        : Promise.resolve([]),
      apiGet<EnrollmentInvitation[]>(`/api/v1/families/${family.id}/enrollment-invitations`),
    ]);
    setFamilyId(family.id);
    setProtectedUserId(protectedUser?.id ?? null);
    setProtectedFamilies(protectedUsers.map((item) => ({
      id: item.id,
      name: item.name ?? "보호 가족",
      relation: protectedRelationLabels[item.relation_code ?? ""] ?? "기타",
      phoneLast4: item.phone_number_last4 ?? "----",
      phoneNumber: item.phone_number ?? undefined,
      status: item.protection_status,
    })));
    setEnrollmentContacts(contacts);
    setInvitations(restoredInvitations);
    await loadRegistrationReadiness(protectedUsers, contacts);
    setScreen(initialScreenAfterLogin(protectedUsers, contacts, restoredInvitations));
  });
  const signInAdmin = () => runApi(async () => {
    const auth = await apiPost<AuthResponse>("/api/v1/auth/admin/login", adminLogin);
    if (auth.user.role !== "ADMIN") throw new Error("관리자 권한이 없는 계정입니다.");
    sessionStorage.setItem(ADMIN_SESSION_STORAGE_KEY, JSON.stringify(auth));
    setApiAccessToken(auth.access_token);
    setSession(auth);
    window.history.replaceState({}, "", `${import.meta.env.BASE_URL}admin`);
    setScreen("admin");
  });
  const signOutAdmin = () => {
    sessionStorage.removeItem(ADMIN_SESSION_STORAGE_KEY);
    setApiAccessToken(null);
    setSession(null);
    setAdminLogin({ admin_id: "", password: "" });
    setApiError("");
    window.history.replaceState({}, "", `${import.meta.env.BASE_URL}admin/login`);
    setScreen("adminLogin");
  };
  const openNextRegistrationStep = async (member: { id: string; name: string }) => {
    setEnrollmentContact(member);
    const [voiceProfiles, faceProfiles] = await Promise.all([
      apiGet<VoiceProfileCreated[]>(`/api/v1/voice-profiles?family_member_id=${encodeURIComponent(member.id)}`),
      apiGet<FaceProfileView[]>(`/api/v1/face-profiles?family_member_id=${encodeURIComponent(member.id)}`),
    ]);
    const voiceRegistered = voiceProfiles.some((profile) => profile.status === "ENROLLED");
    const faceRegistered = faceProfiles.some((profile) => profile.status === "ACTIVE");
    if (voiceRegistered && faceRegistered) setScreen("parentAppInstall");
    else if (voiceRegistered) setScreen("faceRegistration");
    else setScreen("biometrics");
  };
  const openHelperProtection = () => runApi(async () => {
    if (!session) throw new Error("먼저 회원가입 또는 로그인이 필요합니다.");
    setSetupMode("helper");
    const families = await apiGet<Family[]>("/api/v1/families");
    const accessibleFamilyIds = new Set(families.map((family) => family.id));
    let currentFamilyId = familyId && accessibleFamilyIds.has(familyId) ? familyId : (families[0]?.id ?? null);
    if (currentFamilyId !== familyId) setFamilyId(currentFamilyId);
    if (!currentFamilyId) {
      setScreen("protected");
      return;
    }
    const allProtectedUsers = await apiGet<ProtectedUserResponse[]>(`/api/v1/families/${currentFamilyId}/protected-call-users`);
    const protectedUsers = allProtectedUsers.filter((item) => item.relation_code !== "SELF");
    if (protectedUsers.length === 0) {
      setProtectedFamilies([]);
      setScreen("protected");
      return;
    }
    setProtectedFamilies(protectedUsers.map((item) => ({
      id: item.id,
      name: item.name ?? "보호 가족",
      relation: protectedRelationLabels[item.relation_code ?? ""] ?? "기타",
      phoneLast4: item.phone_number_last4 ?? "----",
      phoneNumber: item.phone_number ?? undefined,
      status: item.protection_status,
    })));
    const members = await apiGet<FamilyMemberView[]>(`/api/v1/families/${currentFamilyId}/members`);
    let selfMember = members.find((member) => member.relation === "SELF");
    if (!selfMember) {
      const selfPhone = session.user.phone_number ?? signup.phone;
      selfMember = await apiPost<FamilyMemberView>(`/api/v1/families/${currentFamilyId}/members`, {
        name: session.user.display_name,
        phone_number: selfPhone,
        relation: "SELF",
        user_id: session.user.id,
      });
    }
    setProtectedUserId(protectedUsers[0].id);
    await openNextRegistrationStep({ id: selfMember.id, name: selfMember.name });
  });
  const chooseProtectionMode = (mode: SetupMode) => runApi(async () => {
    if (!session) throw new Error("먼저 회원가입 또는 로그인이 필요합니다.");
    setSetupMode(mode);
    if (mode === "self" && session.family_id && session.senior_id) {
      setFamilyId(session.family_id);
      setProtectedUserId(session.senior_id);
      const [contacts, restoredInvitations] = await Promise.all([
        apiGet<ConfirmationContactResponse[]>(`/api/v1/families/${session.family_id}/protected-call-users/${session.senior_id}/confirmation-contacts`),
        apiGet<EnrollmentInvitation[]>(`/api/v1/families/${session.family_id}/enrollment-invitations`),
      ]);
      const contactIds = new Set(contacts.map((contact) => contact.id));
      setEnrollmentContacts(contacts);
      setInvitations(restoredInvitations.filter((invitation) => contactIds.has(invitation.family_member_id)));
      setContactForm({ name: "", phone: "", primary: true });
      setContactRelation("아들");
      setScreen("contacts");
      return;
    }
    let currentFamilyId = familyId;
    if (!currentFamilyId) {
      const family = await apiPost<Family>("/api/v1/families", { name: `${session.user.display_name}님의 통화보호 가족` });
      currentFamilyId = family.id; setFamilyId(family.id);
    }
    const selfPhone = session.user.phone_number ?? signup.phone;
    if (mode === "self" && !isValidMobilePhone(selfPhone)) throw new Error("본인 휴대전화 번호가 필요합니다. 회원정보에서 휴대전화 번호를 먼저 등록해 주세요.");
    const member = await apiPost<ProtectedUserResponse>(`/api/v1/families/${currentFamilyId}/protected-call-users`, {
      name: mode === "self" ? session.user.display_name : protectedForm.name,
      phone_number: mode === "self" ? selfPhone : protectedForm.phone,
      relation_code: mode === "self" ? "SELF" : (protectedRelationCodes[protectedRelation] ?? "OTHER"),
      user_id: mode === "self" ? session.user.id : undefined,
    });
    setProtectedUserId(member.id);
    if (mode === "self") {
      setEnrollmentContacts([]);
      setContactForm({ name: "", phone: "", primary: true });
      setContactRelation("아들");
      setScreen("contacts");
      return;
    }
    const selfMember = await apiPost<ConfirmationContactResponse>(`/api/v1/families/${currentFamilyId}/members`, {
      name: session.user.display_name,
      phone_number: selfPhone,
      relation: "SELF",
      user_id: session.user.id,
    });
    await openNextRegistrationStep(selfMember);
  });
  const addProtectedFamily = () => runApi(async () => {
    if (!session) throw new Error("먼저 회원가입 또는 로그인이 필요합니다.");
    if (protectedFamilies.some((item) => item.phoneLast4 === protectedForm.phone.replace(/\D/g, "").slice(-4) && item.name === protectedForm.name.trim())) {
      throw new Error("이미 추가한 가족입니다.");
    }
    let currentFamilyId = familyId;
    if (!currentFamilyId) {
      const family = await apiPost<Family>("/api/v1/families", { name: `${session.user.display_name}님의 통화보호 가족` });
      currentFamilyId = family.id;
      setFamilyId(family.id);
    }
    const member = await apiPost<ProtectedUserResponse>(`/api/v1/families/${currentFamilyId}/protected-call-users`, {
      name: protectedForm.name.trim(),
      phone_number: protectedForm.phone,
      relation_code: protectedRelationCodes[protectedRelation] ?? "OTHER",
    });
    setProtectedFamilies((current) => [...current, {
      id: member.id,
      name: protectedForm.name.trim(),
      relation: protectedRelation,
      phoneLast4: protectedForm.phone.replace(/\D/g, "").slice(-4),
      phoneNumber: protectedForm.phone,
      status: "PREPARING",
    }]);
    setProtectedForm({ name: "", phone: "" });
    setApiMessage(`${protectedRelation} 가족을 추가했습니다.`);
  });
  const removeProtectedFamily = (family: RegisteredProtectedFamily) => {
    if (!window.confirm(`${family.name}님을 보호 대상에서 삭제할까요?`)) return;
    void runApi(async () => {
      if (!familyId) throw new Error("가족 정보가 없습니다.");
      await apiDelete(`/api/v1/families/${familyId}/protected-call-users/${family.id}`);
      setProtectedFamilies((current) => current.filter((item) => item.id !== family.id));
      if (protectedUserId === family.id) setProtectedUserId(null);
      setApiMessage(`${family.name}님을 보호 대상에서 삭제했습니다.`);
    });
  };
  const finishProtectedFamilies = () => runApi(async () => {
    if (!session || !familyId || protectedFamilies.length === 0) throw new Error("보호할 가족을 한 명 이상 추가해 주세요.");
    const members = await apiGet<FamilyMemberView[]>(`/api/v1/families/${familyId}/members`);
    let selfMember = members.find((member) => member.relation === "SELF");
    if (!selfMember) {
      const selfPhone = session.user.phone_number ?? signup.phone;
      selfMember = await apiPost<FamilyMemberView>(`/api/v1/families/${familyId}/members`, {
        name: session.user.display_name,
        phone_number: selfPhone,
        relation: "SELF",
        user_id: session.user.id,
      });
    }
    await openNextRegistrationStep({ id: selfMember.id, name: selfMember.name });
  });
  const saveContact = () => runApi(async () => {
    if (!familyId || !protectedUserId) throw new Error("보호받을 가족을 먼저 등록해 주세요.");
    const contact = await apiPost<ConfirmationContactResponse>(`/api/v1/families/${familyId}/protected-call-users/${protectedUserId}/confirmation-contacts`, { name: contactForm.name, phone_number: contactForm.phone, relation_code: contactRelationCodes[contactRelation], is_primary_contact: contactForm.primary, notification_priority: 1, notify_enabled: true });
    const contactWithPhone = { ...contact, phoneNumber: contactForm.phone };
    setEnrollmentContact(contactWithPhone);
    setEnrollmentContacts((current) => [...current, contactWithPhone]);
    setContactForm({ name: "", phone: "", primary: false });
    setContactRelation("아들");
    setApiMessage("확인 가족을 추가했습니다.");
  });
  const finishContacts = () => {
    if (enrollmentContacts.length === 0) {
      setApiError("확인 가족을 한 명 이상 추가해 주세요.");
      return;
    }
    setApiError("");
    setApiMessage("");
    setScreen("registrationPlan");
  };
  const removeContact = (contact: ConfirmationContactResponse) => {
    if (!window.confirm(`${contact.name}님을 확인 가족에서 삭제할까요?`)) return;
    void runApi(async () => {
      if (!familyId || !protectedUserId) throw new Error("가족 정보가 없습니다.");
      await apiDelete(`/api/v1/families/${familyId}/protected-call-users/${protectedUserId}/confirmation-contacts/${contact.id}`);
      setEnrollmentContacts((current) => current.filter((item) => item.id !== contact.id));
      setInvitations((current) => current.filter((item) => item.family_member_id !== contact.id));
      if (enrollmentContact?.id === contact.id) setEnrollmentContact(null);
      setApiMessage(`${contact.name}님을 확인 가족에서 삭제했습니다.`);
    });
  };
  const removeRegisteredAsset = (invitation: EnrollmentInvitation, asset: "voice" | "face") => {
    const label = asset === "voice" ? "음성" : "얼굴";
    if (!window.confirm(`${invitation.family_member_name}님의 ${label} 등록정보를 삭제할까요? 삭제 후 다시 등록할 수 있습니다.`)) return;
    void runApi(async () => {
      const profiles = asset === "voice"
        ? await apiGet<VoiceProfileCreated[]>(`/api/v1/voice-profiles?family_member_id=${encodeURIComponent(invitation.family_member_id)}`)
        : await apiGet<FaceProfileView[]>(`/api/v1/face-profiles?family_member_id=${encodeURIComponent(invitation.family_member_id)}`);
      const activeProfiles = profiles.filter((profile) => profile.status !== "DELETED");
      await Promise.all(activeProfiles.map((profile) => apiDelete(
        asset === "voice" ? `/api/v1/voice-profiles/${profile.id}` : `/api/v1/face-profiles/${profile.id}`,
      )));
      setInvitations((current) => current.map((item) => item.id === invitation.id
        ? { ...item, [asset === "voice" ? "voice_deleted" : "face_deleted"]: true }
        : item));
      setApiMessage(`${invitation.family_member_name}님의 ${label} 등록정보를 삭제했습니다.`);
    });
  };
  const phoneForContact = (contact: ConfirmationContactResponse): string => {
    const phone = contact.phoneNumber ?? window.prompt(
      `${contact.name}님의 휴대전화 번호 전체를 입력해 주세요. (끝 ${contact.phone_number_last4 ?? "----"})`,
      "010-",
    ) ?? "";
    if (!isValidMobilePhone(phone)) throw new Error(`${contact.name}님의 올바른 휴대전화 번호가 필요합니다.`);
    setEnrollmentContacts((current) => current.map((item) => item.id === contact.id ? { ...item, phoneNumber: phone } : item));
    return phone;
  };
  const sendEnrollmentInvitation = (contact: ConfirmationContactResponse, channel: "LINK" | "QR" | "DIRECT" = "LINK") => runApi(async () => {
    if (!familyId) throw new Error("가족 정보가 없습니다.");
    const phone = channel === "LINK" ? phoneForContact(contact) : "";
    const sent = await apiPost<EnrollmentInvitation>(`/api/v1/families/${familyId}/members/${contact.id}/enrollment-invitations?channel=${channel}`, {});
    setInvitations((current) => [
      ...current.filter((item) => item.family_member_id !== sent.family_member_id),
      sent,
    ]);
    setScreen("enrollmentStatus");
    if (channel === "LINK") {
      if (!sent.enrollment_url) throw new Error("등록 링크를 만들지 못했습니다.");
      const url = new URL(sent.enrollment_url, window.location.origin).toString();
      setApiMessage("문자 앱을 열었습니다. 내용을 확인하고 전송 버튼을 눌러 주세요.");
      openSmsComposer(phone, `[SoriCall] ${contact.name}님 가족 등록 요청\n아래 링크에서 본인 동의 후 음성과 얼굴을 등록해 주세요.\n${url}`);
    }
  });
  const resendInvitation = (invitation: EnrollmentInvitation) => runApi(async () => {
    if (!familyId) throw new Error("가족 정보가 없습니다.");
    const contact = enrollmentContacts.find((item) => item.id === invitation.family_member_id) ?? {
      id: invitation.family_member_id,
      name: invitation.family_member_name,
      phone_number_last4: invitation.phone_number_last4,
    };
    const phone = phoneForContact(contact);
    const resent = await apiPost<EnrollmentInvitation>(`/api/v1/families/${familyId}/enrollment-invitations/${invitation.id}/resend`, {});
    setInvitations((current) => current.map((item) => item.id === invitation.id ? resent : item));
    if (!resent.enrollment_url) throw new Error("등록 링크를 다시 만들지 못했습니다.");
    const url = new URL(resent.enrollment_url, window.location.origin).toString();
    setApiMessage("새 링크로 문자 앱을 열었습니다. 전송 버튼을 눌러 주세요.");
    openSmsComposer(phone, `[SoriCall] ${invitation.family_member_name}님 가족 등록 요청\n새 등록 링크를 보내드립니다.\n${url}`);
  });
  const approveEnrollment = (invitation: EnrollmentInvitation) => runApi(async () => {
    if (!familyId || !protectedUserId) throw new Error("보호 대상 정보가 없습니다.");
    await apiPost(
      `/api/v1/families/${familyId}/protected-call-users/${protectedUserId}/confirmation-contacts/${invitation.family_member_id}/approve`,
      {},
    );
    setInvitations((current) => current.map((item) => item.id === invitation.id
      ? { ...item, member_approval_status: "ACTIVE" }
      : item));
    setApiMessage(`${invitation.family_member_name}님을 확인 가족으로 승인했습니다.`);
  });
  const verifyInvitePhone = () => runApi(async () => {
    if (!enrollmentToken) throw new Error("초대 정보가 없습니다.");
    await apiPost<EnrollmentInvitation>(
      `/api/v1/enrollment-invitations/phone-check?${enrollmentQuery}`,
      { phone_number: invitePhone },
    );
    setScreen("biometrics");
  });
  const saveBiometrics = (audioRef: string, durationMs: number, faceImageRef: string | null) => runApi(async () => {
    if (!enrollmentContact) throw new Error("음성을 등록할 확인 가족 정보가 없습니다.");
    if (enrollmentToken) {
      setPendingVoiceEnrollment({ audioRef, durationMs });
      setScreen("faceRegistration");
      return;
    }
    const profile = await apiPost<VoiceProfileCreated>("/api/v1/voice-profiles", {
      family_member_id: enrollmentContact.id,
      display_name: enrollmentContact.name,
    });
    await apiPost(`/api/v1/voice-profiles/${profile.id}/samples`, {
      audio_ref: audioRef,
      duration_ms: durationMs,
      mime_type: "audio/webm",
      purpose: "ENROLLMENT",
    });
    await apiPost(`/api/v1/voice-profiles/${profile.id}/enroll`, { audio_ref: audioRef });
    if (faceImageRef) {
      await apiPost("/api/v1/face-profiles", {
        family_member_id: enrollmentContact.id,
        display_name: enrollmentContact.name,
        image_ref: faceImageRef,
        consent_accepted: true,
      });
    }
    setInvitations((current) => current.map((item) => item.family_member_id === enrollmentContact.id ? { ...item, status: "COMPLETED" } : item));
    setScreen("faceRegistration");
  });
  const saveFaceRegistration = (faceImageRef: string | null) => runApi(async () => {
    if (!enrollmentContact) throw new Error("얼굴을 등록할 가족 정보가 없습니다.");
    if (enrollmentToken) {
      if (!pendingVoiceEnrollment) throw new Error("먼저 음성을 녹음해 주세요.");
      if (!faceImageRef) throw new Error("얼굴 사진을 촬영해 주세요.");
      await apiPost<EnrollmentInvitation>(`/api/v1/enrollment-invitations/complete?${enrollmentQuery}`, {
        audio_ref: pendingVoiceEnrollment.audioRef,
        duration_ms: pendingVoiceEnrollment.durationMs,
        mime_type: "audio/webm",
        face_image_ref: faceImageRef,
        consent_accepted: true,
      });
      setPendingVoiceEnrollment(null);
      setScreen("enrollmentComplete");
      return;
    }
    if (faceImageRef) {
      await apiPost("/api/v1/face-profiles", {
        family_member_id: enrollmentContact.id,
        display_name: enrollmentContact.name,
        image_ref: faceImageRef,
        consent_accepted: true,
      });
    }
    setScreen("parentAppInstall");
  });
  const shareParentInstall = async (family: RegisteredProtectedFamily) => {
    if (!familyId) throw new Error("가족 정보가 없습니다.");
    const phone = family.phoneNumber ?? window.prompt(
      `${family.name}님의 등록된 휴대전화 번호 전체를 입력해 주세요. (끝 ${family.phoneLast4})`,
      "010-",
    );
    if (phone === null) return;
    if (!isValidMobilePhone(phone)) throw new Error("올바른 휴대전화 번호를 입력해 주세요.");
    const enrollment = await apiPost<DeviceEnrollment>(
      `/api/v1/families/${familyId}/protected-call-users/${family.id}/device-enrollment`,
      { phone_number: phone },
    );
    const connectionUrl = enrollment.enrollment_url ?? "";
    if (!connectionUrl) throw new Error("연결 링크를 만들지 못했습니다.");
    const message = [
      `[SoriCall] ${family.name}님 통화 보호 연결 안내`,
      "아래 링크를 눌러 앱 설치와 연결을 순서대로 진행해 주세요.",
      connectionUrl,
    ].join("\n");
    setApiMessage("문자 앱을 열었습니다. 내용을 확인하고 전송 버튼을 눌러 주세요.");
    openSmsComposer(phone, message);
  };
  const title = useMemo(() => ({
    parentConnect: "부모님 통화 보호 연결", setupChoice: "보호 방법 선택", selfPhone: "본인 휴대전화 확인", signup: "회원가입", consent: "서비스 이용 동의", signupComplete: "가입 완료", login: "로그인",
    protected: "가족 등록", contacts: "확인 가족 등록", deviceInvite: "부모님 앱 연결", registrationPlan: "등록 항목 안내", invite: "등록 요청 보내기",
    enrollmentStatus: "가족 등록 현황", enrollmentVerify: "초대 가족 본인 확인", biometrics: setupMode === "helper" ? "자녀 음성 등록" : "가족 본인 등록", faceRegistration: "얼굴 등록", parentAppInstall: "부모님 앱 설치", enrollmentComplete: "등록 완료", normal: "안전한 전화", analysis: "의심전화 분석",
    blocked: "고위험 전화 차단", confirm: "가족 확인 요청", history: "통화기록",
    adminLogin: "관리자 로그인", admin: "관리자 페이지", home: "통화 보호 홈", welcome: "",
  }[screen]), [screen]);

  const goBack = () => {
    const previous: Partial<Record<Screen, Screen>> = {
      signup: "welcome",
      login: "welcome",
      consent: "signup",
      setupChoice: "login",
      selfPhone: "setupChoice",
      protected: "setupChoice",
      contacts: "setupChoice",
      deviceInvite: "setupChoice",
      registrationPlan: "contacts",
      invite: "registrationPlan",
      enrollmentStatus: "invite",
      biometrics: setupMode === "helper" ? "protected" : "contacts",
      faceRegistration: "biometrics",
      parentAppInstall: "faceRegistration",
      normal: "home",
      analysis: "home",
      blocked: "analysis",
      confirm: "blocked",
      history: "home",
      admin: "home",
    };
    setApiError("");
    setApiMessage("");
    setScreen(previous[screen] ?? "welcome");
  };

  const goWelcome = () => {
    window.history.replaceState({}, "", import.meta.env.BASE_URL);
    setApiError("");
    setApiMessage("");
    setScreen("welcome");
  };

  const goServiceHome = () => {
    setApiError("");
    setApiMessage("");
    if (session && !enrollmentToken) {
      setScreen("home");
      return;
    }
    goWelcome();
  };

  const closeEnrollmentWindow = () => {
    window.open("", "_self");
    window.close();
    window.setTimeout(() => {
      if (window.closed) return;
      if (window.history.length > 1) window.history.back();
    }, 200);
  };

  const openRegistrationManagement = () => {
    setApiError("");
    setApiMessage("");
    if (registrationReadiness.protectedUsers === 0) {
      setScreen("setupChoice");
    } else if (registrationReadiness.contacts === 0) {
      setScreen("contacts");
    } else if (
      registrationReadiness.voiceProfiles < registrationReadiness.contacts
      || registrationReadiness.faceProfiles < registrationReadiness.contacts
    ) {
      setScreen("registrationPlan");
    } else {
      setScreen("enrollmentStatus");
    }
  };

  if (screen === "adminLogin") {
    return <AdminLoginPage value={adminLogin} setValue={setAdminLogin} error={apiError} busy={busy} onSubmit={signInAdmin} onService={() => { window.location.href = import.meta.env.BASE_URL; }} />;
  }

  if (screen === "admin") {
    return <div className="admin-desktop-shell"><main className="admin-desktop-main"><AdminPage isAdmin={session?.user.role === "ADMIN"} adminName={session?.user.display_name || "관리자"} onLogout={signOutAdmin}/></main></div>;
  }

  return (
    <div className="site-shell">
      {screen !== "welcome" && screen !== "enrollmentComplete" && <header className="topbar">
        <button className="brand" onClick={goWelcome}>
          <span className="brand-mark"><Shield size={22} /></span>
          <span>SoriCall<small>안심소리 가족콜</small></span>
        </button>
        <div className="top-title">{title}</div>
        <div className="top-actions">
          <button className="screen-home-button" onClick={goServiceHome}><Home size={19} /> 홈</button>
        </div>
      </header>}

      <main className={`page ${screen === "welcome" ? "welcome-page" : ""}`}>
        {screen !== "welcome" && screen !== "home" && screen !== "signupComplete" && screen !== "enrollmentComplete" && screen !== "enrollmentStatus" && (
          <button className="back-button" onClick={goBack}><ArrowLeft size={18} /> 이전</button>
        )}
        {screen === "welcome" && (missingResumeToken
          ? <ResumeDeviceEnrollmentMissing />
          : <Welcome onSignup={startNewSignup} onLogin={() => { setApiError(""); setScreen("login"); }} />)}
        {screen === "parentConnect" && deviceToken && <ParentDeviceConnect token={deviceToken} />}
        {screen === "setupChoice" && <SetupChoice onSelect={(mode) => { setSetupMode(mode); if (mode === "self") { const phone = session?.user.phone_number ?? signup.phone; if (isValidMobilePhone(phone)) chooseProtectionMode("self"); else { setApiError(""); setScreen("selfPhone"); } } else void openHelperProtection(); }} />}
        {screen === "selfPhone" && <SelfPhone value={signup.phone} setValue={(phone) => setSignup((current) => ({ ...current, phone }))} onNext={() => chooseProtectionMode("self")} />}
        {screen === "signup" && <Signup value={signup} setValue={setSignup} onSendCode={sendSignupCode} onConfirmCode={confirmSignupCode} onNext={() => setScreen("consent")} busy={busy} />}
        {screen === "consent" && <Consent agreed={agreed} setAgreed={setAgreed} onNext={register} error={apiError} onClearError={() => setApiError("")} busy={busy} />}
        {screen === "signupComplete" && <SignupComplete onNext={() => { setLogin({ phone_number: signup.phone, password: "" }); setScreen("login"); }} />}
        {screen === "login" && <Login value={login} setValue={setLogin} onNext={signIn} error={apiError} onClearError={() => setApiError("")} />}
        {screen === "protected" && <FamilyRegistration value={protectedForm} setValue={setProtectedForm} relation={protectedRelation} setRelation={setProtectedRelation} families={protectedFamilies} onAdd={addProtectedFamily} onDelete={removeProtectedFamily} onNext={finishProtectedFamilies} busy={busy} />}
        {screen === "contacts" && <ContactRegistration value={contactForm} setValue={setContactForm} relation={contactRelation} setRelation={setContactRelation} contacts={enrollmentContacts} onAdd={saveContact} onDelete={removeContact} onNext={finishContacts} busy={busy} />}
        {screen === "deviceInvite" && <DeviceInvite familyName={protectedForm.name} link={parentInstallLink} onNext={() => setScreen("contacts")} />}
        {screen === "registrationPlan" && <RegistrationPlan contacts={enrollmentContacts} onNext={() => setScreen("invite")} />}
        {screen === "invite" && <EnrollmentInvite contacts={enrollmentContacts} onSend={sendEnrollmentInvitation} />}
        {screen === "enrollmentStatus" && <EnrollmentStatus invitations={invitations} onResend={resendInvitation} onApprove={approveEnrollment} onDeleteAsset={removeRegisteredAsset} onDeleteFamily={(invitation) => removeContact({ id: invitation.family_member_id, name: invitation.family_member_name })} />}
        {screen === "enrollmentVerify" && <EnrollmentPhoneVerification phone={invitePhone} setPhone={(phone) => { setInvitePhone(phone); setApiError(""); }} busy={busy} onConfirm={verifyInvitePhone} />}
        {screen === "biometrics" && enrollmentContact && <Biometrics contactName={enrollmentContact.name} onDone={saveBiometrics} />}
        {screen === "faceRegistration" && enrollmentContact && <FaceRegistration contactName={enrollmentContact.name} onDone={saveFaceRegistration} />}
        {screen === "parentAppInstall" && <ParentAppInstall families={protectedFamilies} onShare={shareParentInstall} onHome={() => setScreen("home")} />}
        {screen === "enrollmentComplete" && <CallStage tone="safe" icon={<CheckCircle2 />} eyebrow="가족 본인 등록 완료" title="안전하게 등록됐어요" description="등록한 목소리와 얼굴정보가 가족 사칭 확인에 사용됩니다."><button className="primary full" onClick={closeEnrollmentWindow}><X /> 이 창 닫기</button><small>초대한 가족의 등록 현황에 완료 상태가 표시됩니다.</small></CallStage>}
        {screen === "home" && <Dashboard navigate={setScreen} invitations={invitations} />}
        {screen === "normal" && <NormalCall onHome={() => setScreen("home")} />}
        {screen === "analysis" && <Analysis step={analysisStep} setStep={setAnalysisStep} onBlock={() => setScreen("blocked")} />}
        {screen === "blocked" && <BlockedCall onConfirm={() => setScreen("confirm")} />}
        {screen === "confirm" && <Confirmation onDone={() => setScreen("history")} />}
        {screen === "history" && <HistoryPage />}
      </main>
      {screen !== "signupComplete" && ((busy && screen !== "consent" && screen !== "protected" && screen !== "setupChoice" && screen !== "login") || apiMessage || (apiError && screen !== "consent" && screen !== "login")) && <div className={`api-feedback ${apiError ? "error" : ""}`} role={apiError ? "alert" : "status"} aria-live={apiError ? "assertive" : "polite"} aria-atomic="true">{busy ? "안전하게 저장하고 있습니다…" : apiError || apiMessage}<button onClick={() => { setApiError(""); setApiMessage(""); }} aria-label="알림 닫기"><X /></button></div>}

      {!([ "welcome", "parentConnect", "setupChoice", "selfPhone", "signup", "consent", "signupComplete", "login", "protected", "contacts", "deviceInvite", "registrationPlan", "invite", "enrollmentStatus", "enrollmentVerify", "biometrics", "faceRegistration", "parentAppInstall", "enrollmentComplete", "normal", "analysis", "blocked", "confirm"] as Screen[]).includes(screen) && (
        <nav className="bottom-nav">
          <NavItem active={screen === "home"} icon={<Home />} label="홈" onClick={() => setScreen("home")} />
          <NavItem active={screen === "protected" || screen === "contacts"} icon={<Users />} label="가족" onClick={openRegistrationManagement} />
          <NavItem active={screen === "history"} icon={<FileClock />} label="기록" onClick={() => setScreen("history")} />
        </nav>
      )}
    </div>
  );
}

function Welcome({ onSignup, onLogin }: { onSignup: () => void; onLogin: () => void }) {
  return <div className="sori-landing">
    <div className="landing-actions"><button className="signup-chip" onClick={onSignup}><UserPlus /> 회원가입</button></div>
    <section className="landing-brand">
      <span className="landing-logo"><Shield /></span>
      <h1>SoriCall</h1>
      <p>AI 가족 사칭 전화 보호</p>
    </section>
    <div className="landing-call-icon"><span><PhoneCall /></span></div>
    <section className="landing-message">
      <h2>부모님의 안전한 통화를<br/>가족의 목소리로 지켜드립니다.</h2>
      <p>가족의 전화번호와 목소리를 기억하고,<br/>의심되는 통화는 가족에게 한 번 더 확인합니다.</p>
    </section>
    <div className="landing-cta">
      <button className="primary full" onClick={onLogin}>서비스 시작</button>
    </div>
    <p className="landing-notice"><ShieldAlert /> 보이스피싱 위험을 줄이기 위한 가족 통화 보호 서비스입니다.</p>
  </div>;
}

function SetupChoice({ onSelect }: { onSelect: (mode: SetupMode) => void }) {
  return <div className="form-wrap"><section className="form-card setup-choice">
    <span className="eyebrow">가입 방법 선택</span>
    <h1>어떻게 시작할까요?</h1>
    <p className="lead">가족 상황에 맞는 방법을 선택해 주세요. 두 방법 모두 하나의 가족 그룹으로 안전하게 연결됩니다.</p>
    <button className="setup-option" onClick={() => onSelect("self")}><span><Shield /></span><strong>내 전화를 보호받고 싶어요</strong><small>부모님·조부모님이 직접 가입하고 자녀·손주를 초대합니다.</small><ChevronRight /></button>
    <button className="setup-option" onClick={() => onSelect("helper")}><span><HeartHandshake /></span><strong>부모님의 전화를 보호하고 싶어요</strong><small>보호할 가족을 먼저 등록하고 내 음성을 등록합니다.</small><ChevronRight /></button>
    <InfoBox icon={<UserRoundCheck />}><b>목소리는 각 가족이 자신의 휴대전화에서 직접 등록합니다.</b><br/>보호받을 휴대전화에서는 최초 한 번 통화 보호를 켜야 합니다.</InfoBox>
  </section></div>;
}

function SelfPhone({ value, setValue, onNext }: { value: string; setValue: (phone: string) => void; onNext: () => void }) { return <FormCard step="본인 휴대전화 확인" title="보호받을 본인 휴대전화를 알려 주세요" description="기존 계정에 휴대전화 번호가 없어 통화 보호 연결을 위해 한 번만 확인합니다.">
  <Field label="본인 휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value} onChange={setValue}/>{value && !isValidMobilePhone(value) && <span className="validation-error">올바른 휴대전화 번호를 입력해 주세요.</span>}
  <InfoBox icon={<Shield />}><b>입력한 번호는 본인 통화 보호 대상을 연결하는 데 사용됩니다.</b><br/>다음 단계에서 자녀·손주 등 확인 가족을 여러 명 등록할 수 있습니다.</InfoBox>
  <button className="primary full" disabled={!isValidMobilePhone(value)} onClick={onNext}>다음: 확인 가족 등록</button>
</FormCard>; }

function Signup({ value, setValue, onSendCode, onConfirmCode, onNext, busy }: { value: {name:string;phone:string;verificationId:string;verificationCode:string;verificationToken:string;password:string;passwordConfirm:string}; setValue: React.Dispatch<React.SetStateAction<typeof value>>; onSendCode: () => void; onConfirmCode: () => void; onNext: () => void; busy: boolean }) { return <FormCard step="1 / 3" title="가족의 안심을 시작해요" description="휴대전화 문자 인증으로 안전하게 가입합니다.">
  <Field label="이름" placeholder="이름을 입력해 주세요" autoComplete="off" value={value.name} onChange={name => setValue(v => ({...v,name}))}/>
  <label className="field"><span>본인 휴대전화 번호</span><div><input aria-label="본인 휴대전화 번호" autoComplete="off" placeholder="010-0000-0000" type="tel" value={value.phone} disabled={Boolean(value.verificationToken)} onChange={e => setValue(v => ({...v,phone:e.target.value,verificationId:"",verificationCode:"",verificationToken:""}))}/><button disabled={busy || !isValidMobilePhone(value.phone) || Boolean(value.verificationToken)} onClick={onSendCode}>{value.verificationId ? "재전송" : "인증번호 받기"}</button></div></label>
  {value.phone && !isValidMobilePhone(value.phone) && <span className="validation-error">올바른 휴대전화 번호를 입력해 주세요.</span>}
  {value.verificationId && !value.verificationToken && <label className="field"><span>문자 인증번호</span><div><input aria-label="문자 인증번호" inputMode="numeric" maxLength={6} placeholder="6자리 인증번호" value={value.verificationCode} onChange={e => setValue(v => ({...v,verificationCode:e.target.value.replace(/\D/g, "")}))}/><button disabled={busy || value.verificationCode.length !== 6} onClick={onConfirmCode}>인증 확인</button></div></label>}
  {value.verificationToken && <div className="info-box"><span><Check /></span><p><b>휴대전화 인증이 완료됐습니다.</b></p></div>}
  <Field label="비밀번호" placeholder="8자 이상 입력해 주세요" type="password" autoComplete="new-password" value={value.password} onChange={password => setValue(v => ({...v,password}))}/>{value.password && value.password.length < 8 && <span className="validation-error">비밀번호는 8자 이상 입력해 주세요.</span>}<Field label="비밀번호 확인" placeholder="한 번 더 입력해 주세요" type="password" autoComplete="new-password" value={value.passwordConfirm} onChange={passwordConfirm => setValue(v => ({...v,passwordConfirm}))}/>{value.passwordConfirm && value.password !== value.passwordConfirm && <span className="validation-error">비밀번호 확인이 일치하지 않습니다.</span>}
  <button className="primary full" disabled={!value.name.trim() || !value.verificationToken || value.password.length < 8 || value.password !== value.passwordConfirm} onClick={onNext}>다음</button><p className="form-note"><LockKeyhole /> 개인정보는 암호화하여 안전하게 보관합니다.</p>
</FormCard>; }

function Consent({ agreed, setAgreed, onNext, error, onClearError, busy }: { agreed: boolean[]; setAgreed: (v: boolean[]) => void; onNext: () => void; error: string; onClearError: () => void; busy: boolean }) {
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const items = [
    ["서비스 이용약관", true, "SoriCall의 가족 통화 보호, 위험 안내 및 본인 등록 기능을 제공하기 위한 기본 이용 조건입니다."],
    ["개인정보 수집·이용", true, "계정 생성과 서비스 제공을 위해 이름, 휴대전화 번호, 가족관계 및 연락처 정보를 수집·이용합니다."],
    ["가족 전화번호 및 음성 특징정보 처리", true, "가족 사칭 여부 확인을 위해 등록한 전화번호와 음성에서 추출한 특징정보를 비교·분석합니다. 원본 음성은 개발환경 보존 설정에 따라 저장하지 않을 수 있습니다."],
    ["통화 위험분석 및 가족 알림", true, "의심 통화의 위험 신호를 분석하고 필요한 경우 등록된 확인 가족에게 알림과 확인 요청을 전달합니다."],
    ["얼굴정보 처리", true, "가족 본인 확인을 위해 등록한 얼굴에서 추출한 특징정보를 비교·분석합니다."],
  ] as const;
  const toggle = (i: number) => setAgreed(agreed.map((v, n) => n === i ? !v : v));
  return <FormCard step="2 / 3" title="서비스 이용에 동의해 주세요" description="음성과 얼굴정보는 가족 본인 확인을 위한 필수 등록 정보입니다.">
    {error && <div className="inline-api-error" role="alert"><span>{error}</span><button onClick={onClearError} aria-label="오류 닫기"><X /></button></div>}
    <button className={`agree-all ${agreed.every(Boolean) ? "checked" : ""}`} onClick={() => setAgreed(items.map(() => !agreed.every(Boolean)))}><span><Check /></span>전체 동의</button>
    <div className="consent-list">{items.map(([label, required, detail], i) => <div className={`consent-item ${expandedItem === i ? "expanded" : ""}`} key={label}><div className="consent-item-row"><button className="consent-toggle" onClick={() => toggle(i)}><span className={agreed[i] ? "check checked" : "check"}><Check /></span><b>{required ? "[필수]" : "[선택]"}</b><span>{label}</span></button><button className="consent-detail-toggle" aria-label={`항목 ${i + 1} 세부내용 ${expandedItem === i ? "닫기" : "열기"}`} onClick={() => setExpandedItem(expandedItem === i ? null : i)}><ChevronRight /></button></div>{expandedItem === i && <div className="consent-detail"><p>{detail}</p></div>}</div>)}</div>
    <button className="primary full" disabled={busy || !agreed.every(Boolean)} onClick={onNext}>{busy ? "가입 정보를 저장하는 중…" : "동의하고 계속하기"}</button>
  </FormCard>;
}

function SignupComplete({ onNext }: { onNext: () => void }) {
  return <CallStage tone="safe" icon={<CheckCircle2 />} eyebrow="회원가입 완료" title="안전하게 가입됐어요" description="이제 통화를 보호할 가족과 확인해 줄 가족을 등록해 주세요.">
    <div className="info-box"><span><Shield /></span><p><b>가입 정보가 안전하게 저장됐습니다.</b><br/>가족 등록을 마치면 통화 보호 준비가 완료됩니다.</p></div>
    <button className="primary full" onClick={onNext}>서비스 시작 <ChevronRight /></button>
  </CallStage>;
}

function Login({ value, setValue, onNext, error, onClearError }: { value:{phone_number:string;password:string}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; onNext: () => void; error: string; onClearError: () => void }) { return <FormCard title="다시 만나서 반가워요" description="등록한 휴대전화 번호로 로그인해 주세요.">{error && <div className="login-error" role="alert"><div><b>{error}</b><p>입력한 휴대전화 번호와 비밀번호를 다시 확인해 주세요.<br/>비밀번호가 기억나지 않으면 ‘비밀번호 찾기’를 이용하고, 가입하지 않았다면 회원가입을 진행해 주세요.</p></div><button onClick={onClearError} aria-label="로그인 오류 닫기"><X /></button></div>}<Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value.phone_number} onChange={phone_number => { onClearError(); setValue(v => ({...v,phone_number})); }}/><Field label="비밀번호" placeholder="비밀번호" type="password" value={value.password} onChange={password => { onClearError(); setValue(v => ({...v,password})); }}/><div className="between"><label><input type="checkbox"/> 로그인 유지</label><button className="link">비밀번호 찾기</button></div><button className="primary full" disabled={!isValidMobilePhone(value.phone_number) || !value.password} onClick={onNext}>로그인</button></FormCard>; }

function AdminLoginPage({ value, setValue, error, busy, onSubmit, onService }: { value: { admin_id: string; password: string }; setValue: React.Dispatch<React.SetStateAction<{ admin_id: string; password: string }>>; error: string; busy: boolean; onSubmit: () => void; onService: () => void }) {
  const valid = Boolean(value.admin_id.trim() && value.password.length >= 8);
  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => { if (event.key === "Enter" && valid) onSubmit(); };
  return <div className="admin-login-shell"><div className="admin-login-panel"><section className="admin-login-brand"><span className="admin-login-logo"><Shield/></span><p>SORICALL OPERATIONS</p><h1>가족의 안전을 지키는<br/>서비스 운영 센터</h1><span>통화 보호 현황과 위험 이벤트를 확인하고<br/>위험번호 데이터를 안전하게 관리합니다.</span><div className="admin-login-features"><div><Activity/><b>실시간 운영 현황</b><small>통화 분석과 보호 단말 상태</small></div><div><ShieldAlert/><b>위험정보 관리</b><small>위험 이벤트와 번호 관리</small></div></div></section><section className="admin-login-form"><span className="eyebrow">ADMIN ONLY</span><h2>SoriCall Admin</h2><p>관리자 콘솔 전용 로그인</p><label><span>Admin ID</span><div><CircleUserRound/><input autoFocus autoComplete="username" placeholder="Admin ID" value={value.admin_id} onChange={(event) => setValue((current) => ({ ...current, admin_id: event.target.value }))} onKeyDown={onKeyDown}/></div></label><label><span>Password</span><div><LockKeyhole/><input type="password" autoComplete="current-password" placeholder="Password" value={value.password} onChange={(event) => setValue((current) => ({ ...current, password: event.target.value }))} onKeyDown={onKeyDown}/></div></label>{error && <div className="admin-login-error" role="alert"><AlertTriangle/>{error}</div>}<button className="primary full" disabled={busy || !valid} onClick={onSubmit}>{busy ? "관리자 권한 확인 중…" : "관리자 콘솔 입장"}</button><button className="admin-service-link" onClick={onService}>서비스 화면으로 나가기</button><small className="admin-security-note"><Shield/> 관리자 콘솔의 개인정보 및 음성 데이터 접근은 운영 로그 기록 대상입니다.</small></section></div></div>;
}

function FamilyRegistration({ value, setValue, relation, setRelation, families, onAdd, onDelete, onNext, busy }: { value:{name:string;phone:string}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; relation: string; setRelation: (v: string) => void; families: RegisteredProtectedFamily[]; onAdd: () => void; onDelete: (family: RegisteredProtectedFamily) => void; onNext: () => void; busy: boolean }) { const valid = Boolean(value.name.trim()) && isValidMobilePhone(value.phone); return <FormCard step="보호할 가족 등록" title="누구의 전화를 보호할까요?" description="부모님과 조부모님 등 여러 명을 한 명씩 추가할 수 있습니다.">
  <label className="section-label">나와의 관계</label><RelationGrid options={familyRelations} value={relation} setValue={setRelation}/><Field label="성함" placeholder="예: 김영희" value={value.name} onChange={name => setValue(v => ({...v,name}))}/><Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value.phone} onChange={phone => setValue(v => ({...v,phone}))}/>{value.phone && !isValidMobilePhone(value.phone) && <span className="validation-error">올바른 휴대전화 번호를 입력해 주세요.</span>}
  <button className="secondary full" disabled={busy || !valid} onClick={onAdd}><Plus /> 이 가족 추가하기</button>
  {families.length > 0 && <div className="enrollment-list">{families.map((family) => <div className="enrollment-person" key={family.id}><span className="person-icon">{family.name.slice(0, 1)}</span><span><b>{family.name}</b><small>{family.relation} · 휴대전화 끝 {family.phoneLast4}</small></span><button className="delete-family-button" disabled={busy} onClick={() => onDelete(family)} aria-label={`${family.name} 보호 대상 삭제`}><Trash2 /> 삭제</button></div>)}</div>}
  <InfoBox icon={<Shield />}><b>{families.length > 0 ? `${families.length}명의 보호할 가족을 등록했습니다.` : "보호할 가족을 한 명 이상 추가해 주세요."}</b><br/>모두 추가한 뒤 내 음성을 등록합니다.</InfoBox><button className="primary full" disabled={busy || families.length === 0} onClick={onNext}>가족 등록 완료 · 내 음성 등록</button>
</FormCard>; }

function DeviceInvite({ familyName, link, onNext }: { familyName: string; link: string; onNext: () => void }) { return <FormCard step="부모님 휴대전화 연결" title={`${familyName}님께 앱 설치 링크를 보내세요`} description="부모님 휴대전화에서 앱을 설치하고 본인 확인과 통화 보호를 한 번만 켜면 됩니다.">
  <InfoBox icon={<Phone />}><b>개발환경용 앱 연결 링크가 준비됐습니다.</b><br/>실제 SMS 발송은 운영 전달 서비스 연결 후 활성화됩니다.</InfoBox>
  <code className="development-link">{link}</code><button className="secondary full" onClick={() => void navigator.clipboard.writeText(link)}>연결 링크 복사</button><button className="primary full" onClick={onNext}>다음: 확인 가족 등록</button>
</FormCard>; }

function ContactRegistration({ value, setValue, relation, setRelation, contacts, onAdd, onDelete, onNext, busy }: { value:{name:string;phone:string;primary:boolean}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; relation: string; setRelation: (v: string) => void; contacts: ConfirmationContactResponse[]; onAdd: () => void; onDelete: (contact: ConfirmationContactResponse) => void; onNext: () => void; busy: boolean }) { const valid = Boolean(value.name.trim()) && isValidMobilePhone(value.phone); return <FormCard step="2 / 3" title="의심전화를 확인해 줄 가족을 등록해 주세요" description="보호받을 가족에게 의심전화가 오면 실제 통화 여부를 확인합니다.">
  <label className="section-label">보호받을 가족과의 관계</label><RelationGrid options={contactRelations} value={relation} setValue={setRelation}/><Field label="성함" placeholder="예: 김민지" value={value.name} onChange={name => setValue(v => ({...v,name}))}/><Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value.phone} onChange={phone => setValue(v => ({...v,phone}))}/>{value.phone && !isValidMobilePhone(value.phone) && <span className="validation-error">올바른 휴대전화 번호를 입력해 주세요.</span>}
  <label className="toggle-row"><span><b>가장 먼저 확인할 가족</b><small>의심전화 발생 시 첫 번째로 알림을 보냅니다.</small></span><input type="checkbox" checked={value.primary} onChange={e => setValue(v => ({...v,primary:e.target.checked}))}/></label>
  <button className="secondary full" disabled={busy || !valid} onClick={onAdd}><Plus /> 이 가족 추가하기</button>
  {contacts.length > 0 && <div className="enrollment-list">{contacts.map((contact) => <div className="enrollment-person" key={contact.id}><span className="person-icon">{contact.name.slice(0, 1)}</span><span><b>{contact.name}</b><small>{contact.phone_number_last4 ? `휴대전화 끝 ${contact.phone_number_last4}` : "확인 가족"}</small></span><button className="delete-family-button" disabled={busy} onClick={() => onDelete(contact)}><Trash2 /> 삭제</button></div>)}</div>}
  <InfoBox icon={<Shield />}><b>{contacts.length > 0 ? `${contacts.length}명의 확인 가족을 등록했습니다.` : "확인 가족을 한 명 이상 추가해 주세요."}</b><br/>가족 등록을 완료하면 음성·얼굴 등록 안내로 이동합니다.</InfoBox>
  <button className="primary full" disabled={busy || contacts.length === 0} onClick={onNext}>가족 등록 완료 · 음성·얼굴 등록</button>
</FormCard>; }

function RegistrationPlan({ contacts, onNext }: { contacts: ConfirmationContactResponse[]; onNext: () => void }) { return <FormCard step="생체정보 등록 안내" title="가족별 등록 항목을 확인해 주세요" description="가족 관계와 전화번호 등록을 마쳤습니다. 음성과 얼굴은 각 가족이 자신의 휴대전화에서 별도로 등록합니다.">
  <div className="registration-type-card required"><span><Mic /></span><div><b>음성 등록</b><em>필수</em><p>가족의 목소리 특징을 등록해 가족 사칭 의심 통화 확인에 사용합니다.</p></div></div>
  <div className="registration-type-card required"><span><Video /></span><div><b>얼굴 등록</b><em>필수</em><p>가족 본인 확인을 위해 정면 얼굴정보를 등록합니다.</p></div></div>
  <div className="enrollment-list">{contacts.map((contact) => <div className="enrollment-person" key={contact.id}><span className="person-icon">{contact.name.slice(0, 1)}</span><span><b>{contact.name}</b><small>음성 필수 · 얼굴 필수</small></span><em>요청 준비</em></div>)}</div>
  <InfoBox icon={<Shield />}><b>음성과 얼굴은 모두 필수 등록 항목입니다.</b><br/>두 항목을 모두 등록해야 가족 등록이 완료됩니다.</InfoBox>
  <button className="primary full" disabled={contacts.length === 0} onClick={onNext}>다음: 등록 요청 보내기</button>
</FormCard>; }

function EnrollmentInvite({ contacts, onSend }: { contacts: ConfirmationContactResponse[]; onSend: (contact: ConfirmationContactResponse, channel: "LINK" | "QR" | "DIRECT") => void }) {
  return <FormCard step="3 / 3" title="가족에게 등록 요청을 보내세요" description="가족이 자신의 휴대전화에서 직접 동의하고 목소리와 얼굴을 등록합니다.">
    <InfoBox icon={<Shield />}><b>문자 앱에서 가족에게 직접 전송합니다.</b><br/>SoriCall은 별도 문자 발송 서비스를 사용하지 않으며, 전송 버튼은 사용자가 직접 누릅니다.</InfoBox>
    <div className="enrollment-list">{contacts.map((contact) => <div className="enrollment-person status" key={contact.id}><span className="person-icon">{contact.name.slice(0, 1)}</span><span><b>{contact.name}</b><small>휴대전화 끝 {contact.phone_number_last4 ?? "----"} · 음성 필수 · 얼굴 필수</small></span><button className="primary" onClick={() => onSend(contact, "LINK")}><Bell /> 문자 앱으로 보내기</button><button className="link" onClick={() => onSend(contact, "QR")}>QR로 연결</button><button className="link" onClick={() => onSend(contact, "DIRECT")}>옆에서 등록</button></div>)}</div>
  </FormCard>;
}

function EnrollmentStatus({ invitations, onResend, onApprove, onDeleteAsset, onDeleteFamily }: { invitations: EnrollmentInvitation[]; onResend: (invitation: EnrollmentInvitation) => void; onApprove: (invitation: EnrollmentInvitation) => void; onDeleteAsset: (invitation: EnrollmentInvitation, asset: "voice" | "face") => void; onDeleteFamily: (invitation: EnrollmentInvitation) => void }) {
  const labels: Record<string, string> = { PENDING: "응답 대기", COMPLETED: "자료 도착", EXPIRED: "링크 만료" };
  return <FormCard title="가족 등록 현황" description="가족별 음성·얼굴 등록 진행 상태를 확인할 수 있습니다.">
    <div className="enrollment-list">{invitations.map((invitation) => { const approval = invitation.member_approval_status ?? (invitation.status === "COMPLETED" ? "REVIEW_REQUIRED" : "INVITED"); return <div className="enrollment-person status" key={invitation.id}><span className="person-icon">{invitation.family_member_name.slice(0, 1)}</span><span><b>{invitation.family_member_name}</b><small>휴대전화 끝 {invitation.phone_number_last4 ?? "----"} · 신뢰등급 {invitation.member_trust_level ?? "D"}</small>{invitation.enrollment_url && <code className="development-link">{new URL(invitation.enrollment_url, window.location.origin).toString()}</code>}</span>{invitation.channel === "QR" && invitation.enrollment_url && invitation.status === "PENDING" && <EnrollmentQr url={new URL(invitation.enrollment_url, window.location.origin).toString()} name={invitation.family_member_name} />}<em className={approval.toLowerCase()}>{approval === "ACTIVE" ? "승인 완료" : labels[invitation.status] ?? invitation.status}</em>{approval === "REVIEW_REQUIRED" ? <button className="primary" onClick={() => onApprove(invitation)}>이 가족이 맞습니다</button> : invitation.status !== "COMPLETED" && <button className="primary" onClick={() => onResend(invitation)}><Bell /> 문자 앱으로 보내기</button>}{invitation.status === "COMPLETED" && <div className="registered-delete-actions"><button disabled={invitation.voice_deleted} onClick={() => onDeleteAsset(invitation, "voice")}><Trash2 /> {invitation.voice_deleted ? "음성 삭제됨" : "음성 삭제"}</button><button disabled={invitation.face_deleted} onClick={() => onDeleteAsset(invitation, "face")}><Trash2 /> {invitation.face_deleted ? "얼굴 삭제됨" : "얼굴 삭제"}</button></div>}<button className="delete-family-button" onClick={() => onDeleteFamily(invitation)}><Trash2 /> 가족 삭제</button></div>; })}</div>
  </FormCard>;
}

function EnrollmentQr({ url, name }: { url: string; name: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => { void QRCode.toDataURL(url, { width: 220, margin: 2 }).then(setSrc); }, [url]);
  return src ? <img className="enrollment-qr" src={src} alt={`${name}님의 5분 한정 등록 QR`} /> : null;
}

function EnrollmentPhoneVerification({ phone, setPhone, busy, onConfirm }: { phone: string; setPhone: (value: string) => void; busy: boolean; onConfirm: () => void }) {
  return <FormCard title="초대받은 가족 본인 확인" description="가족 자료를 안전하게 등록하기 위해 초대받은 휴대전화 번호를 확인합니다.">
    <InfoBox icon={<Shield />}><b>초대받은 본인의 휴대전화 번호를 입력해 주세요.</b><br/>번호가 일치해야 필수 항목인 음성과 얼굴정보를 등록할 수 있습니다.</InfoBox>
    <Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={phone} onChange={setPhone}/>
    <button className="primary full" disabled={busy || !isValidMobilePhone(phone)} onClick={onConfirm}>{busy ? "번호를 확인하는 중…" : "휴대전화 번호 확인"}</button>
  </FormCard>;
}

function Biometrics({ contactName, onDone }: { contactName: string; onDone: (audioRef: string, durationMs: number, faceImageRef: string | null) => void }) {
  const minimumRecordingMs = 15_000;
  const maximumRecordingMs = 60_000;
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const elapsedRef = useRef(0);
  const [recording, setRecording] = useState(false);
  const [paused, setPaused] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [audioRef, setAudioRef] = useState("");
  const [durationMs, setDurationMs] = useState(0);
  const [mediaError, setMediaError] = useState("");

  useEffect(() => { elapsedRef.current = elapsedMs; }, [elapsedMs]);
  useEffect(() => {
    if (!recording || paused) return;
    const interval = window.setInterval(() => setElapsedMs((current) => Math.min(maximumRecordingMs, current + 250)), 250);
    return () => window.clearInterval(interval);
  }, [recording, paused]);
  useEffect(() => {
    if (recording && elapsedMs >= maximumRecordingMs) recorderRef.current?.stop();
  }, [recording, elapsedMs]);

  const startRecording = async () => {
    setMediaError("");
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setMediaError("문장을 보면서 녹음하려면 HTTPS 보안 주소로 접속해야 합니다. 현재 페이지를 HTTPS 주소로 다시 열어 주세요.");
      return;
    }
    if (typeof MediaRecorder === "undefined") {
      setMediaError("현재 브라우저는 화면 내 녹음을 지원하지 않습니다. 최신 Chrome 또는 Safari에서 다시 시도해 주세요.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredMimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = preferredMimeType ? new MediaRecorder(stream, { mimeType: preferredMimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = () => setAudioRef(String(reader.result));
        reader.readAsDataURL(blob);
        const recordedDuration = Math.max(1, elapsedRef.current);
        setDurationMs(recordedDuration);
        if (recordedDuration < minimumRecordingMs) {
          setMediaError("목소리 특징을 정확히 확인하려면 문장을 끝까지 읽어 15초 이상 녹음해 주세요.");
        }
        setRecording(false);
        setPaused(false);
        stream.getTracks().forEach((track) => track.stop());
      };
      recorderRef.current = recorder;
      setAudioRef("");
      setDurationMs(0);
      setElapsedMs(0);
      elapsedRef.current = 0;
      recorder.start();
      setRecording(true);
      setPaused(false);
    } catch (error) {
      const name = error instanceof DOMException ? error.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setMediaError("마이크 사용이 차단됐습니다. 주소창의 사이트 설정에서 마이크를 ‘허용’하면 문장을 보면서 녹음할 수 있습니다.");
      } else if (name === "NotFoundError") {
        setMediaError("사용 가능한 마이크를 찾지 못했습니다. 기기의 마이크 연결 상태를 확인해 주세요.");
      } else if (name === "NotReadableError") {
        setMediaError("다른 앱이 마이크를 사용 중입니다. 통화나 녹음 앱을 종료한 뒤 다시 시도해 주세요.");
      } else {
        setMediaError("마이크를 시작하지 못했습니다. 브라우저를 새로고침한 뒤 다시 시도해 주세요.");
      }
    }
  };

  const togglePause = () => {
    const recorder = recorderRef.current;
    if (!recorder) return;
    if (paused) {
      recorder.resume();
      setPaused(false);
    } else {
      recorder.pause();
      setPaused(true);
    }
  };

  const finishRecording = () => recorderRef.current?.stop();
  const elapsedSeconds = Math.floor(elapsedMs / 1000);

  return <FormCard step="자녀 음성 등록" title={`${contactName}님, 목소리를 등록해 주세요`} description="부모님과의 통화 분석을 위해 아래 문장을 평소 말투로 읽어 주세요.">
    <div className={`voice-recorder ${recording ? "is-recording" : ""}`}><div className="voice-script"><p>엄마, 오늘 저녁 일곱 시쯤 집에 도착하면 다시 전화드릴게요.</p><p>창문 옆 화분에 물도 주고, 따뜻한 차를 마시면서 천천히 이야기해요.</p><p>급한 일이 있어도 먼저 가족끼리 약속한 방법으로 꼭 확인해 주세요.</p></div>{recording ? <div className="recording-control"><div className="recording-meta"><b>{paused ? "녹음 일시정지" : "녹음 중"}</b><span>{elapsedSeconds}초 / 60초</span></div><div className="recording-progress"><i style={{width: `${(elapsedMs / maximumRecordingMs) * 100}%`}} /></div><div className="recording-actions"><button className="secondary" onClick={togglePause}>{paused ? <Play /> : <Pause />}{paused ? "계속 녹음" : "녹음 멈춤"}</button><button className="primary" onClick={finishRecording}><CheckCircle2 /> 녹음 끝내기</button></div></div> : <button className="primary voice-start" onClick={startRecording}><Mic /> {audioRef ? "다시 녹음" : "녹음 시작"}</button>}{audioRef && !recording && <small className="recorded-status">녹음 시간 {(durationMs / 1000).toFixed(1)}초 {durationMs >= minimumRecordingMs ? "· 음성 등록 준비 완료" : "· 15초 이상 다시 녹음해 주세요"}</small>}</div>
    {mediaError && <span className="validation-error">{mediaError}</span>}
    <button className="primary full" disabled={!audioRef || durationMs < minimumRecordingMs || recording} onClick={() => onDone(audioRef, durationMs, null)}>등록 완료하기</button>
  </FormCard>;
}

function FaceRegistration({ contactName, onDone }: { contactName: string; onDone: (faceImageRef: string) => void }) {
  const [preview, setPreview] = useState("");
  const [faceImageRef, setFaceImageRef] = useState("");
  const [error, setError] = useState("");
  const selectFace = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("얼굴 사진 이미지 파일을 선택해 주세요.");
      return;
    }
    setError("");
    if (file.size > 10 * 1024 * 1024) {
      setError("얼굴 사진은 10MB 이하만 등록할 수 있습니다.");
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      const dataUrl = String(reader.result);
      setPreview(dataUrl);
      setFaceImageRef(dataUrl);
    };
    reader.readAsDataURL(file);
  };
  return <FormCard step="얼굴 등록" title={`${contactName}님, 얼굴을 등록해 주세요`} description="정면을 바라보고 얼굴이 선명하게 보이도록 촬영해 주세요.">
    <div className="face-registration-card">
      <div className={`face-preview ${preview ? "has-image" : ""}`}>{preview ? <img src={preview} alt="선택한 얼굴 사진 미리보기" /> : <CircleUserRound />}</div>
      <b>{preview ? "얼굴 사진을 확인해 주세요" : "밝은 곳에서 정면 사진을 촬영해 주세요"}</b>
      <small>모자와 마스크를 벗고 얼굴 전체가 화면 안에 들어오게 해 주세요.</small>
      <label className="secondary face-capture"><Video /> {preview ? "다시 촬영" : "얼굴 촬영"}<input className="file-input" type="file" accept="image/*" capture="user" aria-label="얼굴 촬영" onChange={(event) => selectFace(event.target.files?.[0])}/></label>
    </div>
    {error && <span className="validation-error">{error}</span>}
    <button className="primary full" disabled={!faceImageRef} onClick={() => onDone(faceImageRef)}>얼굴 등록 완료</button>
  </FormCard>;
}

function ParentAppInstall({ families, onShare, onHome }: { families: RegisteredProtectedFamily[]; onShare: (family: RegisteredProtectedFamily) => void; onHome: () => void }) {
  return <FormCard step="마지막 단계" title="부모님 휴대전화에 앱을 설치해 주세요" description="실제로 통화를 보호하려면 보호 대상자의 휴대전화에서 SoriCall 앱 설치와 권한 설정이 필요합니다.">
    <div className="install-step-list">
      <div><span>1</span><p><b>설치 안내 보내기</b><small>아래 보호 대상별 버튼으로 설치 링크를 전달합니다.</small></p></div>
      <div><span>2</span><p><b>부모님 휴대전화에서 링크 열기</b><small>SoriCall 앱을 설치하고 본인 휴대전화 번호를 확인합니다.</small></p></div>
      <div><span>3</span><p><b>통화 보호 권한 켜기</b><small>전화 식별과 마이크 등 필요한 권한을 한 번만 허용합니다.</small></p></div>
    </div>
    <div className="parent-install-list">{families.map((family) => <div className="parent-install-person" key={family.id}><span className="person-icon">{family.name.slice(0, 1)}</span><span><b>{family.name}</b><small>{family.relation} · 휴대전화 끝 {family.phoneLast4}</small></span>{family.status === "ACTIVE" ? <em className="connection-active"><Check /> 통화 보호 켜짐</em> : <button className="secondary" onClick={() => onShare(family)}><Phone /> 설치 안내 보내기</button>}</div>)}</div>
    <InfoBox icon={<Shield />}><b>부모님 휴대전화에서 설정을 마쳐야 보호가 시작됩니다.</b><br/>아직 설치하지 않았더라도 나중에 홈에서 다시 안내를 보낼 수 있습니다.</InfoBox>
    <button className="primary full" onClick={onHome}>안내를 보냈어요 · 홈으로 이동</button>
  </FormCard>;
}

function ParentDeviceConnect({ token }: { token: string }) {
  const [enrollment, setEnrollment] = useState<DeviceEnrollment | null>(null);
  const [step, setStep] = useState<"download" | "verify" | "permissions" | "complete">("download");
  const [phone, setPhone] = useState("");
  const [verificationId, setVerificationId] = useState("");
  const [code, setCode] = useState("");
  const [permissions, setPermissions] = useState([false, false, false]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [downloadStarted, setDownloadStarted] = useState(false);
  const apkUrl = `${import.meta.env.BASE_URL}downloads/soricall.apk`;

  useEffect(() => {
    apiGet<DeviceEnrollment>(`/api/v1/device-enrollments/resolve?token=${encodeURIComponent(token)}`)
      .then((result) => {
        setEnrollment(result);
        if (result.status === "ACTIVE") setStep("complete");
        else if (result.status === "PHONE_VERIFIED") setStep("permissions");
      })
      .catch((reason) => setError(userMessage(reason)));
  }, [token]);

  const action = async (work: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setError("");
    try { await work(); } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  };
  const sendCode = () => void action(async () => {
    const result = await apiPost<{ verification_id: string; development_code?: string | null }>(`/api/v1/device-enrollments/verification?token=${encodeURIComponent(token)}`, { phone_number: phone });
    setVerificationId(result.verification_id);
    setCode(result.development_code ?? "");
  });
  const confirmCode = () => void action(async () => {
    const result = await apiPost<DeviceEnrollment>(`/api/v1/device-enrollments/verification/confirm?token=${encodeURIComponent(token)}`, { verification_id: verificationId, code });
    setEnrollment(result); setStep("permissions");
  });
  const complete = () => void action(async () => {
    const result = await apiPost<DeviceEnrollment>(`/api/v1/device-enrollments/complete?token=${encodeURIComponent(token)}`, {});
    window.localStorage.removeItem("soricall_device_enrollment_token");
    setEnrollment(result); setStep("complete");
  });

  if (!enrollment && !error) return <FormCard title="연결 정보를 확인하고 있습니다" description="잠시만 기다려 주세요."><div className="info-box"><span><Activity /></span><p>부모님 통화 보호 연결을 준비하고 있습니다.</p></div></FormCard>;
  return <FormCard step="부모님 휴대전화 연결" title={step === "complete" ? "통화 보호 연결이 완료됐어요" : `${enrollment?.protected_user_name ?? "부모님"}님의 전화를 보호해요`} description={step === "complete" ? "이제 이 휴대전화에서 SoriCall 통화 보호가 시작됩니다." : "아래 순서대로 앱 설치와 본인 확인을 진행해 주세요."}>
    {error && <div className="inline-api-error" role="alert"><span>{error}</span></div>}
    {step === "download" && <><div className="connect-hero"><Phone /><b>SoriCall Android 앱</b><small>다운로드가 끝나면 표시되는 SoriCall.apk를 눌러 설치해 주세요.</small></div><a className="primary full download-link" href={apkUrl} onClick={() => setDownloadStarted(true)}><Download /> Android 앱 다운로드 · 설치 열기</a>{downloadStarted && <div className="download-install-guide" role="status"><Download /><span><b>다운로드가 시작됐습니다.</b><small>화면 위의 다운로드 완료 알림에서 <strong>SoriCall.apk</strong>를 눌러 설치한 뒤 이 안내 링크를 다시 열어 주세요.</small></span></div>}<button className="secondary full" onClick={() => { window.location.href = `soricall://connect?device_token=${encodeURIComponent(token)}`; }}>설치를 완료했어요 · SoriCall 열기</button></>}
    {step === "verify" && <><InfoBox icon={<Shield />}><b>등록된 부모님 휴대전화인지 확인합니다.</b><br/>휴대전화 끝 {enrollment?.phone_number_last4 ?? "----"} 번호로 인증해 주세요.</InfoBox><Field label="부모님 휴대전화 번호" placeholder="010-0000-0000" type="tel" value={phone} onChange={setPhone}/><button className="secondary full" disabled={busy || !isValidMobilePhone(phone)} onClick={sendCode}>인증번호 받기</button>{verificationId && <><Field label="문자 인증번호" placeholder="6자리 인증번호" value={code} onChange={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))}/><button className="primary full" disabled={busy || code.length !== 6} onClick={confirmCode}>인증하고 계속하기</button></>}</>}
    {step === "permissions" && <><div className="permission-list">{[["전화 식별 권한", "걸려오는 번호를 확인하고 위험 통화를 안내합니다."], ["마이크 권한", "통화 중 음성 위험 신호를 분석합니다."], ["알림 권한", "위험 감지와 가족 확인 결과를 알려드립니다."]].map(([title, detail], index) => <label key={title}><input type="checkbox" checked={permissions[index]} onChange={() => setPermissions((current) => current.map((value, item) => item === index ? !value : value))}/><span><b>{title}</b><small>{detail}</small></span></label>)}</div><InfoBox icon={<Phone />}><b>설치한 앱을 열어 위 권한을 허용해 주세요.</b><br/>앱 설정을 마친 뒤 각 항목을 확인하면 연결을 완료할 수 있습니다.</InfoBox><button className="primary full" disabled={busy || !permissions.every(Boolean)} onClick={complete}>권한 설정 완료 · 보호 시작</button></>}
    {step === "complete" && <><div className="connection-complete"><CheckCircle2 /><b>{enrollment?.protected_user_name}님 통화 보호 켜짐</b><small>자녀의 SoriCall 화면에도 연결 완료 상태가 표시됩니다.</small></div><button className="primary full" onClick={() => window.close()}>완료</button></>}
  </FormCard>;
}

function ResumeDeviceEnrollmentMissing() {
  return <FormCard
    step="부모님 휴대전화 연결"
    title="처음 받은 연결 링크를 다시 열어 주세요"
    description="앱 설치는 완료됐지만 이 브라우저에는 연결 정보가 남아 있지 않습니다."
  >
    <InfoBox icon={<Phone />}>
      <b>문자나 카카오톡으로 받은 SoriCall 설치 안내 링크를 다시 눌러 주세요.</b><br/>
      앱을 다시 다운로드할 필요는 없습니다. 안내 화면에서 ‘설치를 완료했어요’를 누르면 본인 확인을 계속할 수 있습니다.
    </InfoBox>
  </FormCard>;
}

function Dashboard({ navigate, invitations }: { navigate: (s: Screen) => void; invitations: EnrollmentInvitation[] }) { return <div className="dashboard">
  <section className="enrollment-summary"><div className="section-heading"><div><span>내 전화를 보호받고 싶어요</span><h2>의심전화를 확인해 줄 가족</h2></div><button onClick={() => navigate("enrollmentStatus")}>등록 현황 <ChevronRight/></button></div>{invitations.length > 0 ? invitations.map((item) => <div className="enrollment-person status" key={item.id}><span className="person-icon">{item.family_member_name.slice(0, 1)}</span><span><b>{item.family_member_name}</b><small>{item.status === "COMPLETED" ? "음성·얼굴 등록 완료" : "음성·얼굴 등록 대기"}</small></span><em className={item.status.toLowerCase()}>{item.status === "COMPLETED" ? "등록 완료" : "등록 대기"}</em></div>) : <div className="empty-state">의심전화를 확인해 줄 가족을 등록해 주세요.</div>}</section>
  <div className="section-heading"><div><span>최근 통화</span><h2>통화 보호 기록</h2></div><button onClick={() => navigate("history")}>전체 보기 <ChevronRight/></button></div>
  <section className="recent-list"><CallRow tone="safe" icon={<Check/>} title="등록된 가족 전화" meta="김민지 · 딸 · 오늘 오전 9:41" badge="안전" onClick={() => navigate("normal")}/><CallRow tone="warn" icon={<AlertTriangle/>} title="가족 사칭 의심전화" meta="번호 끝 8821 · 어제 오후 3:18" badge="확인 완료" onClick={() => navigate("analysis")}/><CallRow tone="danger" icon={<PhoneOff/>} title="고위험 전화 차단" meta="번호 끝 4402 · 7월 12일" badge="차단" onClick={() => navigate("blocked")}/></section>
</div>; }

function NormalCall({ onHome }: { onHome: () => void }) { return <CallStage tone="safe" icon={<PhoneCall/>} eyebrow="등록된 가족 전화" title="김민지 딸의 전화입니다" description="등록된 전화번호와 가족 정보가 일치합니다."><div className="caller-card"><span className="person-icon">김</span><span><b>김민지</b><small>딸 · 010-••••-4421</small></span><span className="safe-label"><Check/> 안전</span></div><button className="primary full" onClick={onHome}><PhoneCall/> 통화 계속하기</button></CallStage>; }

function Analysis({ step, setStep, onBlock }: { step: number; setStep: (n: number) => void; onBlock: () => void }) { const steps = [["전화번호 확인", "등록되지 않은 번호입니다"], ["가족 음성 비교", "가족 목소리와 유사합니다"], ["AI 합성음 분석", "합성음 가능성이 감지됐습니다"], ["통화내용 분석", "송금 요구 표현이 감지됐습니다"], ["가족 확인", "김민지 딸에게 확인 중입니다"]]; return <CallStage tone="warn" icon={<ShieldAlert/>} eyebrow="통화 중 실시간 확인" title="가족 사칭이 의심됩니다" description="돈을 보내거나 앱을 설치하지 마세요. 가족에게 확인하고 있습니다."><div className="analysis-list">{steps.map(([a,b], i) => <div key={a} className={i < step ? "complete" : i === step ? "working" : "pending"}><span>{i < step ? <Check/> : i === step ? <Activity/> : <Clock3/>}</span><div><b>{a}</b><small>{i <= step ? b : "확인 대기"}</small></div>{i === step && <i className="pulse"/>}</div>)}</div><div className="button-row"><button className="secondary" onClick={() => setStep(Math.min(4, step + 1))}>분석 진행 보기</button><button className="danger" onClick={onBlock}><PhoneOff/> 지금 통화 끊기</button></div></CallStage>; }

function BlockedCall({ onConfirm }: { onConfirm: () => void }) { return <CallStage tone="danger" icon={<PhoneOff/>} eyebrow="고위험 전화 차단" title="보이스피싱 위험이 높아 전화를 차단했습니다" description="가족 목소리처럼 들려도 저장된 가족 번호로 다시 확인하세요."><div className="risk-reasons"><b>차단한 이유</b><span><X/> 등록되지 않은 전화번호</span><span><X/> AI 합성음 가능성 높음</span><span><X/> 송금 요구 표현 감지</span></div><button className="primary full"><PhoneCall/> 저장된 가족에게 다시 전화</button><button className="secondary full" onClick={onConfirm}><HeartHandshake/> 확인 가족에게 요청</button></CallStage>; }

function Confirmation({ onDone }: { onDone: () => void }) { return <CallStage tone="confirm" icon={<HeartHandshake/>} eyebrow="가족 확인 요청" title="지금 김영희 어머니께 전화하셨나요?" description="가족의 응답은 의심전화 위험도 판단에 바로 반영됩니다."><div className="confirm-caller"><span className="person-icon">김</span><div><b>김영희 어머니</b><small>의심전화 수신 · 지금</small></div></div><button className="answer yes" onClick={onDone}><CheckCircle2/><span><b>네, 제가 전화했어요</b><small>정상 가족 통화입니다</small></span></button><button className="answer no" onClick={onDone}><X/><span><b>아니요, 제가 아닙니다</b><small>즉시 위험도를 높이고 차단합니다</small></span></button><button className="answer unknown" onClick={onDone}><AlertTriangle/><span><b>잘 모르겠습니다</b><small>추가 확인을 진행합니다</small></span></button></CallStage>; }

function HistoryPage() { return <div className="content-wide"><div className="page-heading"><span className="eyebrow">통화 보호 기록</span><h1>최근 통화를 확인하세요</h1><p>민감한 통화내용은 기본적으로 숨겨지며 보존기간 후 자동 삭제됩니다.</p></div><div className="filter-row"><button className="active">전체 16</button><button>안전 12</button><button>주의 2</button><button>차단 2</button></div><section className="history-table"><div className="table-head"><span>상태</span><span>통화 정보</span><span>판단 근거</span><span>가족 확인</span><span>시간</span></div><HistoryRow tone="safe" status="안전" call="김민지 · 딸" reason="등록 가족 번호 일치" confirm="확인 불필요" time="오늘 09:41"/><HistoryRow tone="warn" status="주의" call="번호 끝 8821" reason="미등록 번호 · 유사 음성" confirm="전화했음" time="어제 15:18"/><HistoryRow tone="danger" status="차단" call="번호 끝 4402" reason="합성음 · 송금 요구" confirm="전화하지 않음" time="7월 12일"/></section></div>; }

type AdminTab = "dashboard" | "seniors" | "family" | "auth" | "calls" | "actions" | "confirmations" | "incidents" | "consents" | "disposals" | "reports" | "admins" | "audits";
type AdminMenuGroup = { id: string; label: string; icon: React.ReactNode; tab?: AdminTab; children?: { id: AdminTab; label: string }[] };
const adminMenuGroups: AdminMenuGroup[] = [
  { id: "dashboard", label: "대시보드", icon: <LayoutDashboard/>, tab: "dashboard" },
  { id: "users", label: "사용자 관리", icon: <Users/>, children: [{id:"seniors",label:"어르신 사용자"},{id:"family",label:"가족 사용자"}] },
  { id: "auth", label: "가족 인증정보 관리", icon: <Mic/>, tab: "auth" },
  { id: "security", label: "통화 보안 관리", icon: <ShieldAlert/>, children: [{id:"calls",label:"통화 분석 이력"},{id:"actions",label:"경고·차단·알림 이력"},{id:"confirmations",label:"가족 확인 응답"}] },
  { id: "incidents", label: "신고·사건 관리", icon: <AlertTriangle/>, tab: "incidents" },
  { id: "privacy", label: "개인정보 관리", icon: <Database/>, children: [{id:"consents",label:"동의 현황"},{id:"disposals",label:"철회·파기 이력"}] },
  { id: "reports", label: "통계·보고서", icon: <FileText/>, tab: "reports" },
  { id: "system", label: "시스템 관리", icon: <LockKeyhole/>, children: [{id:"admins",label:"관리자 계정·권한"},{id:"audits",label:"보안감사 로그"}] },
];
const adminTabLabel = Object.fromEntries(adminMenuGroups.flatMap(group => group.tab ? [[group.tab, group.label]] : (group.children ?? []).map(item => [item.id, item.label]))) as Record<AdminTab,string>;

const adminValue = (value: unknown) => value == null || value === "" ? "-" : typeof value === "boolean" ? (value ? "예" : "아니요") : Array.isArray(value) ? value.join(", ") : String(value);
const formatAdminDate = (value: unknown) => value ? new Date(String(value)).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) : "-";

function AdminDataTable({ rows, columns, query, onSelect }: { rows: AdminRow[]; columns: { key: string; label: string; date?: boolean }[]; query: string; onSelect: (row: AdminRow) => void }) {
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
  return <div className="admin-data-table"><div className="admin-data-head">{columns.map((column) => <span key={column.key}>{column.label}</span>)}</div>{filtered.length ? filtered.slice(0, 200).map((row, index) => <button className="admin-data-row" key={row.id ?? index} style={{gridTemplateColumns:`repeat(${columns.length}, minmax(120px, 1fr))`}} onClick={() => onSelect(row)}>{columns.map((column) => <span key={column.key}>{column.date ? formatAdminDate(row[column.key]) : adminValue(row[column.key])}</span>)}</button>) : <p className="empty-state">조회 결과가 없습니다.</p>}</div>;
}

function AdminPage({ isAdmin, adminName, onLogout }: { isAdmin: boolean; adminName: string; onLogout: () => void }) {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [tab, setTab] = useState<AdminTab>("dashboard");
  const [expandedGroups, setExpandedGroups] = useState<string[]>(["users", "security", "privacy", "system"]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<AdminRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = async () => { if (!isAdmin) return; setLoading(true); try { setData(await apiGet<AdminOverview>("/api/v1/admin/overview")); setError(""); } catch (reason) { if (reason instanceof Error && reason.message === "Request failed with 404") { setData(emptyAdminOverview()); setError(""); } else setError(userMessage(reason)); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, [isAdmin]);
  if (!isAdmin) return <div className="admin-access-denied"><LockKeyhole/><h1>관리자 전용 페이지입니다</h1><p>관리자 계정으로 다시 로그인해 주세요.</p></div>;
  const config: Record<Exclude<AdminTab, "dashboard" | "reports">, { title: string; description: string; rows: AdminRow[]; columns: { key: string; label: string; date?: boolean }[] }> = {
    seniors: { title: "어르신 사용자", description: "보호 대상의 가입·단말·보호 활성 상태를 확인합니다.", rows: data?.seniors ?? [], columns: [{key:"id",label:"사용자 번호"},{key:"name",label:"성명"},{key:"phone",label:"휴대전화"},{key:"protection_status",label:"보호 상태"},{key:"device_status",label:"단말 상태"},{key:"family_count",label:"등록 가족"},{key:"created_at",label:"가입일",date:true}] },
    family: { title: "가족 사용자", description: "가족 관계, 본인인증과 어르신 연결 상태를 조회합니다.", rows: data?.family_members ?? [], columns: [{key:"id",label:"가족 번호"},{key:"name",label:"성명"},{key:"relation",label:"관계"},{key:"phone",label:"휴대전화"},{key:"verified",label:"본인인증"},{key:"connection_status",label:"연결 상태"},{key:"trust_level",label:"신뢰등급"}] },
    auth: { title: "가족 인증정보 등록상태", description: "원본을 열람하지 않고 음성·얼굴 특징정보와 품질 상태만 확인합니다.", rows: data?.family_members ?? [], columns: [{key:"name",label:"가족"},{key:"voice_status",label:"음성 등록"},{key:"voice_samples",label:"샘플 수"},{key:"voice_duration_ms",label:"녹음 길이(ms)"},{key:"voice_quality",label:"음성 품질"},{key:"face_status",label:"얼굴 등록"},{key:"face_quality",label:"얼굴 품질"},{key:"consent",label:"동의"}] },
    calls: { title: "통화 분석·위험 판정 이력", description: "특허 처리 단계의 분석 결과와 최종 조치를 사건번호로 추적합니다.", rows: data?.calls ?? [], columns: [{key:"id",label:"사건번호"},{key:"started_at",label:"통화 시각",date:true},{key:"senior",label:"어르신"},{key:"caller",label:"발신번호"},{key:"speaker_similarity",label:"음성 유사도"},{key:"spoof_probability",label:"합성 의심도"},{key:"risk_score",label:"위험점수"},{key:"risk_level",label:"등급"},{key:"action",label:"최종 조치"}] },
    actions: { title: "경고·차단·알림 이력", description: "위험 판정 이후 조치의 성공·실패 결과를 확인합니다.", rows: [...(data?.actions ?? []), ...(data?.notifications ?? [])], columns: [{key:"case_id",label:"사건번호"},{key:"type",label:"조치 유형"},{key:"status",label:"상태"},{key:"failure_reason",label:"실패 사유"},{key:"requested_at",label:"요청 시각",date:true},{key:"executed_at",label:"처리 시각",date:true}] },
    confirmations: { title: "가족 확인 응답", description: "미응답 요청과 가족 응답 이후 시스템 조치를 점검합니다.", rows: data?.confirmations ?? [], columns: [{key:"case_id",label:"사건번호"},{key:"channel",label:"확인 방법"},{key:"status",label:"상태"},{key:"response",label:"응답 결과"},{key:"requested_at",label:"요청 시각",date:true},{key:"responded_at",label:"응답 시각",date:true}] },
    incidents: { title: "신고·사건 관리", description: "실제 위험·오탐·미탐으로 분류할 통화 사건을 추적합니다.", rows: (data?.calls ?? []).filter(row => ["HIGH","CRITICAL"].includes(String(row.risk_level))), columns: [{key:"id",label:"사건번호"},{key:"started_at",label:"접수 시각",date:true},{key:"senior",label:"관련 사용자"},{key:"risk_level",label:"신고 유형"},{key:"decision",label:"처리 단계"},{key:"action",label:"조치 결과"}] },
    consents: { title: "개인정보 동의 현황", description: "사용자별 동의 유형·버전·동의 여부를 조회합니다.", rows: data?.consents ?? [], columns: [{key:"user",label:"사용자"},{key:"type",label:"동의 항목"},{key:"version",label:"버전"},{key:"accepted",label:"동의 상태"},{key:"created_at",label:"처리 시각",date:true}] },
    disposals: { title: "철회·파기 이력", description: "철회된 동의와 삭제된 음성·얼굴 등록 상태를 확인합니다.", rows: [...(data?.consents ?? []).filter(row=>row.accepted===false), ...(data?.family_members ?? []).filter(row=>row.voice_status==="DELETED"||row.face_status==="DELETED")], columns: [{key:"id",label:"요청번호"},{key:"user",label:"사용자"},{key:"type",label:"대상"},{key:"accepted",label:"상태"},{key:"created_at",label:"처리 시각",date:true}] },
    admins: { title: "관리자 계정·권한", description: "등록된 관리자 계정과 역할을 확인합니다. 비밀번호는 표시하지 않습니다.", rows: data?.admins ?? [], columns: [{key:"admin_id",label:"관리자 ID"},{key:"name",label:"이름"},{key:"role",label:"역할"},{key:"created_at",label:"생성일",date:true}] },
    audits: { title: "관리자 작업·보안감사 로그", description: "감사 로그는 조회만 가능하며 수정하거나 삭제할 수 없습니다.", rows: data?.audits ?? [], columns: [{key:"actor",label:"관리자"},{key:"action",label:"작업"},{key:"resource_type",label:"대상 유형"},{key:"resource_id",label:"대상 ID"},{key:"created_at",label:"작업 시각",date:true}] },
  };
  const downloadCsv = () => { const item = tab === "reports" ? config.calls : config[tab as Exclude<AdminTab,"dashboard"|"reports">]; if (!item) return; const csv = [item.columns.map(c=>c.label), ...item.rows.map(row=>item.columns.map(c=>adminValue(row[c.key])))].map(line=>line.map(value=>`"${value.split('"').join('""')}"`).join(",")).join("\n"); const link=document.createElement("a"); link.href=URL.createObjectURL(new Blob(["\uFEFF",csv],{type:"text/csv;charset=utf-8"})); link.download=`soricall-${tab}-${new Date().toISOString().slice(0,10)}.csv`; link.click(); URL.revokeObjectURL(link.href); };
  const selectTab = (next: AdminTab) => { setTab(next); setQuery(""); setSelected(null); };
  const currentItem = tab === "dashboard" || tab === "reports" ? null : config[tab];
  return <div className="admin-console">
    <aside className="admin-sidebar">
      <div className="admin-sidebar-brand"><span><Shield/></span><div><b>SoriCall Admin</b><small>안심소리 가족콜 운영 콘솔</small></div></div>
      <nav className="admin-menu-tree">{adminMenuGroups.map(group => {
        const expanded = expandedGroups.includes(group.id);
        return <div className="admin-menu-group" key={group.id}>
          <button className={group.tab === tab ? "active" : ""} onClick={() => group.tab ? selectTab(group.tab) : setExpandedGroups(current => expanded ? current.filter(id => id !== group.id) : [...current, group.id])}>{group.icon}<span>{group.label}</span>{group.children && <ChevronRight className={expanded ? "expanded" : ""}/>}</button>
          {group.children && expanded && <div className="admin-submenu">{group.children.map(item => <button className={tab === item.id ? "active" : ""} key={item.id} onClick={() => selectTab(item.id)}><i/>{item.label}</button>)}</div>}
        </div>;
      })}</nav>
      <div className="admin-sidebar-account"><span><CircleUserRound/></span><div><b>{adminName}</b><small>최고관리자</small></div></div>
    </aside>
    <section className="admin-workspace">
      <header className="admin-content-header"><div><h1>{adminTabLabel[tab]}</h1><p>{new Date().toLocaleDateString("ko-KR")} · {adminName} · 개인정보 접근 기록 대상</p></div><div><button className="secondary" onClick={() => void load()}><Activity/>새로고침</button><button className="admin-logout-button" onClick={onLogout}>로그아웃</button></div></header>
      {error && <div className="inline-api-error"><span>{error}</span></div>}
      {tab === "dashboard" && <><div className="admin-metric-grid"><Stat icon={<CircleUserRound/>} value={String(data?.metrics.seniors??0)} label="전체 어르신"/><Stat icon={<Users/>} value={String(data?.metrics.family_members??0)} label="등록 가족"/><Stat icon={<Mic/>} value={`${data?.metrics.voice_rate??0}%`} label="음성 등록률"/><Stat icon={<Video/>} value={`${data?.metrics.face_rate??0}%`} label="얼굴 등록률"/><Stat icon={<PhoneCall/>} value={String(data?.metrics.calls??0)} label="분석 통화"/><Stat icon={<ShieldAlert/>} value={String(data?.metrics.danger_calls??0)} label="위험·긴급" tone="orange"/><Stat icon={<PhoneOff/>} value={String(data?.metrics.blocked_calls??0)} label="자동 차단" tone="red"/><Stat icon={<Bell/>} value={String(data?.metrics.pending_confirmations??0)} label="미응답 확인" tone="orange"/></div><div className="admin-card"><h3>최근 위험 통화</h3><AdminDataTable rows={(data?.calls??[]).slice(0,10)} query="" onSelect={setSelected} columns={config.calls.columns}/></div></>}
      {tab === "reports" && <><div className="admin-page-title"><div><span>ADM-070</span><h1>운영 통계</h1><p>개인정보가 마스킹된 통화 현황을 출력합니다.</p></div><button className="primary" onClick={downloadCsv}>CSV 다운로드</button></div><div className="admin-metric-grid"><Stat icon={<PhoneCall/>} value={String(data?.metrics.calls??0)} label="분석 통화"/><Stat icon={<ShieldAlert/>} value={String(data?.metrics.danger_calls??0)} label="위험 통화" tone="orange"/><Stat icon={<Mic/>} value={`${data?.metrics.voice_rate??0}%`} label="음성 등록률"/><Stat icon={<Video/>} value={`${data?.metrics.face_rate??0}%`} label="얼굴 등록률"/></div></>}
      {currentItem && <><div className="admin-section-heading"><div><h2>{currentItem.title}</h2><p>{currentItem.description}</p></div><button className="secondary" onClick={downloadCsv}>CSV</button></div><div className="admin-toolbar"><div><Search/><input placeholder="검색" value={query} onChange={event=>setQuery(event.target.value)}/></div><span>최대 200건 표시 · 개인정보 마스킹</span></div><AdminDataTable rows={currentItem.rows} columns={currentItem.columns} query={query} onSelect={setSelected}/></>}
      {loading && <div className="admin-loading">관리자 데이터를 불러오는 중입니다…</div>}
    </section>
    {selected && <div className="admin-detail-drawer"><button onClick={()=>setSelected(null)} aria-label="상세 닫기"><X/></button><span>상세 정보</span><h2>{adminValue(selected.id??"선택 항목")}</h2><div>{Object.entries(selected).map(([key,value])=><p key={key}><b>{key}</b><span>{key.includes("at")?formatAdminDate(value):adminValue(value)}</span></p>)}</div><small><Shield/> 원본 음성·얼굴 및 전체 전화번호는 제공하지 않습니다.</small></div>}
  </div>;
}

function FormCard({ step, title, description, children }: { step?: string; title: string; description: string; children: React.ReactNode }) { return <div className="form-wrap"><div className="form-card">{step && <span className="step">{step}</span>}<h1>{title}</h1><p className="lead">{description}</p><div className="form-content">{children}</div></div></div>; }
function Field({ label, placeholder, type="text", suffix, autoComplete, value, onChange }: { label: string; placeholder: string; type?: string; suffix?: string; autoComplete?: string; value?:string; onChange?:(value:string)=>void }) { return <label className="field"><span>{label}</span><div><input type={type} autoComplete={autoComplete} placeholder={placeholder} value={value} onChange={e => onChange?.(e.target.value)}/>{suffix && <button type="button">{suffix}</button>}</div></label>; }
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
