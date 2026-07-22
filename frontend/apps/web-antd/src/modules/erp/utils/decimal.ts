import BigNumber from 'bignumber.js';

export type DecimalValue = BigNumber.Value | null | undefined;

export const MONEY_DECIMAL_PLACES = 4;
export const QUANTITY_DECIMAL_PLACES = 6;

function toDecimal(value: DecimalValue) {
  const decimal = new BigNumber(value ?? 0);
  return decimal.isFinite() ? decimal : new BigNumber(0);
}

export function compareDecimal(left: DecimalValue, right: DecimalValue) {
  return toDecimal(left).comparedTo(toDecimal(right));
}

export function subtractDecimal(
  left: DecimalValue,
  right: DecimalValue,
  decimalPlaces = MONEY_DECIMAL_PLACES,
) {
  return toDecimal(left)
    .minus(toDecimal(right))
    .decimalPlaces(decimalPlaces, BigNumber.ROUND_HALF_UP)
    .toFixed(decimalPlaces);
}

export function formatDecimal(
  value: DecimalValue,
  decimalPlaces = MONEY_DECIMAL_PLACES,
) {
  return toDecimal(value)
    .decimalPlaces(decimalPlaces, BigNumber.ROUND_HALF_UP)
    .toFixed(decimalPlaces);
}

export function normalizeDecimal(
  value: DecimalValue,
  decimalPlaces = MONEY_DECIMAL_PLACES,
) {
  return toDecimal(value)
    .decimalPlaces(decimalPlaces, BigNumber.ROUND_HALF_UP)
    .toFixed();
}
