export const COMPANY = {
  legalName: 'APEX Element Group LLC',
  shortName: 'APEX Element Group',
  email: 'tours@apexelementgrp.com',
  site: 'apexelementgrp.com',
  toursSite: 'tours.apexelementgrp.com',
  policyEffectiveDate: 'November 3, 2026',
};

// Shown next to the SMS opt-in checkbox. Twilio toll-free verification
// reviewers check this wording, so keep it in sync with SmsTermsPage.
export const SMS_CONSENT_TEXT =
  `I agree to receive text messages from ${COMPANY.legalName} about my tour request, ` +
  'including approval status, my one-time access code, and a follow-up request for feedback. ' +
  'Message frequency varies (typically 3–5 messages per tour). Message and data rates may apply. ' +
  'Reply STOP to opt out or HELP for help. Consent is not required to request a tour.';
