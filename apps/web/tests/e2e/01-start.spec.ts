import { expect, test } from "@playwright/test";

test.describe("화면 1: 시작", () => {
  test("모바일 시작 화면의 핵심 정보와 진입 버튼이 동작한다", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle("SoriCall");
    await expect(page.getByText("AI 가족 사칭 전화 보호")).toBeVisible();
    await expect(page.getByRole("heading", { name: /부모님의 안전한 통화를/ })).toBeVisible();
    await expect(page.getByText("가족의 전화번호와 목소리를 기억하고")).toBeVisible();

    const signup = page.getByRole("button", { name: /회원가입/ });
    const login = page.getByRole("button", { name: "서비스 시작" });
    await expect(signup).toBeEnabled();
    await expect(login).toBeEnabled();
    await expect(page.locator(".top-actions")).toHaveCount(0);

    await page.screenshot({ path: "test-results/01-start-mobile.png", fullPage: true });

    await login.click();
    await expect(page.getByRole("heading", { name: "다시 만나서 반가워요" })).toBeVisible();
    await page.getByRole("button", { name: /이전/ }).click();
    await signup.click();
    await expect(page.getByRole("heading", { name: "가족의 안심을 시작해요" })).toBeVisible();
  });

  test("저장된 로그인 세션이 있어도 새로고침하면 시작 화면에 머문다", async ({ page }) => {
    await page.route("**/api/v1/auth/refresh", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
        access_token: "refreshed-access-token",
        refresh_token: "refreshed-token-00000000000000000000000000000000",
        token_type: "bearer",
        user: { id: "11111111-1111-1111-1111-111111111111", email: "saved@example.com", display_name: "저장 사용자", role: "GUARDIAN" },
      }) });
    });
    await page.goto("/");
    await page.evaluate(() => localStorage.setItem("soricall.dev.session", JSON.stringify({
      access_token: "old-access-token",
      refresh_token: "old-refresh-token-00000000000000000000000000000000",
      user: { id: "11111111-1111-1111-1111-111111111111", email: "saved@example.com", display_name: "저장 사용자", role: "GUARDIAN" },
    })));
    await page.reload();

    await expect(page.getByRole("heading", { name: "SoriCall" })).toBeVisible();
    await expect(page.getByText("통화 보호 켜짐")).toHaveCount(0);
    await page.getByRole("button", { name: "서비스 시작" }).click();
    await expect(page.getByRole("heading", { name: "다시 만나서 반가워요" })).toBeVisible();
    await expect(page.getByText("통화 보호 켜짐")).toHaveCount(0);
  });
});
