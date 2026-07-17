import { expect, test } from "@playwright/test";

test("부모·조부모가 본인 휴대전화를 직접 보호 대상으로 연결한다", async ({ page }) => {
  let registerBody: Record<string, unknown> = {};

  await page.route("**/api/v1/auth/register", async (route) => {
    registerBody = route.request().postDataJSON();
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({
      access_token: "self-access-token",
      refresh_token: "self-refresh-token-00000000000000000000000000000000",
      token_type: "bearer",
      user: { id: "11111111-1111-1111-1111-111111111111", email: "parent@example.com", display_name: "김부모", role: "GUARDIAN", phone_number: "010-1234-5678" },
    }) });
  });
  await page.route("**/api/v1/auth/login", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      access_token: "self-access-token", refresh_token: "self-refresh-token-00000000000000000000000000000000", token_type: "bearer",
      user: { id: "11111111-1111-1111-1111-111111111111", email: "parent@example.com", display_name: "김부모", role: "GUARDIAN", phone_number: "010-1234-5678" },
    }) });
  });
  await page.route("**/api/v1/families", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "family-1", name: "김부모 통화보호 가족", created_by: "11111111-1111-1111-1111-111111111111" }) });
    } else await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route(/\/protected-call-users$/, async (route) => {
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "protected-1", family_id: "family-1", name: "김부모", member_type: "PROTECTED_CALL_USER", relation_code: "SELF", phone_number_last4: "5678", protection_status: "PREPARING" }) });
  });
  await page.route(/\/confirmation-contacts$/, async (route) => {
    const request = route.request().postDataJSON();
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: `contact-${request.relation_code}`, family_id: "family-1", name: request.name, member_type: "FAMILY_CONFIRMATION_CONTACT", relation_code: request.relation_code, phone_number_last4: request.phone_number.slice(-4), is_primary_contact: request.is_primary_contact, notification_priority: 1, notify_enabled: true }) });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /회원가입/ }).click();
  await page.getByLabel("이름").fill("김부모");
  await page.getByLabel("본인 휴대전화 번호").fill("010-1234-5678");
  await page.getByLabel("이메일").fill("parent@example.com");
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();

  expect(registerBody).toMatchObject({ role: "GUARDIAN", phone_number: "010-1234-5678" });
  await page.getByRole("button", { name: "서비스 시작" }).click();
  await page.getByLabel("비밀번호").fill("password1");
  await page.getByRole("button", { name: "로그인" }).click();
  const protectedRequest = page.waitForRequest((request) => request.url().includes("/protected-call-users") && request.method() === "POST");
  await page.getByRole("button", { name: /내 전화를 보호받고 싶어요/ }).click();
  const protectedBody = (await protectedRequest).postDataJSON();
  await expect(page.locator(".api-feedback")).toHaveCount(0);
  await page.getByRole("button", { name: "아들", exact: true }).click();
  await page.getByLabel("성함").fill("김아들");
  await page.getByLabel("휴대전화 번호").fill("010-7777-9999");
  const firstContactRequest = page.waitForRequest((request) => request.url().includes("/confirmation-contacts") && request.method() === "POST");
  await page.getByRole("button", { name: /이 가족 추가하기/ }).click();
  const contactBody = (await firstContactRequest).postDataJSON();
  await page.getByRole("button", { name: "딸", exact: true }).click();
  await page.getByLabel("성함").fill("김딸");
  await page.getByLabel("휴대전화 번호").fill("010-8888-0000");
  await page.getByRole("button", { name: /이 가족 추가하기/ }).click();
  await expect(page.getByText("2명의 확인 가족을 등록했습니다.")).toBeVisible();
  await page.getByRole("button", { name: "가족 등록 완료 · 음성·얼굴 등록" }).click();

  expect(protectedBody).toMatchObject({
    name: "김부모",
    phone_number: "010-1234-5678",
    relation_code: "SELF",
    user_id: "11111111-1111-1111-1111-111111111111",
  });
  expect(contactBody).toMatchObject({ name: "김아들", phone_number: "010-7777-9999", relation_code: "SON" });
  await expect(page.getByRole("heading", { name: "가족별 등록 항목을 확인해 주세요" })).toBeVisible();
  await expect(page.getByText("음성 등록", { exact: true })).toBeVisible();
  await expect(page.getByText("얼굴 등록", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "다음: 등록 요청 보내기" }).click();
  await expect(page.getByRole("heading", { name: "가족에게 등록 요청을 보내세요" })).toBeVisible();
  await expect(page.getByText("김아들")).toBeVisible();
  await expect(page.getByText("김딸")).toBeVisible();
});

test("휴대전화 번호가 없는 기존 계정은 번호 보완 화면으로 이동한다", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      access_token: "legacy-access-token", refresh_token: "legacy-refresh-token-00000000000000000000000000000000", token_type: "bearer",
      user: { id: "22222222-2222-2222-2222-222222222222", email: "legacy@example.com", display_name: "기존 사용자", role: "GUARDIAN", phone_number: null },
    }) });
  });
  await page.route("**/api/v1/families", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "서비스 시작" }).click();
  await page.getByLabel("이메일").fill("legacy@example.com");
  await page.getByLabel("비밀번호").fill("password1");
  await page.getByRole("button", { name: "로그인" }).click();
  await page.getByRole("button", { name: /내 전화를 보호받고 싶어요/ }).click();

  await expect(page.getByRole("heading", { name: "보호받을 본인 휴대전화를 알려 주세요" })).toBeVisible();
  await expect(page.getByText("본인 휴대전화 번호가 필요합니다")).toHaveCount(0);
  await expect(page.locator(".api-feedback")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "다음: 확인 가족 등록" })).toBeDisabled();
});
