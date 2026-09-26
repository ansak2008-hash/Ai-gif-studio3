declare module "node:assert/strict" {
  const assert: {
    equal(actual: unknown, expected: unknown): void;
    ok(value: unknown): void;
    throws(block: () => unknown, error?: RegExp): void;
  };
  export default assert;
}

declare module "node:test" {
  const test: (name: string, fn: () => void) => void;
  export default test;
}
