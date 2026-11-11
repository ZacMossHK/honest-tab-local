export function getTotalServedInt(text) {
  return parseInt(text.split(" ").at(-1));
}

export function createGuestDinnerMealForTodayApi(username, receiver) {
  return cy.request({
    method: "POST",
    url: "http://app:8000/api/test/meals/dinner/today",
    qs: { username, receiver },
  });
}

export function getTodaysDinnerMealsApi() {
  return cy.request({
    url: "http://app:8000/api/test/meals/dinner/today",
  });
}

const DINNER_COUNT_GROUPS = ["total", "total-guests", "total-volunteers"];
const DINNER_COUNT_FIELDS = ["eating", "meat", "vegetarian", "vegan"];

export const DINNER_COUNT_TEST_IDS = DINNER_COUNT_GROUPS.flatMap((group) =>
  DINNER_COUNT_FIELDS.map((field) => `${group}-${field}`),
);

export function getDinnerCounts() {
  const counts = {};
  DINNER_COUNT_TEST_IDS.forEach((testId) => {
    cy.get(`[data-testid=${testId}]`)
      .invoke("text")
      .then((text) => {
        counts[testId] = getTotalServedInt(text);
      });
  });
  return cy.wrap(counts);
}
