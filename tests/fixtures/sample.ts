// A line comment.
import { Component } from "@angular/core";

interface User {
  id: number;
  name: string;
}

/** A service. */
export function greet(user: User): string {
  // inner comment
  return `hello ${user.name}`;
}

export class Service {
  private count: number = 0;

  increment(): number {
    this.count += 1;
    return this.count;
  }
}
