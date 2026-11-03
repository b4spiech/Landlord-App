import { Link } from 'react-router-dom';
import { COMPANY } from '../company';
import { H2, LegalPage, Ul } from './legal';

export const PrivacyPage = () => (
  <LegalPage title="Privacy Policy">
    <p>
      {COMPANY.legalName} ("we", "us") operates {COMPANY.site} (including {COMPANY.toursSite}) so prospective renters can request
      self-guided tours of our rental homes. This policy explains what we collect and how we use it.
    </p>

    <H2>Information we collect</H2>
    <Ul>
      <li>Your name, email address, and mobile phone number.</li>
      <li>The home you want to tour and your requested date and time.</li>
      <li>A photo of your government-issued ID.</li>
      <li>Feedback you choose to give after your tour.</li>
      <li>Basic technical data (such as IP address) used to keep the site secure and prevent abuse.</li>
    </Ul>

    <H2>How we use it</H2>
    <Ul>
      <li>To review and approve or decline your tour request.</li>
      <li>To verify your identity before granting access to a home.</li>
      <li>
        To contact you about your tour by email and, if you opt in, by text message — including
        approval status, your one-time access code, and a feedback request.
      </li>
      <li>To protect our properties and the security of this site.</li>
    </Ul>

    <H2>Photo ID retention</H2>
    <p>
      Your ID photo is visible only to us, used only to verify your identity for your tour, and
      deleted automatically 30 days after your scheduled tour.
    </p>

    <H2>Sharing</H2>
    <p>
      We do not sell or rent your personal information. We share it only with service providers
      that help us run this site and send messages (for example, our hosting, email, and text
      messaging providers), and only as needed to provide the service, or when required by law.
    </p>
    <p>
      <strong>
        No mobile information will be shared with third parties or affiliates for marketing or
        promotional purposes.
      </strong>{' '}
      Text messaging opt-in data and consent are never shared with any third party, except the
      providers that deliver our messages.
    </p>

    <H2>Text messages</H2>
    <p>
      Text messaging is optional. See our <Link to="/sms-terms" className="text-blue-700 hover:underline">SMS Terms</Link>{' '}
      for details. Reply STOP to any message to opt out.
    </p>

    <H2>Your choices</H2>
    <p>
      You can ask us to access, correct, or delete your information at any time by emailing{' '}
      <a href={`mailto:${COMPANY.email}`} className="text-blue-700 hover:underline">{COMPANY.email}</a>.
    </p>

    <H2>Changes</H2>
    <p>We may update this policy and will post the new version on this page with its effective date.</p>
  </LegalPage>
);
