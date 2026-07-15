import { expect, test } from "@playwright/test";

test("화면 4: 가입 완료 상태를 확인하고 보호 가족 등록으로 이동한다", async ({ page }) => {
  await page.route("**/api/v1/auth/register", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "test-access-token",
        refresh_token: "test-refresh-token-00000000000000000000000000000000",
        token_type: "bearer",
        user: { id: "11111111-1111-1111-1111-111111111111", email: "complete@example.com", display_name: "가입 완료", role: "GUARDIAN" },
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /회원가입/ }).click();
  await page.getByLabel("이름").fill("가입 완료");
  await page.getByLabel("이메일").fill("complete@example.com");
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();

  await expect(page.getByRole("heading", { name: "안전하게 가입됐어요" })).toBeVisible();
  await expect(page.getByText("가입 정보가 안전하게 저장됐습니다.")).toBeVisible();
  await expect(page.getByRole("button", { name: /이전/ })).toHaveCount(0);
  await page.screenshot({ path: "test-results/04-signup-complete-mobile.png", fullPage: true });

  await page.getByRole("button", { name: /보호 가족 등록하기/ }).click();
  await expect(page.getByRole("heading", { name: "보이스피싱으로부터 누구의 전화를 보호할까요?" })).toBeVisible();
});
