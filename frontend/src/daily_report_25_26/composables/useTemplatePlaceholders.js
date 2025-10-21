"use strict";

const EAST_8_OFFSET_MINUTES = 8 * 60;

function toEast8(dateLike = new Date()) {
  const date = new Date(dateLike);
  const utcTs = date.getTime() + date.getTimezoneOffset() * 60000;
  return new Date(utcTs + EAST_8_OFFSET_MINUTES * 60000);
}

function formatDay(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function formatMonth(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
  ].join("-");
}

function computeReferenceDates(baseDate = new Date()) {
  const eastNow = toEast8(baseDate);
  const yesterday = new Date(
    eastNow.getFullYear(),
    eastNow.getMonth(),
    eastNow.getDate() - 1,
  );

  let lastYearSameDay;
  if (yesterday.getMonth() === 1 && yesterday.getDate() === 29) {
    lastYearSameDay = new Date(yesterday.getFullYear() - 1, 1, 28);
  } else {
    lastYearSameDay = new Date(yesterday);
    lastYearSameDay.setFullYear(yesterday.getFullYear() - 1);
  }

  return {
    currentDay: formatDay(yesterday),
    previousDay: formatDay(lastYearSameDay),
    currentMonth: formatMonth(yesterday),
    previousMonth: formatMonth(lastYearSameDay),
  };
}

function replaceInString(source, replacements) {
  let result = source;
  for (const [pattern, value] of Object.entries(replacements)) {
    result = result.split(pattern).join(value);
  }
  return result;
}

function deepReplace(target, replacements) {
  if (typeof target === "string") {
    return replaceInString(target, replacements);
  }
  if (Array.isArray(target)) {
    return target.map((item) => deepReplace(item, replacements));
  }
  if (target && typeof target === "object") {
    const output = {};
    for (const [key, value] of Object.entries(target)) {
      output[key] = deepReplace(value, replacements);
    }
    return output;
  }
  return target;
}

export function useTemplatePlaceholders() {
  function applyTemplatePlaceholders(template, baseDate = new Date()) {
    const references = computeReferenceDates(baseDate);
    const replacements = {
      "(本期日)": references.currentDay,
      "(同期日)": references.previousDay,
      "(本期月)": references.currentMonth,
      "(同期月)": references.previousMonth,
      "(本供暖期)": "25-26",
      "(同供暖期)": "24-25",
      "同供暖期": "24-25",
    };

    const processed = deepReplace(template, replacements);

    if (!processed.biz_date) {
      processed.biz_date = references.currentDay;
    }

    return {
      template: processed,
      placeholders: {
        currentDay: references.currentDay,
        previousDay: references.previousDay,
        currentMonth: references.currentMonth,
        previousMonth: references.previousMonth,
        currentHeatingSeason: "25-26",
        previousHeatingSeason: "24-25",
      },
    };
  }

  return { applyTemplatePlaceholders };
}
