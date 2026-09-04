import { getDataTestIdElement } from "../../helpers";
import {
  createGuestUserApi,
  createUser,
  generateUsername,
} from "../../steps/users";

function enterRemainingUserData(username) {
  getDataTestIdElement("first-name-input").click().type(username);
  getDataTestIdElement("last-name-input").click().type("Test");
  getDataTestIdElement("phone-number-input").click().type("0123456789");
  getDataTestIdElement("email-input").click().type("test@test.com");
  cy.get('select[name="diet"]').select("Vegan", { force: true });
  getDataTestIdElement("allergies-input").click().type("Nuts");
  getDataTestIdElement("radio-input-yes").click();
}

describe("Wrong passwords", () => {
  let username;
  beforeEach(() => {
    cy.visit("/");
    username = generateUsername();
  });

  it("Users cannot be created with the same nickname", () => {
    createGuestUserApi(username);
    getDataTestIdElement("sign-up-user-button").click();
    getDataTestIdElement("user-name-input").click().type(username);
    enterRemainingUserData(username);
    getDataTestIdElement("user-name-error-message").should(
      "have.text",
      "This username is already taken.",
    );
    getDataTestIdElement("user-submit-button").should("be.disabled");
  });

  for (let character of ["%", "+", " "]) {
    it(`Users cannot be created if the first character ("${character}") is not a number or letter`, () => {
      getDataTestIdElement("sign-up-user-button").click();
      getDataTestIdElement("user-name-input")
        .click()
        .type(character + username);
      enterRemainingUserData(username);
      getDataTestIdElement("user-name-error-message").should(
        "have.text",
        "The first character must be a number or letter.",
      );
      getDataTestIdElement("user-submit-button").should("be.disabled");
    });
  }

  it("Users cannot be created with trailing whitespace", () => {
    getDataTestIdElement("sign-up-user-button").click();
    getDataTestIdElement("user-name-input")
      .click()
      .type(username + " ");
    enterRemainingUserData(username);
    getDataTestIdElement("user-name-error-message").should(
      "have.text",
      "The last character cannot be whitespace.",
    );
    getDataTestIdElement("user-submit-button").should("be.disabled");
  });
});
