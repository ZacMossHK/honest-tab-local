import { getDataTestIdElement } from "../../../helpers";
import { generateReceiver, getUserOrdersApi } from "../../../steps/orders";
import { createGuestUserApi, generateUsername } from "../../../steps/users";

describe(
  "When an admin user signs a guest up for late dinner using register and add another",
  { testIsolation: false },
  () => {
    const firstUsername = generateUsername();
    const secondUsername = generateUsername();

    it("they will both appear in the dinner list", function () {
      cy.wrap([firstUsername, secondUsername]).each((username) => {
        createGuestUserApi(username);
      });
      cy.visit("/admin/dinner");
      getDataTestIdElement("late-signup-button").click();
      cy.wrap([firstUsername, secondUsername]).each((username, index) => {
        getDataTestIdElement("late-signup-user-select-button").click();
        getDataTestIdElement(
          `late-signup-user-select-button-${username}`,
        ).click();
        getDataTestIdElement(
          `late-signup-user-select-button-${username}`,
        ).should("not.exist");
        getDataTestIdElement("late-signup-user-to-pay").should(
          "have.text",
          username,
        );
        getDataTestIdElement("late-signup-full-name-input").should(
          "have.value",
          `${username} Test`,
        );
        getDataTestIdElement("late-signup-item-select").click();
        getDataTestIdElement("late-signup-item-option")
          .first()
          .invoke("text")
          .as("selectedOption");
        cy.waitUntil(() => {
          Cypress.$("[data-testid=late-signup-item-option]").first().click();
          return (
            Cypress.$("[data-testid=late-signup-item-option]").length === 0
          );
        });
        getDataTestIdElement("late-signup-item-select").then(($selectEl) => {
          cy.wrap($selectEl).should("have.text", this.selectedOption);
        });
        getDataTestIdElement(
          `late-signup-register${!index ? "-and-add-another" : ""}-button`,
        ).should("not.be.disabled");
        getDataTestIdElement(
          `late-signup-register${!index ? "-and-add-another" : ""}-button`,
        ).click();
        cy.contains(`${username} Test added successfully!`);
      });
      cy.wrap([firstUsername, secondUsername]).each((username) => {
        const receiver = generateReceiver(username);
        getDataTestIdElement("meal-row")
          .filter(`:contains(${receiver})`)
          .should("have.length", 1);
      });
    });

    it("an order will have been made in both their names", () => {
      cy.wrap([firstUsername, secondUsername]).each((username) => {
        getUserOrdersApi(username).then((orderResponse) => {
          expect(orderResponse.body.orders).to.be.lengthOf(1);
          expect(orderResponse.body.orders[0].item).to.eq("Dinner sign-up");
        });
      });
    });
  },
);
