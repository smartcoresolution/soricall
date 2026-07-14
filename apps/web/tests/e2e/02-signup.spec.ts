import { expect, test } from "@playwright/test";

test.describe("화면 2: 회원가입", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /통화 보호 시작하기/ }).click();
    await expect(page.getByRole("heading", { name: "가족의 안심을 시작해요" })).toBeVisible();
  });

  test("입력값을 검증하고 동의 화면으로 이동한다", async ({ page }) => {
    const next = page.getByRole("button", { name: "다음" });
    await expect(next).toBeDisabled();

    await page.getByLabel("이름").fill("홍길동");
    await page.getByLabel("이메일").fill("잘못된이메일");
    await page.getByLabel("비밀번호", { exact: true }).fill("password1");
    await page.getByLabel("비밀번호 확인").fill("password1");
    await expect(next).toBeDisabled();

    await page.getByLabel("이메일").fill("signup-test@example.com");
    await page.getByLabel("비밀번호 확인").fill("different1");
    await expect(next).toBeDisabled();

    await page.getByLabel("비밀번호 확인").fill("password1");
    await expect(next).toBeEnabled();
    await page.screenshot({ path: "test-results/02-signup-mobile.png", fullPage: true });

    await next.click();
    await expect(page.getByRole("heading", { name: "서비스 이용에 동의해 주세요" })).toBeVisible();

    await page.getByRole("button", { name: /이전/ }).click();
    await expect(page.getByLabel("이름")).toHaveValue("홍길동");
    await expect(page.getByLabel("이메일")).toHaveValue("signup-test@example.com");
  });
});
