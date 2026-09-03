import { getDataTestIdElement } from "../../helpers";
import {
  createGuestUserApi,
  generateUsername,
  logUserOn,
} from "../../steps/users";

describe(
  "When a user orders breakfast twice using different names",
  { testIsolation: false },
  () => {
    const username = generateUsername();
    it("it is successfully ordered", () => {
      createGuestUserApi(username);
      cy.visit("/");
      logUserOn(username);
      getDataTestIdElement("breakfast-signup-button").click();
      getDataTestIdElement("breakfast-signup-item-select").click();
      getDataTestIdElement("breakfast-signup-item-option").first().click();
      getDataTestIdElement("breakfast-signup-register").click();
      getDataTestIdElement("breakfast-signup-button").click();
      getDataTestIdElement("breakfast-signup-first-name").click().type("abc");
      getDataTestIdElement("breakfast-signup-item-select").click();
      getDataTestIdElement("breakfast-signup-item-option").first().click();
      getDataTestIdElement("breakfast-signup-register").click();
      getDataTestIdElement("view-orders-button").click();
      getDataTestIdElement("ordered_item")
        .filter(`:contains(Breakfast sign-up)`)
        .should("have.length", 2);
    });

    it("the second order appears in the breakfast list", () => {
      cy.visit("/admin/breakfast");
      getDataTestIdElement("meal-receiver")
        .filter(`:contains(${username.toUpperCase()}ABC TEST)`)
        .should("have.length", 1);
    });
  },
);
