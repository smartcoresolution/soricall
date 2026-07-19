import { expect, Page, test } from "@playwright/test";

async function openConsent(page: Page, email: string) {
  await page.goto("/");
  await page.getByRole("button", { name: /회원가입/ }).click();
  await page.getByLabel("이름").fill("동의 테스트");
  await page.getByLabel("본인 휴대전화 번호").fill("010-1000-2000");
  await page.getByLabel("이메일").fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await expect(page.getByRole("heading", { name: "서비스 이용에 동의해 주세요" })).toBeVisible();
}

test.describe("화면 3: 서비스 이용 동의", () => {
  test("필수 동의를 명시적으로 선택해야 가입할 수 있다", async ({ page }) => {
    await openConsent(page, `pw-consent-${Date.now()}@example.com`);
    await page.getByRole("button", { name: "항목 1 세부내용 열기" }).click();
    await expect(page.getByText(/기본 이용 조건입니다/)).toBeVisible();
    await page.getByRole("button", { name: "항목 1 세부내용 닫기" }).click();
    await expect(page.getByText(/기본 이용 조건입니다/)).toHaveCount(0);
    const submit = page.getByRole("button", { name: "동의하고 계속하기" });
    await expect(submit).toBeDisabled();

    await page.getByRole("button", { name: /\[선택\].*얼굴정보 처리/ }).click();
    await expect(submit).toBeDisabled();

    for (const label of ["서비스 이용약관", "개인정보 수집·이용", "가족 전화번호 및 음성 특징정보 처리", "통화 위험분석 및 가족 알림"]) {
      await page.getByRole("button", { name: new RegExp(`\\[필수\\].*${label}`) }).click();
    }
    await expect(submit).toBeEnabled();
    await page.screenshot({ path: "test-results/03-consent-mobile.png", fullPage: true });

    await submit.click();
    await expect(page.getByRole("heading", { name: "안전하게 가입됐어요" })).toBeVisible();
  });

  test("전체 동의 토글과 가입된 이메일의 서비스 시작 전환을 처리한다", async ({ page }) => {
    await page.route("**/api/v1/auth/register", async (route) => {
      await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ detail: "email already registered" }) });
    });
    await openConsent(page, "duplicate@example.com");
    const all = page.getByRole("button", { name: "전체 동의" });
    const submit = page.getByRole("button", { name: "동의하고 계속하기" });

    await all.click();
    await expect(submit).toBeEnabled();
    await all.click();
    await expect(submit).toBeDisabled();
    await all.click();
    await submit.click();

    await expect(page.getByRole("heading", { name: "다시 만나서 반가워요" })).toBeVisible();
    await expect(page.getByLabel("이메일")).toHaveValue("duplicate@example.com");
    await expect(page.getByText("이미 가입된 이메일입니다.")).toHaveCount(0);
  });
});
