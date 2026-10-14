// A line comment.
import { readFile } from "fs";

/** JSDoc block comment. */
export function add(a, b) {
  // inner comment
  return a + b;
}

export class Calculator {
  constructor() {
    this.total = 0;
  }

  add(n) {
    this.total += n;
    return this.total;
  }
}

export const identity = (x) => x;
