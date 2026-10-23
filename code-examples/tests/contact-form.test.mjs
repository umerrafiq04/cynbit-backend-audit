import assert from "node:assert/strict";
import test from "node:test";

import { submitContactForm } from "../contact-form/contact-form.mjs";

function createState() {
  return {
    pending: false,
    errors: [],
    successes: 0,
    pendingTransitions: [],
    setPending(value) {
      this.pending = value;
      this.pendingTransitions.push(value);
    },
    setError(value) {
      this.errors.push(value);
    },
    onSuccess() {
      this.successes += 1;
    },
  };
}

function callbacks(state, submit) {
  return {
    submit,
    setPending: state.setPending.bind(state),
    setError: state.setError.bind(state),
    onSuccess: state.onSuccess.bind(state),
  };
}

test("successful submission resets pending state and shows success", async () => {
  const state = createState();

  const result = await submitContactForm(
    callbacks(state, async () => ({ success: true })),
  );

  assert.equal(result, true);
  assert.deepEqual(state.pendingTransitions, [true, false]);
  assert.equal(state.pending, false);
  assert.deepEqual(state.errors, [null]);
  assert.equal(state.successes, 1);
});

test("resolved application failure resets pending state and shows a safe error", async () => {
  const state = createState();

  const result = await submitContactForm(
    callbacks(state, async () => ({ success: false })),
  );

  assert.equal(result, false);
  assert.deepEqual(state.pendingTransitions, [true, false]);
  assert.equal(state.pending, false);
  assert.equal(
    state.errors[1],
    "Something went wrong. Please try again or email us directly.",
  );
  assert.equal(state.successes, 0);
});

test("rejected action resets pending state and a second attempt can succeed", async () => {
  const state = createState();
  let attempts = 0;
  const submit = async () => {
    attempts += 1;
    if (attempts === 1) {
      throw new Error("sensitive internal error");
    }
    return { success: true };
  };

  const firstResult = await submitContactForm(callbacks(state, submit));
  assert.equal(firstResult, false);
  assert.equal(state.pending, false);
  assert.match(state.errors[1], /Please try again/);
  assert.doesNotMatch(state.errors[1], /sensitive internal error/);

  const secondResult = await submitContactForm(callbacks(state, submit));

  assert.equal(secondResult, true);
  assert.equal(attempts, 2);
  assert.deepEqual(state.pendingTransitions, [true, false, true, false]);
  assert.equal(state.pending, false);
  assert.deepEqual(state.errors, [
    null,
    "Something went wrong. Please try again or email us directly.",
    null,
  ]);
  assert.equal(state.successes, 1);
});
