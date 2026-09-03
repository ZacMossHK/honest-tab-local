import { getDataTestIdElement } from "../../helpers";
import {
  createGuestUserApi,
  generateUsername,
  logUserOn,
} from "../../steps/users";

describe(
  "When a user orders breakfast and multiple packed lunches",
  { testIsolation: false },
  () => {
    const username = generateUsername();
    it("they are successfully ordered", () => {
      createGuestUserApi(username);
      cy.visit("/");
      logUserOn(username);
      getDataTestIdElement("breakfast-signup-button").click();
      getDataTestIdElement("breakfast-signup-item-select").click();
      getDataTestIdElement("breakfast-signup-item-option").first().click();
      getDataTestIdElement("breakfast-signup-register").click();
      getDataTestIdElement("breakfast-signup-button").click();
      getDataTestIdElement("breakfast-signup-item-select").click();
      getDataTestIdElement("breakfast-signup-item-option")
        .filter(":contains(Packed Lunch)")
        .first()
        .click();
      getDataTestIdElement("breakfast-signup-register").click();
      getDataTestIdElement("breakfast-signup-button").click();
      getDataTestIdElement("breakfast-signup-item-select").click();
      getDataTestIdElement("breakfast-signup-item-option")
        .filter(":contains(Packed Lunch)")
        .first()
        .click();
      getDataTestIdElement("breakfast-signup-register").click();
      getDataTestIdElement("view-orders-button").click();
      getDataTestIdElement("ordered_item")
        .filter(`:contains(Breakfast sign-up)`)
        .should("have.length", 3);
    });

    it("the orders appear in the breakfast list", () => {
      cy.visit("/admin/breakfast");
      getDataTestIdElement("meal-receiver")
        .filter(`:contains(${username.toUpperCase()} TEST)`)
        .should("have.length", 3);
    });
  },
);
