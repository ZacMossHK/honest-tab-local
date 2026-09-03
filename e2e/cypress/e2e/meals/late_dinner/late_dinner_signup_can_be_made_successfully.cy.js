import { getDataTestIdElement } from "../../../helpers";
import { generateReceiver, getUserOrdersApi } from "../../../steps/orders";
import { createGuestUserApi, generateUsername } from "../../../steps/users";

describe(
  "When an admin user signs a guest up for late dinner",
  { testIsolation: false },
  () => {
    const username = generateUsername();
    const receiver = generateReceiver(username);

    it("they will appear in the dinner list", function () {
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
      getDataTestIdElement("late-signup-user-to-pay").should(
        "have.text",
        username,
      );
      getDataTestIdElement("late-signup-full-name-input").should(
        "have.value",
        `${username} Test`,
      );
      getDataTestIdElement("late-signup-allergies").should(
        "have.value",
        "Nuts",
      );
      getDataTestIdElement("late-signup-item-select").click();
      getDataTestIdElement("late-signup-item-option")
        .first()
        .invoke("text")
        .as("dinnerOption");
      cy.waitUntil(() => {
        Cypress.$("[data-testid=late-signup-item-option]").first().click();
        return Cypress.$("[data-testid=late-signup-item-option]").length === 0;
      });
      getDataTestIdElement("late-signup-register-button").click();
      getDataTestIdElement("meal-row")
        .filter(`:contains(${receiver})`)
        .then(($mealRowEl) => {
          cy.wrap($mealRowEl)
            .find("[data-testid=diet]")
            .should("have.text", this.dinnerOption);
          cy.wrap($mealRowEl)
            .find("[data-testid=allergies]")
            .should("have.text", "Nuts");
        });
    });

    it("an order will have been made in their name", () => {
      getUserOrdersApi(username).then((orderResponse) => {
        expect(orderResponse.body.orders[0].item).to.eq("Dinner sign-up");
      });
    });
  },
);
