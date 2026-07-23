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
  await page.getByLabel("본인 휴대전화 번호").fill("010-1000-2000");
  await page.getByLabel("이메일").fill("complete@example.com");
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();

  await expect(page.getByRole("heading", { name: "안전하게 가입됐어요" })).toBeVisible();
  await expect(page.getByText("가입 정보가 안전하게 저장됐습니다.")).toBeVisible();
  await expect(page.locator(".api-feedback")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /이전/ })).toHaveCount(0);
  await page.screenshot({ path: "test-results/04-signup-complete-mobile.png", fullPage: true });

  await page.getByRole("button", { name: "서비스 시작" }).click();
  await expect(page.getByRole("heading", { name: "다시 만나서 반가워요" })).toBeVisible();
  await expect(page.getByLabel("이메일")).toHaveValue("complete@example.com");
});

test("로그인 실패 안내를 로그인 카드 안에 표시한다", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "invalid email or password" }) });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "서비스 시작" }).click();
  await page.getByLabel("이메일").fill("wrong@example.com");
  await page.getByLabel("비밀번호").fill("wrong-password");
  await page.getByRole("button", { name: "로그인" }).click();

  const alert = page.getByRole("alert");
  await expect(alert).toContainText("이메일 또는 비밀번호가 올바르지 않습니다.");
  await expect(alert).toContainText("비밀번호 찾기");
  await expect(alert).toContainText("회원가입");
  await expect(page.locator(".api-feedback")).toHaveCount(0);

  await page.getByRole("button", { name: /이전/ }).click();
  await expect(page.getByRole("heading", { name: "SoriCall" })).toBeVisible();
  await expect(page.getByText("이메일 또는 비밀번호가 올바르지 않습니다.")).toHaveCount(0);
  await expect(page.locator(".api-feedback")).toHaveCount(0);
});
