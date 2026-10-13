import { describe, expect, it } from 'vitest';
import { isValidCredentials, isValidEmail, isValidPassword } from './validation';

describe('credential validation', () => {
  it('accepts well-formed emails and tolerates surrounding whitespace', () => {
    expect(isValidEmail('you@nightsky.in')).toBe(true);
    expect(isValidEmail('  you@nightsky.in  ')).toBe(true);
  });

  it('rejects malformed emails', () => {
    expect(isValidEmail('')).toBe(false);
    expect(isValidEmail('you@nightsky')).toBe(false);
    expect(isValidEmail('younightsky.in')).toBe(false);
    expect(isValidEmail('@nightsky.in')).toBe(false);
  });

  it('requires passwords of at least 6 characters', () => {
    expect(isValidPassword('12345')).toBe(false);
    expect(isValidPassword('123456')).toBe(true);
    expect(isValidPassword('Testpass12345!')).toBe(true);
  });

  it('combines both rules for the submit gate', () => {
    expect(isValidCredentials('you@nightsky.in', '123456')).toBe(true);
    expect(isValidCredentials('you@nightsky.in', '12345')).toBe(false);
    expect(isValidCredentials('not-an-email', '123456')).toBe(false);
  });
});
