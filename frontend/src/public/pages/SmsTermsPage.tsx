import { Link } from 'react-router-dom';
import { COMPANY } from '../company';
import { H2, LegalPage, Ul } from './legal';

export const SmsTermsPage = () => (
  <LegalPage title="SMS Terms">
    <H2>Program</H2>
    <p>
      {COMPANY.legalName} Tour Notifications. When you request a tour at {COMPANY.site} and check
      the text-message consent box, we send texts about that tour only.
    </p>

    <H2>Messages you'll receive</H2>
    <Ul>
      <li>Confirmation that we received your tour request.</li>
      <li>Whether your tour was approved or declined.</li>
      <li>Your one-time access code, sent 30 minutes before your tour, with visit instructions.</li>
      <li>A request for feedback after your tour.</li>
    </Ul>
    <p>Message frequency varies, typically 3–5 messages per tour. We do not send marketing texts.</p>

    <H2>Costs</H2>
    <p>Message and data rates may apply. Carriers are not liable for delayed or undelivered messages.</p>

    <H2>Opting out and help</H2>
    <p>
      Reply <strong>STOP</strong> at any time to stop receiving texts; you'll receive one final
      confirmation message. Reply <strong>HELP</strong> for help, or email{' '}
      <a href={`mailto:${COMPANY.email}`} className="text-blue-700 hover:underline">{COMPANY.email}</a>.
    </p>

    <H2>Consent</H2>
    <p>
      Consent to receive texts is not a condition of requesting a tour; we'll still email you. No
      mobile information will be shared with third parties or affiliates for marketing or
      promotional purposes. See our{' '}
      <Link to="/privacy" className="text-blue-700 hover:underline">Privacy Policy</Link>.
    </p>
  </LegalPage>
);
