import { getDataTestIdElement } from "../../helpers";
import { orderDinner } from "../../steps/orders";
import {
  createGuestUserApi,
  generateUsername,
  logUserOn,
} from "../../steps/users";

describe(
  "When a user orders dinner twice using different names",
  { testIsolation: false },
  () => {
    const username = generateUsername();
    it("it is successfully ordered", () => {
      createGuestUserApi(username);
      cy.visit("/");
      logUserOn(username);
      orderDinner(username);
      getDataTestIdElement("dinner-signup-button").click();
      getDataTestIdElement("dinner-signup-first-name").click().type("abc");
      getDataTestIdElement("dinner-signup-register").click();
      getDataTestIdElement("view-orders-button").click();
      getDataTestIdElement("ordered_item")
        .filter(`:contains(Dinner sign-up)`)
        .should("have.length", 2);
    });

    it("the second order appears in the dinner list", () => {
      cy.visit("/admin/dinner");
      getDataTestIdElement("meal-receiver")
        .filter(`:contains(${username.toUpperCase()}ABC TEST)`)
        .should("have.length", 1);
    });
  },
);
