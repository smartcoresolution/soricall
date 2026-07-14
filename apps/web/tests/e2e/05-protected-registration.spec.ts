import { expect, test } from "@playwright/test";

test("화면 5: 보호 대상 정보를 검증하고 실제 API에 등록한다", async ({ page }) => {
  const email = `pw-protected-${Date.now()}@example.com`;
  await page.goto("/");
  await page.getByRole("button", { name: /통화 보호 시작하기/ }).click();
  await page.getByLabel("이름").fill("보호자 테스트");
  await page.getByLabel("이메일").fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();
  await page.getByRole("button", { name: /보호 가족 등록하기/ }).click();

  await expect(page.getByRole("heading", { name: "보이스피싱으로부터 누구의 전화를 보호할까요?" })).toBeVisible();
  const next = page.getByRole("button", { name: "다음: 확인 가족 등록" });
  await expect(next).toBeDisabled();

  await page.getByRole("button", { name: "아버지", exact: true }).click();
  await page.getByLabel("성함").fill("테스트 아버지");
  await page.getByLabel("휴대전화 번호").fill("전화번호아님");
  await expect(next).toBeDisabled();
  await expect(page.getByText("올바른 휴대전화 번호를 입력해 주세요.")).toBeVisible();

  await page.getByLabel("휴대전화 번호").fill("010-1234-5678");
  await expect(next).toBeEnabled();
  await expect(page.locator(".bottom-nav")).toHaveCount(0);
  await page.screenshot({ path: "test-results/05-protected-registration-mobile.png", fullPage: true });

  const familyResponse = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/families") && response.request().method() === "POST",
  );
  const protectedResponse = page.waitForResponse((response) =>
    response.url().includes("/protected-call-users") && response.request().method() === "POST",
  );
  await next.click();

  const family = await familyResponse;
  const protectedUser = await protectedResponse;
  expect(family.status()).toBe(201);
  expect(protectedUser.status()).toBe(201);
  expect(protectedUser.request().postDataJSON()).toMatchObject({
    name: "테스트 아버지",
    phone_number: "010-1234-5678",
    relation_code: "FATHER",
  });
  await expect(page.getByRole("heading", { name: "의심전화를 확인해 줄 가족을 등록해 주세요" })).toBeVisible();
});
