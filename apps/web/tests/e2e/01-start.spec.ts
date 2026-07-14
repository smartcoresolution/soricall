import { expect, test } from "@playwright/test";

test.describe("화면 1: 시작", () => {
  test("모바일 시작 화면의 핵심 정보와 진입 버튼이 동작한다", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle("SoriCall");
    await expect(page.getByText("AI 가족 사칭 전화 보호")).toBeVisible();
    await expect(page.getByRole("heading", { name: /부모님의 전화를/ })).toBeVisible();
    await expect(page.getByText("가족의 전화번호와 목소리를 기억하고")).toBeVisible();

    const signup = page.getByRole("button", { name: /통화 보호 시작하기/ });
    const login = page.getByRole("button", { name: "이미 가입했어요" });
    const install = page.getByRole("button", { name: "앱으로 설치하기" });
    await expect(signup).toBeEnabled();
    await expect(login).toBeEnabled();
    await expect(install).toBeEnabled();
    await expect(page.locator(".top-actions")).toHaveCount(0);

    await install.click();
    await expect(page.getByText(/앱 설치.*홈 화면에 추가/)).toBeVisible();
    await page.locator(".api-feedback button").click();

    await page.screenshot({ path: "test-results/01-start-mobile.png", fullPage: true });

    await login.click();
    await expect(page.getByRole("heading", { name: "다시 만나서 반가워요" })).toBeVisible();
    await page.getByRole("button", { name: /이전/ }).click();
    await signup.click();
    await expect(page.getByRole("heading", { name: "가족의 안심을 시작해요" })).toBeVisible();
  });
});
