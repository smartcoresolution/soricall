import { expect, test } from "@playwright/test";

const output = "/home/soricall/artifacts/user-test-screens";
const auth = {
  access_token: "preview-access", refresh_token: "preview-refresh", token_type: "bearer",
  family_id: "family-1", senior_id: "senior-1",
  user: { id: "user-1", email: null, display_name: "김영희", role: "SENIOR", phone_number: "010-1234-5678" },
};
const contact = {
  id: "contact-1", family_id: "family-1", protected_user_id: "senior-1", name: "김민지",
  member_type: "FAMILY_CONFIRMATION_CONTACT", relation_code: "DAUGHTER",
  phone_number_last4: "4421", is_primary_contact: true, notification_priority: 1,
  notify_enabled: true, approval_status: "INVITED", trust_level: "D",
};

test("사용자 테스트용 전체 화면 이미지", async ({ page }) => {
  await page.route("**/api/v1/**", async route => {
    const url = route.request().url();
    const method = route.request().method();
    let body: unknown = {};
    if (url.includes("/auth/phone-verifications/confirm")) body = { verification_token: "verified-token" };
    else if (url.includes("/auth/phone-verifications")) body = { verification_id: "verify-1", expires_in: 300, development_code: "123456" };
    else if (url.includes("/auth/register") || url.includes("/auth/login")) body = auth;
    else if (url.endsWith("/api/v1/families") && method === "GET") body = [];
    else if (url.endsWith("/api/v1/families") && method === "POST") body = { id: "family-1", name: "김영희 통화보호 가족", created_by: "user-1" };
    else if (url.includes("/confirmation-contacts") && method === "POST") body = contact;
    else if (url.includes("/enrollment-invitations") && method === "POST") body = {
      id: "invite-1", family_id: "family-1", family_member_id: "contact-1",
      family_member_name: "김민지", relation_code: "DAUGHTER", phone_number_last4: "4421",
      channel: "DEVELOPMENT_LINK", requested_assets: ["VOICE", "FACE"], status: "PENDING",
      sent_at: new Date().toISOString(), expires_at: new Date(Date.now() + 86400000).toISOString(),
      enrollment_url: "/soricall/enroll?token=preview-token", member_approval_status: "INVITED",
      member_trust_level: "D", phone_verified: false,
    };
    else if (url.includes("/enrollment-invitations")) body = [];
    else if (url.includes("/protected-call-users")) body = [];
    else if (url.includes("/members")) body = [];
    else if (url.includes("/voice-profiles") || url.includes("/face-profiles")) body = [];
    await route.fulfill({ status: method === "POST" ? 201 : 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  const shot = async (name: string) => {
    await page.screenshot({ path: `${output}/${name}.png`, fullPage: true });
  };

  await page.goto("/");
  await shot("01-start");
  await page.getByRole("button", { name: /회원가입/ }).click();
  await shot("02-signup-empty");
  await page.getByLabel("이름").fill("김영희");
  await page.getByLabel("본인 휴대전화 번호").fill("010-1234-5678");
  await page.getByRole("button", { name: "인증번호 받기" }).click();
  await page.getByRole("button", { name: "인증 확인" }).click();
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await shot("03-signup-verified");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await shot("04-consent");
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();
  await shot("05-signup-complete");
  await page.getByRole("button", { name: "서비스 시작" }).click();
  await page.getByLabel("비밀번호").fill("password1");
  await shot("06-login");
  await page.getByRole("button", { name: "로그인" }).click();
  await shot("07-setup-choice");
  await page.getByRole("button", { name: /부모님의 전화를 보호하고 싶어요/ }).click();
  await shot("08-protected-family");
  await page.getByRole("button", { name: /^홈$/ }).click();
  await page.getByRole("button", { name: "서비스 시작" }).click();
  await page.getByLabel("휴대전화 번호").fill("010-1234-5678");
  await page.getByLabel("비밀번호").fill("password1");
  await page.getByRole("button", { name: "로그인" }).click();
  await page.getByRole("button", { name: /내 전화를 보호받고 싶어요/ }).click();
  await page.getByRole("button", { name: "딸", exact: true }).click();
  await page.getByLabel("성함").fill("김민지");
  await page.getByLabel("휴대전화 번호").fill("010-9876-4421");
  await shot("09-confirmation-contact");
  await page.getByRole("button", { name: /이 가족 추가하기/ }).click();
  await page.getByRole("button", { name: "가족 등록 완료 · 음성·얼굴 등록" }).click();
  await shot("10-registration-plan");
  await page.getByRole("button", { name: "다음: 등록 요청 보내기" }).click();
  await shot("11-invitation-methods");
  await page.getByRole("button", { name: "문자 앱으로 보내기" }).click();
  await expect(page.getByRole("heading", { name: "가족 등록 현황" })).toBeVisible();
  await shot("12-enrollment-status");
  await page.getByRole("button", { name: "홈", exact: true }).click();
  await shot("13-home-dashboard");
  await page.getByText("등록된 가족 전화", { exact: true }).click();
  await shot("14-safe-call");
  await page.getByRole("button", { name: /통화 계속하기/ }).click();
  await page.getByText("가족 사칭 의심전화", { exact: true }).click();
  await shot("15-suspicious-analysis");
  await page.getByRole("button", { name: /지금 통화 끊기/ }).click();
  await shot("16-blocked-call");
  await page.getByRole("button", { name: /확인 가족에게 요청/ }).click();
  await shot("17-family-confirmation");
  await page.getByRole("button", { name: /네, 제가 전화했어요/ }).click();
  await shot("18-history");
  await page.getByRole("button", { name: "관리" }).click();
  await shot("19-admin");
});
