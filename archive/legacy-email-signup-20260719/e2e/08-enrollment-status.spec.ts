import { expect, test } from "@playwright/test";

test("화면 8: 가족 등록 상태를 표시하고 링크를 재전송한다", async ({ page }) => {
  const email = `pw-status-${Date.now()}@example.com`;
  await page.goto("/");
  await page.getByRole("button", { name: /회원가입/ }).click();
  await page.getByLabel("이름").fill("상태 테스트");
  await page.getByLabel("본인 휴대전화 번호").fill("010-1000-2000");
  await page.getByLabel("이메일").fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();
  await page.getByRole("button", { name: "서비스 시작" }).click();
  await page.getByLabel("비밀번호").fill("password1");
  await page.getByRole("button", { name: "로그인" }).click();
  await page.getByRole("button", { name: /부모님의 전화를 보호하고 싶어요/ }).click();
  await page.getByLabel("성함").fill("테스트 할아버지");
  await page.getByLabel("휴대전화 번호").fill("010-1111-2222");
  await page.getByRole("button", { name: "다음: 부모님 앱 연결" }).click();
  await page.getByRole("button", { name: "다음: 확인 가족 등록" }).click();
  await page.getByRole("button", { name: "아들", exact: true }).click();
  await page.getByLabel("성함").fill("테스트 아들");
  await page.getByLabel("휴대전화 번호").fill("010-3333-4444");
  await page.getByRole("button", { name: /이 가족 추가하기/ }).click();
  await page.getByRole("button", { name: "가족 등록 완료 · 음성·얼굴 등록" }).click();
  await page.getByRole("button", { name: "다음: 등록 요청 보내기" }).click();
  await page.getByRole("button", { name: /등록 요청 보내기/ }).click();

  await expect(page.getByRole("heading", { name: "가족 등록 현황" })).toBeVisible();
  await expect(page.getByText("응답 대기")).toBeVisible();
  await expect(page.getByText("휴대전화 끝 4444")).toBeVisible();
  await page.screenshot({ path: "test-results/08-enrollment-status-mobile.png", fullPage: true });

  const resendResponse = page.waitForResponse((response) =>
    response.url().endsWith("/resend") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "링크 재발급" }).click();
  expect((await resendResponse).status()).toBe(200);
  await expect(page.getByText("등록 링크를 다시 보냈습니다.")).toBeVisible();
  await page.getByRole("button", { name: "안심 홈으로 이동" }).click();
  await expect(page.getByText("통화 보호 켜짐")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "SoriCall" })).toBeVisible();
  await expect(page.getByText("통화 보호 켜짐")).toHaveCount(0);
});
