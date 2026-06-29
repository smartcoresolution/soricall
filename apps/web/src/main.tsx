import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Headphones,
  History,
  PhoneCall,
  RefreshCcw,
  ShieldCheck,
  Users,
} from "lucide-react";
import {
  ApiHealth,
  CallEvaluation,
  EmergencyNotification,
  RiskEvent,
  VoiceProfile,
  apiGet,
  apiPost,
} from "./api";
import "./styles.css";

type DemoState = {
  familyId: string;
  seniorId: string;
  familyMemberId: string;
  voiceProfileId: string;
};

const defaultDemoState: DemoState = {
  familyId: "",
  seniorId: "",
  familyMemberId: "",
  voiceProfileId: "",
};

function App() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [demo, setDemo] = useState<DemoState>(defaultDemoState);
  const [phoneNumber, setPhoneNumber] = useState("+821077770000");
  const [callEvaluation, setCallEvaluation] = useState<CallEvaluation | null>(null);
  const [riskEvents, setRiskEvents] = useState<RiskEvent[]>([]);
  const [notifications, setNotifications] = useState<EmergencyNotification[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [status, setStatus] = useState("준비됨");
  const [error, setError] = useState<string | null>(null);

  const latestRiskEvent = useMemo(() => riskEvents[0], [riskEvents]);

  async function run<T>(label: string, task: () => Promise<T>): Promise<T | null> {
    setStatus(label);
    setError(null);
    try {
      const result = await task();
      setStatus("완료");
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "알 수 없는 오류";
      setError(message);
      setStatus("오류");
      return null;
    }
  }

  async function refreshHealth() {
    await run("API 상태 확인 중", async () => {
      const result = await apiGet<ApiHealth>("/health");
      setHealth(result);
      return result;
    });
  }

  async function createDemoData() {
    await run("데모 데이터 생성 중", async () => {
      const suffix = Math.random().toString(16).slice(2);
      const guardian = await apiPost<{ user: { id: string } }>("/api/v1/auth/register", {
        email: `guardian-${suffix}@example.com`,
        password: "password123",
        display_name: "데모 보호자",
        role: "GUARDIAN",
      });
      const family = await apiPost<{ id: string }>("/api/v1/families", {
        name: "데모 가족",
        created_by: guardian.user.id,
      });
      const familyMember = await apiPost<{ id: string }>(`/api/v1/families/${family.id}/members`, {
        name: "김민수",
        relation: "아들",
        phone_number: "+821012345678",
      });
      const senior = await apiPost<{ id: string }>("/api/v1/seniors", {
        family_id: family.id,
        name: "김영희",
        phone_number: "+821099998888",
        birth_year: 1948,
      });
      await apiPost(`/api/v1/seniors/${senior.id}/guardians`, {
        user_id: guardian.user.id,
        relation: "딸",
      });
      await apiPost(`/api/v1/families/${family.id}/safe-word`, {
        word: "청포도",
        hint: "우리 가족 과일",
      });
      await apiPost("/api/v1/admin/risk-numbers", {
        phone_number: "+821077770000",
        label: "데모 위험번호",
        risk_score: 90,
      });
      const voiceProfile = await apiPost<{ id: string }>("/api/v1/voice-profiles", {
        family_member_id: familyMember.id,
        display_name: "김민수 목소리",
      });
      await apiPost(`/api/v1/voice-profiles/${voiceProfile.id}/samples`, {
        audio_ref: "family-clean-sample.wav",
        object_key: "demo/family-clean-sample.wav",
        duration_ms: 5000,
        sample_rate: 16000,
        mime_type: "audio/wav",
      });
      await apiPost(`/api/v1/voice-profiles/${voiceProfile.id}/enroll`, {
        audio_ref: "family-clean-sample.wav",
      });
      const nextDemo = {
        familyId: family.id,
        seniorId: senior.id,
        familyMemberId: familyMember.id,
        voiceProfileId: voiceProfile.id,
      };
      setDemo(nextDemo);
      await refreshLists(nextDemo);
      return nextDemo;
    });
  }

  async function evaluateCall() {
    if (!demo.seniorId) {
      setError("먼저 데모 데이터를 생성하세요.");
      return;
    }
    await run("전화 위험도 평가 중", async () => {
      const result = await apiPost<CallEvaluation>("/api/v1/calls/evaluate", {
        senior_id: demo.seniorId,
        phone_number: phoneNumber,
        direction: "INCOMING",
      });
      setCallEvaluation(result);
      await refreshLists(demo);
      return result;
    });
  }

  async function notifyGuardians() {
    if (!latestRiskEvent) {
      setError("먼저 위험 이벤트를 생성하세요.");
      return;
    }
    await run("보호자 알림 생성 중", async () => {
      await apiPost("/api/v1/emergency/notify", {
        risk_event_id: latestRiskEvent.id,
        message: "부모님이 가족 사칭 의심 전화를 받고 있습니다.",
      });
      await refreshLists(demo);
    });
  }

  async function refreshLists(currentDemo = demo) {
    const [events, emergency, voices] = await Promise.all([
      apiGet<RiskEvent[]>(
        currentDemo.seniorId ? `/api/v1/risk-events?senior_id=${currentDemo.seniorId}` : "/api/v1/risk-events",
      ),
      apiGet<EmergencyNotification[]>("/api/v1/emergency/notifications"),
      apiGet<VoiceProfile[]>(
        currentDemo.familyMemberId
          ? `/api/v1/voice-profiles?family_member_id=${currentDemo.familyMemberId}`
          : "/api/v1/voice-profiles",
      ),
    ]);
    setRiskEvents(events.slice().reverse());
    setNotifications(emergency.slice().reverse());
    setVoiceProfiles(voices);
  }

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">SoriCall Web Console</p>
          <h1>안심소리 가족콜</h1>
        </div>
        <button className="icon-button" onClick={() => refreshHealth()} title="새로고침">
          <RefreshCcw size={20} />
        </button>
      </section>

      <section className="status-strip">
        <StatusPill icon={<ShieldCheck size={18} />} label="API" value={health?.status ?? "확인 중"} />
        <StatusPill icon={<CheckCircle2 size={18} />} label="Service" value={health?.service ?? "-"} />
        <StatusPill icon={<Bell size={18} />} label="작업 상태" value={status} />
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="workspace">
        <Panel title="데모 설정" icon={<Users size={22} />}>
          <p className="panel-copy">
            개발용 가족, 어르신, 보호자, 위험번호, 음성 프로필을 한 번에 생성합니다.
          </p>
          <button className="primary-button" onClick={createDemoData}>
            데모 데이터 생성
          </button>
          <dl className="details">
            <div>
              <dt>Senior ID</dt>
              <dd>{demo.seniorId || "-"}</dd>
            </div>
            <div>
              <dt>Voice Profile</dt>
              <dd>{demo.voiceProfileId || "-"}</dd>
            </div>
          </dl>
        </Panel>

        <Panel title="전화 위험 평가" icon={<PhoneCall size={22} />}>
          <label className="field-label" htmlFor="phone">
            수신 번호
          </label>
          <input
            id="phone"
            className="text-input"
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
          />
          <button className="primary-button" onClick={evaluateCall}>
            위험도 평가
          </button>
          {callEvaluation && (
            <div className={`risk-box risk-${callEvaluation.risk_level.toLowerCase()}`}>
              <strong>{callEvaluation.risk_level}</strong>
              <span>{callEvaluation.risk_score}점</span>
              <p>{callEvaluation.message_for_senior}</p>
            </div>
          )}
        </Panel>

        <Panel title="보호자 알림" icon={<Bell size={22} />}>
          <p className="panel-copy">최근 위험 이벤트를 보호자 알림으로 보냅니다.</p>
          <button className="secondary-button" onClick={notifyGuardians}>
            보호자 알림 생성
          </button>
          <List
            items={notifications}
            empty="알림 없음"
            render={(item) => (
              <>
                <strong>{item.status}</strong>
                <span>{item.message ?? "-"}</span>
              </>
            )}
          />
        </Panel>

        <Panel title="위험 이력" icon={<History size={22} />}>
          <List
            items={riskEvents}
            empty="위험 이력 없음"
            render={(item) => (
              <>
                <strong>
                  {item.risk_level} · {item.risk_score}점
                </strong>
                <span>{item.summary ?? item.event_type}</span>
              </>
            )}
          />
        </Panel>

        <Panel title="음성 프로필" icon={<Headphones size={22} />}>
          <List
            items={voiceProfiles}
            empty="음성 프로필 없음"
            render={(item) => (
              <>
                <strong>{item.display_name}</strong>
                <span>
                  {item.status} · 품질 {item.quality_score ?? "-"}
                </span>
              </>
            )}
          />
        </Panel>

        <Panel title="주의 신호" icon={<AlertTriangle size={22} />}>
          <ul className="signals">
            <li>모르는 번호에서 가족이라고 주장</li>
            <li>송금, 앱 설치, 링크 클릭 요구</li>
            <li>전화를 끊지 말라고 압박</li>
            <li>저장된 가족 번호로 다시 확인</li>
          </ul>
        </Panel>
      </section>
    </main>
  );
}

function StatusPill({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="status-pill">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <article className="panel">
      <header className="panel-header">
        {icon}
        <h2>{title}</h2>
      </header>
      {children}
    </article>
  );
}

function List<T>({ items, empty, render }: { items: T[]; empty: string; render: (item: T) => React.ReactNode }) {
  if (!items.length) {
    return <p className="empty">{empty}</p>;
  }
  return (
    <ul className="list">
      {items.map((item, index) => (
        <li key={index}>{render(item)}</li>
      ))}
    </ul>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

