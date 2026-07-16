import { expect, test } from "@playwright/test";

test.describe("화면 2: 회원가입", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /회원가입/ }).click();
    await expect(page.getByRole("heading", { name: "가족의 안심을 시작해요" })).toBeVisible();
  });

  test("입력값을 검증하고 동의 화면으로 이동한다", async ({ page }) => {
    const next = page.getByRole("button", { name: "다음" });
    await expect(next).toBeDisabled();

    await page.getByLabel("이름").fill("홍길동");
    await page.getByLabel("본인 휴대전화 번호").fill("010-1000-2000");
    await page.getByLabel("비밀번호", { exact: true }).fill("password1");
    await page.getByLabel("비밀번호 확인").fill("password1");
    await expect(next).toBeDisabled();

    await page.getByRole("button", { name: "인증번호 받기" }).click();
    await expect(page.getByLabel("문자 인증번호")).toHaveValue(/^\d{6}$/);
    await page.getByRole("button", { name: "인증 확인" }).click();
    await expect(page.getByText("휴대전화 인증이 완료됐습니다.", { exact: true })).toBeVisible();
    await page.getByLabel("비밀번호 확인").fill("different1");
    await expect(next).toBeDisabled();

    await page.getByLabel("비밀번호 확인").fill("password1");
    await expect(next).toBeEnabled();
    await page.screenshot({ path: "test-results/02-signup-mobile.png", fullPage: true });

    await next.click();
    await expect(page.getByRole("heading", { name: "서비스 이용에 동의해 주세요" })).toBeVisible();

    await page.getByRole("button", { name: /이전/ }).click();
    await expect(page.getByLabel("이름")).toHaveValue("홍길동");
    await expect(page.getByLabel("본인 휴대전화 번호")).toHaveValue("010-1000-2000");
  });

  test("상단 홈 버튼으로 최초 화면에 돌아간다", async ({ page }) => {
    await page.getByRole("button", { name: /^홈$/ }).click();
    await expect(page.getByRole("heading", { name: "SoriCall" })).toBeVisible();
    await expect(page.getByRole("button", { name: /회원가입/ })).toBeVisible();
  });
});
