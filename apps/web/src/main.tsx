import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactDOM from "react-dom/client";
import QRCode from "qrcode";
import {
  Activity, AlertTriangle, ArrowLeft, Bell, Check, CheckCircle2, ChevronRight,
  CircleUserRound, Clock3, Download, FileClock, HeartHandshake, Home, LockKeyhole, Mic,
  Pause, Phone, PhoneCall, PhoneOff, Play, Plus, Settings, Shield, ShieldAlert,
  Trash2, UserPlus, UserRoundCheck, Users, Video, Volume2, X,
} from "lucide-react";
import { apiDelete, apiGet, apiPost, setApiAccessToken, type Family, type UserPublic } from "./api";
import "./styles.css";
import "./feedback.css";

type Screen =
  | "welcome" | "parentConnect" | "setupChoice" | "selfPhone" | "signup" | "consent" | "signupComplete" | "login" | "home" | "protected"
  | "contacts" | "deviceInvite" | "registrationPlan" | "invite" | "enrollmentStatus" | "enrollmentVerify" | "biometrics" | "normal" | "analysis" | "blocked"
  | "faceRegistration" | "parentAppInstall" | "enrollmentComplete" | "confirm" | "history" | "admin";

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
type ProtectedUserResponse = { id: string; name?: string; relation_code?: string; phone_number_last4?: string | null; protection_status?: string };
type RegisteredProtectedFamily = { id: string; name: string; relation: string; phoneLast4: string; status?: string };
type ConfirmationContactResponse = { id: string; name: string; relation_code?: string | null; phone_number_last4?: string | null; approval_status?: string; trust_level?: string };
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
};
type DeviceEnrollment = { id: string; protected_user_id: string; protected_user_name: string; phone_number_last4: string | null; status: string; enrollment_url: string | null };
const SESSION_STORAGE_KEY = "soricall.dev.session";
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

function userMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message === "phone number already registered") return "이미 가입된 휴대전화 번호입니다.";
  if (message === "invalid phone number or password") return "휴대전화 번호 또는 비밀번호가 올바르지 않습니다.";
  if (message === "invalid phone verification code") return "인증번호가 올바르지 않습니다.";
  if (message === "phone verification expired") return "인증번호 유효시간이 지났습니다. 다시 받아 주세요.";
  if (message === "authentication required") return "로그인이 필요합니다.";
  if (message === "family access denied") return "이 가족 정보에 접근할 권한이 없습니다.";
  if (message === "invitation expired") return "등록 링크의 유효기간이 지났습니다. 초대한 가족에게 새 링크를 요청해 주세요.";
  if (message === "invitation not found") return "유효하지 않은 등록 링크입니다.";
  return message || "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
}

const isValidMobilePhone = (value: string) => /^01[016789]-?\d{3,4}-?\d{4}$/.test(value.trim());

function App() {
  const enrollmentToken = new URLSearchParams(window.location.search).get("token");
  const query = new URLSearchParams(window.location.search);
  const tokenFromLink = query.get("device_token");
  if (tokenFromLink) window.localStorage.setItem("soricall_device_enrollment_token", tokenFromLink);
  const deviceToken = tokenFromLink ?? (query.get("resume_device_enrollment") === "1"
    ? window.localStorage.getItem("soricall_device_enrollment_token")
    : null);
  const missingResumeToken = query.get("resume_device_enrollment") === "1" && !deviceToken;
  const sessionRestoreStartedRef = useRef(false);
  const newSignupStartedRef = useRef(false);
  const [screen, setScreen] = useState<Screen>(deviceToken ? "parentConnect" : enrollmentToken ? "enrollmentVerify" : "welcome");
  const [setupMode, setSetupMode] = useState<SetupMode>("helper");
  const [protectedRelation, setProtectedRelation] = useState("아버지");
  const [contactRelation, setContactRelation] = useState("딸");
  const [agreed, setAgreed] = useState([false, false, false, false, false]);
  const [analysisStep, setAnalysisStep] = useState(2);
  const [signup, setSignup] = useState({ name: "", phone: "", verificationId: "", verificationCode: "", verificationToken: "", password: "", passwordConfirm: "" });
  const [login, setLogin] = useState({ phone_number: "", password: "" });
  const [protectedForm, setProtectedForm] = useState({ name: "", phone: "" });
  const [protectedFamilies, setProtectedFamilies] = useState<RegisteredProtectedFamily[]>([]);
  const [contactForm, setContactForm] = useState({ name: "", phone: "", primary: true });
  const [session, setSession] = useState<AuthResponse | null>(null);
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
  const [inviteVerificationId, setInviteVerificationId] = useState("");
  const [inviteVerificationCode, setInviteVerificationCode] = useState("");

  const resetFamilyState = () => {
    setFamilyId(null);
    setProtectedUserId(null);
    setProtectedFamilies([]);
    setEnrollmentContact(null);
    setEnrollmentContacts([]);
    setInvitations([]);
    setParentInstallLink("");
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
      }).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (!enrollmentToken) return;
    setApiAccessToken(null);
    setBusy(true);
    apiGet<EnrollmentInvitation>(`/api/v1/enrollment-invitations/resolve?token=${encodeURIComponent(enrollmentToken)}`)
      .then((invitation) => {
        setEnrollmentContact({ id: invitation.family_member_id, name: invitation.family_member_name });
        if (invitation.status === "COMPLETED") setScreen("enrollmentComplete");
        else if (invitation.status === "EXPIRED") throw new Error("invitation expired");
        else setScreen(invitation.phone_verified ? "biometrics" : "enrollmentVerify");
      })
      .catch((error) => setApiError(userMessage(error)))
      .finally(() => setBusy(false));
  }, [enrollmentToken]);

  useEffect(() => {
    if (enrollmentToken) return;
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
  }, [enrollmentToken]);

  useEffect(() => {
    if (!session || enrollmentToken) return;
    let cancelled = false;
    const restoreFamilyState = async () => {
      try {
        const families = await apiGet<Family[]>("/api/v1/families");
        const family = families[0];
        if (!family) {
          if (!cancelled) resetFamilyState();
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
          status: item.protection_status,
        })));
        setEnrollmentContacts(contacts);
        setInvitations(restoredInvitations);
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
      setProtectedFamilies(users.map((item) => ({
        id: item.id,
        name: item.name ?? "보호 가족",
        relation: protectedRelationLabels[item.relation_code ?? ""] ?? "기타",
        phoneLast4: item.phone_number_last4 ?? "----",
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
    setFamilyId(auth.family_id ?? null);
    setProtectedUserId(auth.senior_id ?? null);
    setApiAccessToken(auth.access_token); persistSession(auth); setSession(auth);
    setScreen("setupChoice");
  });
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
    const protectedUsers = await apiGet<ProtectedUserResponse[]>(`/api/v1/families/${currentFamilyId}/protected-call-users`);
    if (protectedUsers.length === 0) {
      setScreen("protected");
      return;
    }
    setProtectedFamilies(protectedUsers.map((item) => ({
      id: item.id,
      name: item.name ?? "보호 가족",
      relation: protectedRelationLabels[item.relation_code ?? ""] ?? "기타",
      phoneLast4: item.phone_number_last4 ?? "----",
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
      setEnrollmentContacts([]);
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
    setEnrollmentContact(contact);
    setEnrollmentContacts((current) => [...current, contact]);
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
      if (enrollmentContact?.id === contact.id) setEnrollmentContact(null);
      setApiMessage(`${contact.name}님을 확인 가족에서 삭제했습니다.`);
    });
  };
  const sendEnrollmentInvitations = (channel: "LINK" | "QR" | "DIRECT" = "LINK") => runApi(async () => {
    if (!familyId || enrollmentContacts.length === 0) throw new Error("등록 요청을 보낼 가족이 없습니다.");
    const sent = await Promise.all(enrollmentContacts.map((contact) =>
      apiPost<EnrollmentInvitation>(`/api/v1/families/${familyId}/members/${contact.id}/enrollment-invitations?channel=${channel}`, {}),
    ));
    setInvitations(sent);
    setScreen("enrollmentStatus");
  });
  const resendInvitation = (invitationId: string) => runApi(async () => {
    if (!familyId) throw new Error("가족 정보가 없습니다.");
    const resent = await apiPost<EnrollmentInvitation>(`/api/v1/families/${familyId}/enrollment-invitations/${invitationId}/resend`, {});
    setInvitations((current) => current.map((item) => item.id === invitationId ? resent : item));
    setApiMessage("등록 링크를 다시 보냈습니다.");
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
  const copyEnrollmentLink = async (invitation: EnrollmentInvitation) => {
    if (!invitation.enrollment_url) {
      setApiError("사용 가능한 개발용 등록 링크가 없습니다.");
      return;
    }
    const absoluteUrl = new URL(invitation.enrollment_url, window.location.origin).toString();
    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setApiMessage("개발용 등록 링크를 복사했습니다.");
    } catch {
      setApiError(`링크를 복사하지 못했습니다: ${absoluteUrl}`);
    }
  };
  const shareEnrollmentLink = async (invitation: EnrollmentInvitation) => {
    if (!invitation.enrollment_url) return;
    const url = new URL(invitation.enrollment_url, window.location.origin).toString();
    if (navigator.share) {
      await navigator.share({ title: "SoriCall 가족 등록 요청", text: `${invitation.family_member_name}님의 음성 등록 요청입니다.`, url });
    } else {
      await navigator.clipboard.writeText(url);
      setApiMessage("공유 기능을 지원하지 않아 링크를 복사했습니다.");
    }
  };
  const sendInvitePhoneCode = () => runApi(async () => {
    if (!enrollmentToken) throw new Error("초대 정보가 없습니다.");
    const sent = await apiPost<{ verification_id: string; development_code?: string | null }>(
      `/api/v1/enrollment-invitations/phone-verification?token=${encodeURIComponent(enrollmentToken)}`,
      { phone_number: invitePhone },
    );
    setInviteVerificationId(sent.verification_id);
    setInviteVerificationCode(sent.development_code ?? "");
    setApiMessage(sent.development_code ? `개발용 인증번호: ${sent.development_code}` : "인증번호를 문자로 보냈습니다.");
  });
  const confirmInvitePhoneCode = () => runApi(async () => {
    if (!enrollmentToken) throw new Error("초대 정보가 없습니다.");
    await apiPost(
      `/api/v1/enrollment-invitations/phone-verification/confirm?token=${encodeURIComponent(enrollmentToken)}`,
      { verification_id: inviteVerificationId, code: inviteVerificationCode },
    );
    setScreen("biometrics");
  });
  const saveBiometrics = (audioRef: string, durationMs: number, faceImageRef: string | null) => runApi(async () => {
    if (!enrollmentContact) throw new Error("음성을 등록할 확인 가족 정보가 없습니다.");
    if (enrollmentToken) {
      await apiPost<EnrollmentInvitation>(`/api/v1/enrollment-invitations/complete?token=${encodeURIComponent(enrollmentToken)}`, {
        audio_ref: audioRef,
        duration_ms: durationMs,
        mime_type: "audio/webm",
        face_image_ref: faceImageRef,
        consent_accepted: true,
      });
      setScreen("enrollmentComplete");
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
    const enrollment = await apiPost<DeviceEnrollment>(`/api/v1/families/${familyId}/protected-call-users/${family.id}/device-enrollment`, {});
    const link = new URL(enrollment.enrollment_url ?? "", window.location.origin);
    const shareData = {
      title: "SoriCall 통화 보호 앱 설치",
      text: `${family.name}님, 아래 링크를 열어 SoriCall 앱을 설치하고 통화 보호를 켜 주세요.`,
      url: link.toString(),
    };
    try {
      if (navigator.share) await navigator.share(shareData);
      else {
        await navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`);
        setApiMessage("앱 설치 안내를 복사했습니다.");
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setApiError("앱 설치 안내를 공유하지 못했습니다. 다시 시도해 주세요.");
    }
  };
  const openFamilyEnrollment = (invitation: EnrollmentInvitation) => {
    if (!invitation.enrollment_url) throw new Error("사용 가능한 개발용 등록 링크가 없습니다.");
    window.open(invitation.enrollment_url, "_blank", "noopener,noreferrer");
  };

  const title = useMemo(() => ({
    parentConnect: "부모님 통화 보호 연결", setupChoice: "보호 방법 선택", selfPhone: "본인 휴대전화 확인", signup: "회원가입", consent: "서비스 이용 동의", signupComplete: "가입 완료", login: "로그인",
    protected: "가족 등록", contacts: "확인 가족 등록", deviceInvite: "부모님 앱 연결", registrationPlan: "등록 항목 안내", invite: "등록 요청 보내기",
    enrollmentStatus: "가족 등록 현황", enrollmentVerify: "초대 가족 본인 확인", biometrics: setupMode === "helper" ? "자녀 음성 등록" : "가족 본인 등록", faceRegistration: "얼굴 등록", parentAppInstall: "부모님 앱 설치", enrollmentComplete: "등록 완료", normal: "안전한 전화", analysis: "의심전화 분석",
    blocked: "고위험 전화 차단", confirm: "가족 확인 요청", history: "통화기록",
    admin: "관리자 페이지", home: "통화 보호 홈", welcome: "",
  }[screen]), [screen]);

  const goBack = () => {
    const previous: Partial<Record<Screen, Screen>> = {
      signup: "welcome",
      login: "welcome",
      consent: "signup",
      setupChoice: "login",
      selfPhone: "setupChoice",
      protected: "setupChoice",
      contacts: "protected",
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

  return (
    <div className="site-shell">
      {screen !== "welcome" && <header className="topbar">
        <button className="brand" onClick={goWelcome}>
          <span className="brand-mark"><Shield size={22} /></span>
          <span>SoriCall<small>안심소리 가족콜</small></span>
        </button>
        <div className="top-title">{title}</div>
        <div className="top-actions">
          <button className="screen-home-button" onClick={goWelcome}><Home size={19} /> 홈</button>
        </div>
      </header>}

      <main className={`page ${screen === "welcome" ? "welcome-page" : ""}`}>
        {screen !== "welcome" && screen !== "home" && screen !== "signupComplete" && (
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
        {screen === "invite" && <EnrollmentInvite contacts={enrollmentContacts} onSend={sendEnrollmentInvitations} />}
        {screen === "enrollmentStatus" && <EnrollmentStatus invitations={invitations} onResend={resendInvitation} onOpen={openFamilyEnrollment} onCopy={copyEnrollmentLink} onShare={shareEnrollmentLink} onApprove={approveEnrollment} onHome={() => setScreen("home")} />}
        {screen === "enrollmentVerify" && <EnrollmentPhoneVerification phone={invitePhone} setPhone={setInvitePhone} verificationId={inviteVerificationId} code={inviteVerificationCode} setCode={setInviteVerificationCode} busy={busy} onSend={sendInvitePhoneCode} onConfirm={confirmInvitePhoneCode} />}
        {screen === "biometrics" && enrollmentContact && <Biometrics contactName={enrollmentContact.name} protectedFamilies={protectedFamilies} onManageTargets={() => setScreen("protected")} onDone={saveBiometrics} />}
        {screen === "faceRegistration" && enrollmentContact && <FaceRegistration contactName={enrollmentContact.name} onDone={saveFaceRegistration} />}
        {screen === "parentAppInstall" && <ParentAppInstall families={protectedFamilies} onShare={shareParentInstall} onHome={() => setScreen("home")} />}
        {screen === "enrollmentComplete" && <CallStage tone="safe" icon={<CheckCircle2 />} eyebrow="가족 본인 등록 완료" title="안전하게 등록됐어요" description="목소리와 선택한 얼굴정보가 가족 사칭 확인에 사용됩니다."><InfoBox icon={<Shield />}><b>이제 이 창을 닫아도 됩니다.</b><br/>초대한 가족의 등록 현황에 완료 상태가 표시됩니다.</InfoBox></CallStage>}
        {screen === "home" && <Dashboard navigate={setScreen} invitations={invitations} />}
        {screen === "normal" && <NormalCall onHome={() => setScreen("home")} />}
        {screen === "analysis" && <Analysis step={analysisStep} setStep={setAnalysisStep} onBlock={() => setScreen("blocked")} />}
        {screen === "blocked" && <BlockedCall onConfirm={() => setScreen("confirm")} />}
        {screen === "confirm" && <Confirmation onDone={() => setScreen("history")} />}
        {screen === "history" && <HistoryPage />}
        {screen === "admin" && <AdminPage />}
      </main>
      {screen !== "signupComplete" && ((busy && screen !== "consent" && screen !== "protected" && screen !== "setupChoice" && screen !== "login") || apiMessage || (apiError && screen !== "consent" && screen !== "login")) && <div className={`api-feedback ${apiError ? "error" : ""}`} role={apiError ? "alert" : "status"} aria-live={apiError ? "assertive" : "polite"} aria-atomic="true">{busy ? "안전하게 저장하고 있습니다…" : apiError || apiMessage}<button onClick={() => { setApiError(""); setApiMessage(""); }} aria-label="알림 닫기"><X /></button></div>}

      {!([ "welcome", "parentConnect", "setupChoice", "selfPhone", "signup", "consent", "signupComplete", "login", "protected", "contacts", "deviceInvite", "registrationPlan", "invite", "enrollmentStatus", "enrollmentVerify", "biometrics", "faceRegistration", "parentAppInstall", "enrollmentComplete", "normal", "analysis", "blocked", "confirm"] as Screen[]).includes(screen) && (
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
    ["얼굴정보 처리", false, "가족 본인 확인 정확도를 높이기 위한 선택 항목입니다. 동의하지 않아도 음성 기반 통화 보호 서비스를 이용할 수 있습니다."],
  ] as const;
  const toggle = (i: number) => setAgreed(agreed.map((v, n) => n === i ? !v : v));
  return <FormCard step="2 / 3" title="서비스 이용에 동의해 주세요" description="얼굴정보는 선택사항이며 동의하지 않아도 서비스를 이용할 수 있습니다.">
    {error && <div className="inline-api-error" role="alert"><span>{error}</span><button onClick={onClearError} aria-label="오류 닫기"><X /></button></div>}
    <button className={`agree-all ${agreed.every(Boolean) ? "checked" : ""}`} onClick={() => setAgreed(items.map(() => !agreed.every(Boolean)))}><span><Check /></span>전체 동의</button>
    <div className="consent-list">{items.map(([label, required, detail], i) => <div className={`consent-item ${expandedItem === i ? "expanded" : ""}`} key={label}><div className="consent-item-row"><button className="consent-toggle" onClick={() => toggle(i)}><span className={agreed[i] ? "check checked" : "check"}><Check /></span><b>{required ? "[필수]" : "[선택]"}</b><span>{label}</span></button><button className="consent-detail-toggle" aria-label={`항목 ${i + 1} 세부내용 ${expandedItem === i ? "닫기" : "열기"}`} onClick={() => setExpandedItem(expandedItem === i ? null : i)}><ChevronRight /></button></div>{expandedItem === i && <div className="consent-detail"><p>{detail}</p></div>}</div>)}</div>
    <button className="primary full" disabled={busy || !agreed.slice(0, 4).every(Boolean)} onClick={onNext}>{busy ? "가입 정보를 저장하는 중…" : "동의하고 계속하기"}</button>
  </FormCard>;
}

function SignupComplete({ onNext }: { onNext: () => void }) {
  return <CallStage tone="safe" icon={<CheckCircle2 />} eyebrow="회원가입 완료" title="안전하게 가입됐어요" description="이제 통화를 보호할 가족과 확인해 줄 가족을 등록해 주세요.">
    <div className="info-box"><span><Shield /></span><p><b>가입 정보가 안전하게 저장됐습니다.</b><br/>가족 등록을 마치면 통화 보호 준비가 완료됩니다.</p></div>
    <button className="primary full" onClick={onNext}>서비스 시작 <ChevronRight /></button>
  </CallStage>;
}

function Login({ value, setValue, onNext, error, onClearError }: { value:{phone_number:string;password:string}; setValue:React.Dispatch<React.SetStateAction<typeof value>>; onNext: () => void; error: string; onClearError: () => void }) { return <FormCard title="다시 만나서 반가워요" description="등록한 휴대전화 번호로 로그인해 주세요.">{error && <div className="login-error" role="alert"><div><b>{error}</b><p>입력한 휴대전화 번호와 비밀번호를 다시 확인해 주세요.<br/>비밀번호가 기억나지 않으면 ‘비밀번호 찾기’를 이용하고, 가입하지 않았다면 회원가입을 진행해 주세요.</p></div><button onClick={onClearError} aria-label="로그인 오류 닫기"><X /></button></div>}<Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={value.phone_number} onChange={phone_number => { onClearError(); setValue(v => ({...v,phone_number})); }}/><Field label="비밀번호" placeholder="비밀번호" type="password" value={value.password} onChange={password => { onClearError(); setValue(v => ({...v,password})); }}/><div className="between"><label><input type="checkbox"/> 로그인 유지</label><button className="link">비밀번호 찾기</button></div><button className="primary full" disabled={!isValidMobilePhone(value.phone_number) || !value.password} onClick={onNext}>로그인</button></FormCard>; }

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
  <div className="registration-type-card optional"><span><Video /></span><div><b>얼굴 등록</b><em>선택</em><p>영상 확인이 필요한 경우 정확도를 높이기 위한 선택 정보입니다.</p></div></div>
  <div className="enrollment-list">{contacts.map((contact) => <div className="enrollment-person" key={contact.id}><span className="person-icon">{contact.name.slice(0, 1)}</span><span><b>{contact.name}</b><small>음성 필수 · 얼굴 선택</small></span><em>요청 준비</em></div>)}</div>
  <InfoBox icon={<Shield />}><b>음성과 얼굴은 서로 다른 등록 항목으로 안내됩니다.</b><br/>얼굴 등록을 선택하지 않아도 음성 기반 통화 보호를 이용할 수 있습니다.</InfoBox>
  <button className="primary full" disabled={contacts.length === 0} onClick={onNext}>다음: 등록 요청 보내기</button>
</FormCard>; }

function EnrollmentInvite({ contacts, onSend }: { contacts: ConfirmationContactResponse[]; onSend: (channel: "LINK" | "QR" | "DIRECT") => void }) {
  return <FormCard step="3 / 3" title="가족에게 등록 요청을 보내세요" description="가족이 자신의 휴대전화에서 직접 동의하고 목소리와 얼굴을 등록합니다.">
    <InfoBox icon={<Shield />}><b>현재는 개발환경용 등록 방식입니다.</b><br/>3일 동안 유효한 링크를 만든 뒤 직접 복사해 전달합니다.</InfoBox>
    <div className="enrollment-list">{contacts.map((contact) => <div className="enrollment-person" key={contact.id}><span className="person-icon">{contact.name.slice(0, 1)}</span><span><b>{contact.name}</b><small>음성 필수 · 얼굴 선택</small></span><em>전송 준비</em></div>)}</div>
    <button className="primary full" disabled={contacts.length === 0} onClick={() => onSend("LINK")}><Bell /> 안전한 링크 보내기</button>
    <button className="secondary full" disabled={contacts.length === 0} onClick={() => onSend("QR")}>QR로 바로 연결 · 5분</button>
    <button className="secondary full" disabled={contacts.length === 0} onClick={() => onSend("DIRECT")}>옆에서 직접 등록</button>
  </FormCard>;
}

function EnrollmentStatus({ invitations, onResend, onOpen, onCopy, onShare, onApprove, onHome }: { invitations: EnrollmentInvitation[]; onResend: (id: string) => void; onOpen: (invitation: EnrollmentInvitation) => void; onCopy: (invitation: EnrollmentInvitation) => void; onShare: (invitation: EnrollmentInvitation) => void; onApprove: (invitation: EnrollmentInvitation) => void; onHome: () => void }) {
  const labels: Record<string, string> = { PENDING: "응답 대기", COMPLETED: "자료 도착", EXPIRED: "링크 만료" };
  return <FormCard title="가족 등록 현황" description="가족별 음성·얼굴 등록 진행 상태를 확인할 수 있습니다.">
    <div className="enrollment-list">{invitations.map((invitation) => { const approval = invitation.member_approval_status ?? (invitation.status === "COMPLETED" ? "REVIEW_REQUIRED" : "INVITED"); return <div className="enrollment-person status" key={invitation.id}><span className="person-icon">{invitation.family_member_name.slice(0, 1)}</span><span><b>{invitation.family_member_name}</b><small>휴대전화 끝 {invitation.phone_number_last4 ?? "----"} · 신뢰등급 {invitation.member_trust_level ?? "D"} · {invitation.channel}</small>{invitation.enrollment_url && <code className="development-link">{new URL(invitation.enrollment_url, window.location.origin).toString()}</code>}</span>{invitation.channel === "QR" && invitation.enrollment_url && invitation.status === "PENDING" && <EnrollmentQr url={new URL(invitation.enrollment_url, window.location.origin).toString()} name={invitation.family_member_name} />}<em className={approval.toLowerCase()}>{approval === "ACTIVE" ? "승인 완료" : labels[invitation.status] ?? invitation.status}</em>{approval === "REVIEW_REQUIRED" ? <button className="primary" onClick={() => onApprove(invitation)}>이 가족이 맞습니다</button> : invitation.status !== "COMPLETED" && <>{invitation.enrollment_url && <><button className="link" onClick={() => onShare(invitation)}>공유하기</button><button className="link" onClick={() => onCopy(invitation)}>링크 복사</button><button className="link" onClick={() => onOpen(invitation)}>새 창에서 열기</button></>}<button className="link" onClick={() => onResend(invitation.id)}>링크 재발급</button></>}</div>; })}</div>
    <InfoBox icon={<Bell />}><b>개발환경에서는 링크를 직접 전달해 등록 흐름을 확인합니다.</b><br/>실제 SMS 발송은 운영 전달 제공자를 연결한 뒤 활성화합니다.</InfoBox>
    <button className="primary full" onClick={onHome}>안심 홈으로 이동</button>
  </FormCard>;
}

function EnrollmentQr({ url, name }: { url: string; name: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => { void QRCode.toDataURL(url, { width: 220, margin: 2 }).then(setSrc); }, [url]);
  return src ? <img className="enrollment-qr" src={src} alt={`${name}님의 5분 한정 등록 QR`} /> : null;
}

function EnrollmentPhoneVerification({ phone, setPhone, verificationId, code, setCode, busy, onSend, onConfirm }: { phone: string; setPhone: (value: string) => void; verificationId: string; code: string; setCode: (value: string) => void; busy: boolean; onSend: () => void; onConfirm: () => void }) {
  return <FormCard title="초대받은 가족 본인 확인" description="가족 자료를 안전하게 등록하기 위해 초대받은 휴대전화 번호를 확인합니다.">
    <InfoBox icon={<Shield />}><b>초대받은 본인의 휴대전화 번호를 입력해 주세요.</b><br/>번호가 일치해야 음성과 선택 얼굴정보를 등록할 수 있습니다.</InfoBox>
    <Field label="휴대전화 번호" placeholder="010-0000-0000" type="tel" value={phone} onChange={setPhone}/>
    {!verificationId
      ? <button className="primary full" disabled={busy || !isValidMobilePhone(phone)} onClick={onSend}>인증번호 받기</button>
      : <><Field label="문자 인증번호" placeholder="6자리 인증번호" value={code} onChange={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))}/><button className="primary full" disabled={busy || code.length !== 6} onClick={onConfirm}>본인 확인하고 음성 등록</button></>}
  </FormCard>;
}

function Biometrics({ contactName, protectedFamilies, onManageTargets, onDone }: { contactName: string; protectedFamilies: RegisteredProtectedFamily[]; onManageTargets: () => void; onDone: (audioRef: string, durationMs: number, faceImageRef: string | null) => void }) {
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
    <section className="protected-target-summary"><div className="section-heading"><div><span>현재 보호 대상</span><h2>{protectedFamilies.length > 0 ? `${protectedFamilies.length}명의 전화를 보호합니다` : "보호 대상을 추가해 주세요"}</h2></div><button className="link" onClick={onManageTargets}><Plus /> 보호 대상 추가</button></div>{protectedFamilies.length > 0 && <div className="target-chip-row">{protectedFamilies.map((family) => <span className="target-chip" key={family.id}><b>{family.name}</b><small>{family.relation}</small></span>)}</div>}</section>
    <div className={`voice-recorder ${recording ? "is-recording" : ""}`}><div className="voice-script"><p>엄마, 오늘 저녁 일곱 시쯤 집에 도착하면 다시 전화드릴게요.</p><p>창문 옆 화분에 물도 주고, 따뜻한 차를 마시면서 천천히 이야기해요.</p><p>급한 일이 있어도 먼저 가족끼리 약속한 방법으로 꼭 확인해 주세요.</p></div>{recording ? <div className="recording-control"><div className="recording-meta"><b>{paused ? "녹음 일시정지" : "녹음 중"}</b><span>{elapsedSeconds}초 / 60초</span></div><div className="recording-progress"><i style={{width: `${(elapsedMs / maximumRecordingMs) * 100}%`}} /></div><div className="recording-actions"><button className="secondary" onClick={togglePause}>{paused ? <Play /> : <Pause />}{paused ? "계속 녹음" : "녹음 멈춤"}</button><button className="primary" onClick={finishRecording}><CheckCircle2 /> 녹음 끝내기</button></div></div> : <button className="primary voice-start" onClick={startRecording}><Mic /> {audioRef ? "다시 녹음" : "녹음 시작"}</button>}{audioRef && !recording && <small className="recorded-status">녹음 시간 {(durationMs / 1000).toFixed(1)}초 {durationMs >= minimumRecordingMs ? "· 음성 등록 준비 완료" : "· 15초 이상 다시 녹음해 주세요"}</small>}</div>
    {mediaError && <span className="validation-error">{mediaError}</span>}
    <button className="primary full" disabled={!audioRef || durationMs < minimumRecordingMs || recording} onClick={() => onDone(audioRef, durationMs, null)}>등록 완료하기</button>
  </FormCard>;
}

function FaceRegistration({ contactName, onDone }: { contactName: string; onDone: (faceImageRef: string | null) => void }) {
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
    <button className="secondary full" onClick={() => onDone(null)}>나중에 등록하기 · 선택사항</button>
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
  <section className="stat-grid"><Stat icon={<PhoneCall/>} value="12" label="이번 달 확인 전화"/><Stat icon={<ShieldAlert/>} value="3" label="의심전화 감지" tone="orange"/><Stat icon={<PhoneOff/>} value="1" label="고위험 차단" tone="red"/><Stat icon={<Users/>} value="2명" label="확인 가족"/></section>
  <div className="section-heading"><div><span>통화 보호 상태</span><h2>모든 준비가 완료됐어요</h2></div><button onClick={() => navigate("protected")}>관리하기 <ChevronRight/></button></div>
  <section className="ready-grid"><Ready icon={<Phone/>} title="가족 연락처" text="등록 완료 · 3개 번호"/><Ready icon={<Mic/>} title="가족 음성" text="등록 완료 · 품질 좋음"/><Ready icon={<UserRoundCheck/>} title="확인 가족" text="김민지 외 1명"/><Ready icon={<Activity/>} title="AI 위험 분석" text="정상 작동 중"/></section>
  {invitations.length > 0 && <section className="enrollment-summary"><div className="section-heading"><div><span>가족 등록 현황</span><h2>초대한 가족의 진행 상태</h2></div><button onClick={() => navigate("enrollmentStatus")}>자세히 보기 <ChevronRight/></button></div>{invitations.map((item) => <div className="enrollment-person status" key={item.id}><span className="person-icon">{item.family_member_name.slice(0, 1)}</span><span><b>{item.family_member_name}</b><small>{item.status === "COMPLETED" ? "음성·얼굴 등록 완료" : "등록 링크 응답 대기"}</small></span><em className={item.status.toLowerCase()}>{item.status === "COMPLETED" ? "등록 완료" : "응답 대기"}</em></div>)}</section>}
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
