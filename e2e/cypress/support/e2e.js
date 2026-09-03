import "cypress-wait-until";
import { register as registerCypressGrep } from "@cypress/grep";

registerCypressGrep();

Cypress.on("uncaught:exception", (err, runnable) => {
  if (err.message.includes("Hydration failed")) {
    return false;
  }
});

afterEach(function () {
  if (
    Cypress.config("testIsolation") === false &&
    this.currentTest.state === "failed"
  ) {
    Cypress.stop();
    return;
  }
});
