import { createUser, generateUsername, logUserOn } from "../../steps/users";

describe(
  "When signing up a new user",
  { testIsolation: false, tags: "@smoke" },
  () => {
    const username = generateUsername();
    it("they are created successfully and can log on", () => {
      cy.visit("/");
      createUser(username);
      logUserOn(username);
      cy.get(`[data-testid="user-page-heading"]`).contains(`Hello ${username}`);
    });

    it("they can't log on with the wrong password", () => {
      cy.visit("/");
      logUserOn(username, "wrong");
      cy.get(`[data-testid="wrong-password-error"]`).should("be.visible");
    });
  },
);
