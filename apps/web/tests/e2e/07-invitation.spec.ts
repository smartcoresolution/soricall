import { expect, test } from "@playwright/test";

test("화면 7: 등록 가족에게 실제 초대 링크를 전송한다", async ({ page }) => {
  const email = `pw-invite-${Date.now()}@example.com`;
  await page.goto("/");
  await page.getByRole("button", { name: /통화 보호 시작하기/ }).click();
  await page.getByLabel("이름").fill("초대 테스트");
  await page.getByLabel("이메일").fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();
  await page.getByRole("button", { name: /보호 가족 등록하기/ }).click();
  await page.getByLabel("성함").fill("테스트 할머니");
  await page.getByLabel("휴대전화 번호").fill("010-1111-2222");
  await page.getByRole("button", { name: "다음: 확인 가족 등록" }).click();
  await page.getByRole("button", { name: "손녀", exact: true }).click();
  await page.getByLabel("성함").fill("테스트 손녀");
  await page.getByLabel("휴대전화 번호").fill("010-3333-4444");
  await page.getByRole("button", { name: "다음: 가족 정보 등록" }).click();

  await expect(page.getByRole("heading", { name: "가족에게 등록 요청을 보내세요" })).toBeVisible();
  await expect(page.getByText("테스트 손녀")).toBeVisible();
  await expect(page.getByText("생체정보는 가족 본인이 직접 등록합니다.")).toBeVisible();
  await page.screenshot({ path: "test-results/07-invitation-mobile.png", fullPage: true });

  const invitationResponse = page.waitForResponse((response) =>
    response.url().includes("/enrollment-invitations") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: /등록 요청 보내기/ }).click();
  const response = await invitationResponse;
  expect(response.status()).toBe(201);
  const body = await response.json();
  expect(body.status).toBe("PENDING");
  expect(body.enrollment_url).toContain("/soricall/enroll?token=");
  await expect(page.getByRole("heading", { name: "가족 등록 현황" })).toBeVisible();
});
