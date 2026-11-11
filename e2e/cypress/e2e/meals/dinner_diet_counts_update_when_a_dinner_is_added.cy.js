import { getDataTestIdElement } from "../../helpers";
import {
  DINNER_COUNT_TEST_IDS,
  getDinnerCounts,
  getTotalServedInt,
} from "../../steps/meals";
import { createDinnerOrderApi, generateReceiver } from "../../steps/orders";
import {
  createGuestUserApi,
  createVolunteerUserApi,
  generateUsername,
} from "../../steps/users";

// Test users and dinner orders are always Vegan, so adding one dinner should
// increase only the vegan and "eating" counts of the matching group and the overall totals.
function assertDinnerCountsChanged(before, expectedIncrements) {
  DINNER_COUNT_TEST_IDS.forEach((testId) => {
    const expected = before[testId] + (expectedIncrements[testId] ?? 0);
    getDataTestIdElement(testId).should(($el) => {
      expect(getTotalServedInt($el.text()), testId).to.eq(expected);
    });
  });
}

function visitAdminDinnerAndGetCounts() {
  cy.visit("/admin/dinner");
  cy.get("[data-testid=total-eating]", { timeout: 60000 }).should("exist");
  return getDinnerCounts();
}

describe("When a dinner is added", () => {
  it("for a guest, the overall and guest vegan counts increase by one", () => {
    const username = generateUsername();
    const receiver = generateReceiver(username);

    visitAdminDinnerAndGetCounts().then((before) => {
      createGuestUserApi(username);
      createDinnerOrderApi(username, receiver);
      cy.visit("/admin/dinner");
      cy.contains(receiver, { timeout: 60000 });
      assertDinnerCountsChanged(before, {
        "total-eating": 1,
        "total-vegan": 1,
        "total-guests-eating": 1,
        "total-guests-vegan": 1,
      });
    });
  });

  it("for a volunteer, the overall and volunteer vegan counts increase by one", () => {
    const username = generateUsername();
    const receiver = generateReceiver(username);

    visitAdminDinnerAndGetCounts().then((before) => {
      createVolunteerUserApi(username);
      cy.visit("/admin/dinner");
      cy.contains(receiver, { timeout: 60000 });
      assertDinnerCountsChanged(before, {
        "total-eating": 1,
        "total-vegan": 1,
        "total-volunteers-eating": 1,
        "total-volunteers-vegan": 1,
      });
    });
  });
});
