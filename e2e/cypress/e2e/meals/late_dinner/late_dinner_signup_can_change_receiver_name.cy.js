import { getDataTestIdElement } from "../../../helpers";
import { generateReceiver, getUserOrdersApi } from "../../../steps/orders";
import { createGuestUserApi, generateUsername } from "../../../steps/users";

describe(
  "When an admin user signs a guest up for late dinner but changes the receiver",
  { testIsolation: false },
  () => {
    const username = generateUsername();
    const receiver = `${generateReceiver(username)}-ABCD`;

    it("they will appear in the dinner list", () => {
      createGuestUserApi(username);
      cy.visit("/admin/dinner");
      getDataTestIdElement("late-signup-button").click();
      getDataTestIdElement("late-signup-user-select-button").click();
      getDataTestIdElement(
        `late-signup-user-select-button-${username}`,
      ).click();
      getDataTestIdElement(`late-signup-user-select-button-${username}`).should(
        "not.exist",
      );
      getDataTestIdElement("late-signup-full-name-input").should(
        "have.value",
        `${username} Test`,
      );
      getDataTestIdElement("late-signup-full-name-input").click().type("-abcd");
      getDataTestIdElement("late-signup-item-select").click();
      cy.waitUntil(() => {
        Cypress.$("[data-testid=late-signup-item-option]").first().click();
        return Cypress.$("[data-testid=late-signup-item-option]").length === 0;
      });
      getDataTestIdElement("late-signup-register-button").click();
      getDataTestIdElement("meal-row")
        .filter(`:contains(${receiver})`)
        .should("have.length", 1);
    });

    it("an order will have been made in the paying user's name", () => {
      getUserOrdersApi(username).then((orderResponse) => {
        expect(orderResponse.body.orders[0].item).to.eq("Dinner sign-up");
      });
    });
  },
);
