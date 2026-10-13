export const isValidEmail = (value: string): boolean =>
  /.+@.+\..+/.test(value.trim());

export const isValidPassword = (value: string): boolean => value.length >= 6;

export const isValidCredentials = (email: string, password: string): boolean =>
  isValidEmail(email) && isValidPassword(password);
