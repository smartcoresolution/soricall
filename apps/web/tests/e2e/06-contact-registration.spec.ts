import { expect, test } from "@playwright/test";

test("화면 6: 확인 가족을 여러 명 실제 API에 등록한다", async ({ page }) => {
  const email = `pw-contact-${Date.now()}@example.com`;
  await page.goto("/");
  await page.getByRole("button", { name: /통화 보호 시작하기/ }).click();
  await page.getByLabel("이름").fill("확인 가족 테스트");
  await page.getByLabel("이메일").fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill("password1");
  await page.getByLabel("비밀번호 확인").fill("password1");
  await page.getByRole("button", { name: "다음" }).click();
  await page.getByRole("button", { name: "전체 동의" }).click();
  await page.getByRole("button", { name: "동의하고 계속하기" }).click();
  await page.getByRole("button", { name: /보호 가족 등록하기/ }).click();
  await page.getByLabel("성함").fill("테스트 어머니");
  await page.getByLabel("휴대전화 번호").fill("010-1111-2222");
  await page.getByRole("button", { name: "다음: 확인 가족 등록" }).click();

  await expect(page.getByRole("heading", { name: "의심전화를 확인해 줄 가족을 등록해 주세요" })).toBeVisible();
  const add = page.getByRole("button", { name: /확인 가족 한 명 더 추가/ });
  const next = page.getByRole("button", { name: "다음: 가족 정보 등록" });
  await expect(add).toBeDisabled();
  await expect(next).toBeDisabled();

  await page.getByRole("button", { name: "아들", exact: true }).click();
  await page.getByLabel("성함").fill("테스트 아들");
  await page.getByLabel("휴대전화 번호").fill("잘못된번호");
  await expect(add).toBeDisabled();
  await expect(next).toBeDisabled();
  await expect(page.getByText("올바른 휴대전화 번호를 입력해 주세요.")).toBeVisible();

  await page.getByLabel("휴대전화 번호").fill("010-3333-4444");
  await expect(add).toBeEnabled();
  await page.screenshot({ path: "test-results/06-contact-registration-mobile.png", fullPage: true });

  const firstResponse = page.waitForResponse((response) =>
    response.url().includes("/confirmation-contacts") && response.request().method() === "POST",
  );
  await add.click();
  expect((await firstResponse).status()).toBe(201);
  await expect(page.getByText("확인 가족을 추가했습니다.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "의심전화를 확인해 줄 가족을 등록해 주세요" })).toBeVisible();
  await expect(page.getByLabel("성함")).toHaveValue("");
  await expect(page.getByLabel("휴대전화 번호")).toHaveValue("");

  await page.getByRole("button", { name: "딸", exact: true }).click();
  await page.getByLabel("성함").fill("테스트 딸");
  await page.getByLabel("휴대전화 번호").fill("010-5555-6666");
  const secondResponse = page.waitForResponse((response) =>
    response.url().includes("/confirmation-contacts") && response.request().method() === "POST",
  );
  await next.click();
  const response = await secondResponse;
  expect(response.status()).toBe(201);
  expect(response.request().postDataJSON()).toMatchObject({
    name: "테스트 딸",
    relation_code: "DAUGHTER",
    phone_number: "010-5555-6666",
  });
  await expect(page.getByRole("heading", { name: "가족에게 등록 요청을 보내세요" })).toBeVisible();
});
