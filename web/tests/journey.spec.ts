import { test, expect } from "@playwright/test";
test("consulta, fontes, pergunta sem resposta e avaliação", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Carregar exemplos" }).click();
  await expect(
    page.getByText("Atraso dos consumidores Kafka", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Atraso dos consumidores Kafka número de partições");
  await page.getByRole("button", { name: "Buscar resposta" }).click();
  await expect(page.getByRole("heading", { name: "Resposta" })).toBeVisible();
  await page.locator("summary").click();
  await expect(
    page
      .locator(".citation")
      .getByText("runbooks/kafka-consumer-lag", { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/knowledge-desk.png",
    fullPage: true,
  });
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quem venceu o campeonato intergaláctico de xadrez?");
  await page.getByRole("button", { name: "Buscar resposta" }).click();
  await expect(
    page.getByRole("heading", { name: "Sem informação nos documentos" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Avaliação" }).click();
  await page.getByRole("button", { name: "Executar avaliação" }).click();
  await expect(page.getByText("4 / 4 testes passaram")).toBeVisible();
});
test("cadastro de documento no celular", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Documentos" }).click();
  await page.getByLabel("Identificador").fill("runbooks/mobile-smoke");
  await page
    .getByLabel("Título", { exact: true })
    .fill("Procedimento de teste no celular");
  await page
    .getByLabel("Conteúdo")
    .fill(
      "No teste em celular, verifique o tamanho da interface e a leitura dos trechos citados.",
    );
  await page.getByRole("button", { name: "Salvar documento" }).click();
  await expect(
    page.getByRole("heading", { name: "Procedimento de teste no celular" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: "../docs/screenshots/mobile-library.png",
    fullPage: true,
  });
});
