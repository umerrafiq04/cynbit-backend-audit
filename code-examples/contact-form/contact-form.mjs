const GENERIC_SUBMISSION_ERROR =
  "Something went wrong. Please try again or email us directly.";

export async function submitContactForm({
  submit,
  setPending,
  setError,
  onSuccess,
}) {
  setPending(true);
  setError(null);

  let result;
  try {
    result = await submit();
  } catch {
    setError(GENERIC_SUBMISSION_ERROR);
    return false;
  } finally {
    setPending(false);
  }

  if (!result?.success) {
    setError(GENERIC_SUBMISSION_ERROR);
    return false;
  }

  onSuccess();
  return true;
}
